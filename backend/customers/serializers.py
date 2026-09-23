from rest_framework import serializers

from .models import Client, ClientChangeHistory
from .validators import normalize_rut, validate_rut


class ClientSerializer(serializers.ModelSerializer):
    rut = serializers.CharField(max_length=20)

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )
    updated_by_username = serializers.CharField(
        source="updated_by.username",
        read_only=True,
    )

    class Meta:
        model = Client
        fields = (
            "id",
            "rut",
            "name",
            "phone",
            "email",
            "is_active",
            "created_at",
            "updated_at",
            "created_by_username",
            "updated_by_username",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "created_by_username",
            "updated_by_username",
        )

    def validate_rut(self, value):
        rut = normalize_rut(value)

        validate_rut(rut)

        queryset = Client.objects.filter(rut=rut)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "Ya existe un cliente registrado con este RUT."
            )

        return rut


class ClientChangeHistorySerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(
        source="changed_by.username",
        read_only=True,
    )

    class Meta:
        model = ClientChangeHistory
        fields = (
            "id",
            "changed_at",
            "changed_by_username",
            "changes",
        )
        read_only_fields = fields