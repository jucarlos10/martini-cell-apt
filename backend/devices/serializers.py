from rest_framework import serializers

from .models import Equipment


class EquipmentSerializer(serializers.ModelSerializer):
    imei = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=30,
    )

    serial_number = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=100,
    )

    client_name = serializers.CharField(
        source="client.name",
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

    class Meta:
        model = Equipment
        fields = (
            "id",
            "client",
            "client_name",
            "equipment_type",
            "brand",
            "model",
            "imei",
            "serial_number",
            "color",
            "observations",
            "is_active",
            "created_at",
            "updated_at",
            "created_by_username",
            "updated_by_username",
        )

        read_only_fields = (
            "id",
            "client_name",
            "created_at",
            "updated_at",
            "created_by_username",
            "updated_by_username",
        )

    def validate_imei(self, value):
        if not value:
            return None

        normalized_imei = (
            value.replace(" ", "")
            .replace("-", "")
            .strip()
        )

        queryset = Equipment.objects.filter(
            imei=normalized_imei
        )

        if self.instance:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise serializers.ValidationError(
                "Ya existe un equipo registrado con este IMEI."
            )

        return normalized_imei

    def validate_serial_number(self, value):
        if not value:
            return None

        normalized_serial = (
            value.replace(" ", "")
            .strip()
            .upper()
        )

        queryset = Equipment.objects.filter(
            serial_number=normalized_serial
        )

        if self.instance:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise serializers.ValidationError(
                "Ya existe un equipo registrado con este número de serie."
            )

        return normalized_serial