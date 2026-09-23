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
            "received_at",
            "updated_at",
            "created_by_username",
        )

        read_only_fields = (
            "id",
            "tracking_code",
            "client_name",
            "equipment_description",
            "received_at",
            "updated_at",
            "created_by_username",
        )

    def get_equipment_description(self, obj):
        return (
            f"{obj.equipment.brand} "
            f"{obj.equipment.model}"
        )

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

        return attrs


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