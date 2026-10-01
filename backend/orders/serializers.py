from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Max
from PIL import Image, ImageOps
from rest_framework import serializers

from accounts.models import User

from .models import (
    OrderEvidence,
    OrderSensitiveChangeHistory,
    OrderStatusHistory,
    OrderTechnicalReport,
    OrderTechnicalReportHistory,
    ServiceOrder,
)


class ServiceOrderSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(
        source="client.name",
        read_only=True,
    )

    equipment_description = serializers.SerializerMethodField()

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    # HU-27: motivo del cambio sensible. No se guarda en ServiceOrder;
    # se conserva únicamente en el historial de auditoría.
    change_reason = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    class Meta:
        model = ServiceOrder
        fields = (
            "id",
            "tracking_code",
            "client",
            "client_name",
            "equipment",
            "equipment_description",
            "reported_issue",
            "initial_observations",
            "status",
            "status_display",
            "received_at",
            "updated_at",
            "created_by_username",
            "change_reason",
        )

        read_only_fields = (
            "id",
            "tracking_code",
            "client_name",
            "equipment_description",
            "status",
            "status_display",
            "received_at",
            "updated_at",
            "created_by_username",
        )

    def get_equipment_description(self, obj):
        return (
            f"{obj.equipment.brand} "
            f"{obj.equipment.model}"
        )

    def _field_changes(self, instance, attrs):
        """
        Devuelve los campos sensibles cuyo valor realmente cambia.

        Cliente y equipo se comparan por PK. Los campos de texto se
        comparan directamente para no crear registros de auditoría
        cuando un PATCH reenvía el mismo valor.
        """
        changes = []

        if "client" in attrs:
            new_client = attrs["client"]

            if new_client.pk != instance.client_id:
                changes.append("client")

        if "equipment" in attrs:
            new_equipment = attrs["equipment"]

            if new_equipment.pk != instance.equipment_id:
                changes.append("equipment")

        if (
            "reported_issue" in attrs
            and attrs["reported_issue"] != instance.reported_issue
        ):
            changes.append("reported_issue")

        if (
            "initial_observations" in attrs
            and attrs["initial_observations"]
            != instance.initial_observations
        ):
            changes.append("initial_observations")

        return changes

    def _snapshot_value(self, field_name, value):
        """
        Convierte el valor en una copia JSON estable para la auditoría.
        Así el historial sigue siendo legible aunque luego cambien los
        datos descriptivos del cliente o del equipo.
        """
        if field_name == "client":
            return {
                "id": value.pk,
                "name": value.name,
            }

        if field_name == "equipment":
            return {
                "id": value.pk,
                "description": (
                    f"{value.brand} {value.model}"
                ).strip(),
            }

        return value

    def validate(self, attrs):
        client = attrs.get(
            "client",
            getattr(self.instance, "client", None),
        )

        equipment = attrs.get(
            "equipment",
            getattr(self.instance, "equipment", None),
        )

        if (
            client
            and equipment
            and equipment.client_id != client.id
        ):
            raise serializers.ValidationError(
                {
                    "equipment": (
                        "El equipo seleccionado no pertenece "
                        "al cliente indicado."
                    )
                }
            )

        if self.instance is not None:
            changes = self._field_changes(
                self.instance,
                attrs,
            )

            if (
                self.instance.status
                in {
                    ServiceOrder.Status.DELIVERED,
                    ServiceOrder.Status.CLOSED,
                }
                and changes
            ):
                raise serializers.ValidationError(
                    {
                        "detail": (
                            "No se pueden modificar datos generales "
                            "de una orden entregada o cerrada."
                        )
                    }
                )

            if (
                {"client", "equipment"} & set(changes)
                and not attrs.get("change_reason", "").strip()
            ):
                raise serializers.ValidationError(
                    {
                        "change_reason": (
                            "Debes indicar el motivo al cambiar "
                            "el cliente o el equipo de la orden."
                        )
                    }
                )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        # change_reason solo existe para modificaciones posteriores.
        validated_data.pop("change_reason", None)

        order = super().create(validated_data)

        OrderStatusHistory.objects.create(
            order=order,
            from_status=None,
            to_status=order.status,
            note="Registro inicial al crear la orden.",
            changed_by=order.created_by,
        )

        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        change_reason = validated_data.pop(
            "change_reason",
            "",
        ).strip()

        # Bloquea la fila para que la modificación y su auditoría se
        # calculen sobre el mismo estado de la orden.
        order = (
            ServiceOrder.objects
            .select_for_update()
            .select_related("client", "equipment")
            .get(pk=instance.pk)
        )

        changes = self._field_changes(
            order,
            validated_data,
        )

        if (
            order.status
            in {
                ServiceOrder.Status.DELIVERED,
                ServiceOrder.Status.CLOSED,
            }
            and changes
        ):
            raise serializers.ValidationError(
                {
                    "detail": (
                        "No se pueden modificar datos generales "
                        "de una orden entregada o cerrada."
                    )
                }
            )

        if (
            {"client", "equipment"} & set(changes)
            and not change_reason
        ):
            raise serializers.ValidationError(
                {
                    "change_reason": (
                        "Debes indicar el motivo al cambiar "
                        "el cliente o el equipo de la orden."
                    )
                }
            )

        old_values = {}

        for field_name in changes:
            if field_name == "client":
                old_values[field_name] = self._snapshot_value(
                    field_name,
                    order.client,
                )

            elif field_name == "equipment":
                old_values[field_name] = self._snapshot_value(
                    field_name,
                    order.equipment,
                )

            else:
                old_values[field_name] = self._snapshot_value(
                    field_name,
                    getattr(order, field_name),
                )

        order = super().update(
            order,
            validated_data,
        )

        request = self.context.get("request")
        changed_by = None

        if (
            request is not None
            and getattr(request, "user", None) is not None
            and request.user.is_authenticated
        ):
            changed_by = request.user

        for field_name in changes:
            if field_name == "client":
                new_value = self._snapshot_value(
                    field_name,
                    order.client,
                )

            elif field_name == "equipment":
                new_value = self._snapshot_value(
                    field_name,
                    order.equipment,
                )

            else:
                new_value = self._snapshot_value(
                    field_name,
                    getattr(order, field_name),
                )

            OrderSensitiveChangeHistory.objects.create(
                order=order,
                field=field_name.upper(),
                old_value=old_values[field_name],
                new_value=new_value,
                reason=change_reason,
                changed_by=changed_by,
                changed_by_username=(
                    changed_by.username
                    if changed_by is not None
                    else ""
                ),
                changed_by_role=(
                    changed_by.role
                    if changed_by is not None
                    else ""
                ),
            )

        return order


