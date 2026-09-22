from rest_framework import serializers

from .models import ServiceOrder


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