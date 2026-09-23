from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps
from rest_framework import serializers

from .models import OrderEvidence, ServiceOrder


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

    class Meta:
        model = ServiceOrder
        fields = (
            "id",
            "tracking_code",
            "received_at",
            "reported_issue",
            "initial_observations",
            "order_url",
        )

        read_only_fields = fields

    def get_order_url(self, obj):
        return f"/api/orders/{obj.id}/"


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