class OrderSensitiveChangeHistorySerializer(
    serializers.ModelSerializer
):
    field_display = serializers.CharField(
        source="get_field_display",
        read_only=True,
    )

    class Meta:
        model = OrderSensitiveChangeHistory
        fields = (
            "id",
            "field",
            "field_display",
            "old_value",
            "new_value",
            "reason",
            "changed_by_username",
            "changed_by_role",
            "changed_at",
        )

        read_only_fields = fields


class ServiceOrderHistorySerializer(serializers.ModelSerializer):
    order_url = serializers.SerializerMethodField()

    diagnosis = serializers.SerializerMethodField()
    repair_actions = serializers.SerializerMethodField()
    repair_observations = serializers.SerializerMethodField()
    parts_description = serializers.SerializerMethodField()
    result = serializers.SerializerMethodField()
    result_display = serializers.SerializerMethodField()
    technician_username = serializers.SerializerMethodField()

    class Meta:
        model = ServiceOrder
        fields = (
            "id",
            "tracking_code",
            "received_at",
            "reported_issue",
            "initial_observations",
            "diagnosis",
            "repair_actions",
            "repair_observations",
            "parts_description",
            "result",
            "result_display",
            "technician_username",
            "order_url",
        )

        read_only_fields = fields

    def get_order_url(self, obj):
        return f"/api/orders/{obj.id}/"

    def get_technical_report(self, obj):
        try:
            return obj.technical_report
        except OrderTechnicalReport.DoesNotExist:
            return None

    def get_diagnosis(self, obj):
        report = self.get_technical_report(obj)
        return report.diagnosis if report else None

    def get_repair_actions(self, obj):
        report = self.get_technical_report(obj)
        return report.repair_actions if report else None

    def get_repair_observations(self, obj):
        report = self.get_technical_report(obj)
        return report.repair_observations if report else None

    def get_parts_description(self, obj):
        report = self.get_technical_report(obj)
        return report.parts_description if report else None

    def get_result(self, obj):
        report = self.get_technical_report(obj)
        return report.result if report else None

    def get_result_display(self, obj):
        report = self.get_technical_report(obj)

        if not report:
            return None

        return report.get_result_display()

    def get_technician_username(self, obj):
        report = self.get_technical_report(obj)

        if not report:
            return None

        return report.technician.username


class OrderEvidenceSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(
        write_only=True,
    )

    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username",
        read_only=True,
    )

    download_url = serializers.SerializerMethodField()

    class Meta:
        model = OrderEvidence
        fields = (
            "id",
            "order",
            "stage",
            "image",
            "description",
            "uploaded_by_username",
            "created_at",
            "download_url",
        )

        read_only_fields = (
            "id",
            "order",
            "uploaded_by_username",
            "created_at",
            "download_url",
        )

    def validate_image(self, value):
        allowed_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }

        extension = Path(value.name).suffix.lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Formato no permitido. Usa JPG, JPEG, PNG o WEBP."
            )

        if value.size > settings.EVIDENCE_MAX_UPLOAD_SIZE:
            raise serializers.ValidationError(
                "La imagen no puede superar los 20 MB."
            )

        # Hasta 10 MB se guarda sin modificar.
        if value.size <= settings.EVIDENCE_MAX_FILE_SIZE:
            return value

        # Entre 10 y 20 MB se intenta optimizar.
        try:
            value.seek(0)

            image = Image.open(value)
            image = ImageOps.exif_transpose(image)

            if image.mode != "RGB":
                image = image.convert("RGB")

            quality = 85

            while True:
                output = BytesIO()

                image.save(
                    output,
                    format="JPEG",
                    quality=quality,
                    optimize=True,
                )

                if output.tell() <= settings.EVIDENCE_MAX_FILE_SIZE:
                    break

                if quality > 60:
                    quality -= 10
                else:
                    new_width = max(
                        1,
                        int(image.width * 0.85),
                    )
                    new_height = max(
                        1,
                        int(image.height * 0.85),
                    )

                    image = image.resize(
                        (new_width, new_height),
                        Image.Resampling.LANCZOS,
                    )

            output.seek(0)

            new_name = (
                f"{Path(value.name).stem}_optimized.jpg"
            )

            return ContentFile(
                output.read(),
                name=new_name,
            )

        except Exception:
            raise serializers.ValidationError(
                "No fue posible procesar la imagen."
            )

    def get_download_url(self, obj):
        return (
            f"/api/orders/{obj.order_id}/"
            f"evidence/{obj.id}/download/"
        )


class OrderTechnicalReportSerializer(serializers.ModelSerializer):
    technician = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(
            role=User.Role.TECH,
            is_active=True,
        )
    )

    technician_username = serializers.CharField(
        source="technician.username",
        read_only=True,
    )

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    updated_by_username = serializers.CharField(
        source="updated_by.username",
        read_only=True,
    )

    result_display = serializers.CharField(
        source="get_result_display",
        read_only=True,
    )

    class Meta:
        model = OrderTechnicalReport
        fields = (
            "id",
            "order",
            "diagnosis",
            "repair_actions",
            "repair_observations",
            "parts_description",
            "result",
            "result_display",
            "technician",
            "technician_username",
            "created_by_username",
            "updated_by_username",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "order",
            "result_display",
            "technician_username",
            "created_by_username",
            "updated_by_username",
            "created_at",
            "updated_at",
        )

    @transaction.atomic
    def create(self, validated_data):
        report = OrderTechnicalReport.objects.create(
            **validated_data
        )

        OrderTechnicalReportHistory.objects.create(
            report=report,
            revision=1,
            diagnosis=report.diagnosis,
            repair_actions=report.repair_actions,
            repair_observations=report.repair_observations,
            parts_description=report.parts_description,
            result=report.result,
            technician=report.technician,
            changed_by=report.created_by,
        )

        return report

    @transaction.atomic
    def update(self, instance, validated_data):
        report = (
            OrderTechnicalReport.objects
            .select_for_update()
            .get(pk=instance.pk)
        )

        tracked_fields = (
            "diagnosis",
            "repair_actions",
            "repair_observations",
            "parts_description",
            "result",
            "technician_id",
        )

        previous_values = {
            field: getattr(report, field)
            for field in tracked_fields
        }

        report = super().update(
            report,
            validated_data,
        )

        current_values = {
            field: getattr(report, field)
            for field in tracked_fields
        }

        if previous_values != current_values:
            last_revision = (
                report.history.aggregate(
                    max_revision=Max("revision")
                )["max_revision"]
                or 0
            )

            OrderTechnicalReportHistory.objects.create(
                report=report,
                revision=last_revision + 1,
                diagnosis=report.diagnosis,
                repair_actions=report.repair_actions,
                repair_observations=report.repair_observations,
                parts_description=report.parts_description,
                result=report.result,
                technician=report.technician,
                changed_by=report.updated_by,
            )

        return report


class OrderTechnicalReportHistorySerializer(
    serializers.ModelSerializer
):
    technician_username = serializers.CharField(
        source="technician.username",
        read_only=True,
    )

    changed_by_username = serializers.CharField(
        source="changed_by.username",
        read_only=True,
    )

    result_display = serializers.CharField(
        source="get_result_display",
        read_only=True,
    )

    class Meta:
        model = OrderTechnicalReportHistory
        fields = (
            "id",
            "revision",
            "diagnosis",
            "repair_actions",
            "repair_observations",
            "parts_description",
            "result",
            "result_display",
            "technician",
            "technician_username",
            "changed_by_username",
            "changed_at",
        )

        read_only_fields = fields