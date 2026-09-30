from rest_framework import serializers

from .models import (
    Supplier,
    Part,
    OrderPart,
    OrderPartCorrectionHistory,
)


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = (
            "id",
            "name",
            "contact_name",
            "phone",
            "email",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class PartSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(
        source="supplier.name",
        read_only=True,
    )

    class Meta:
        model = Part
        fields = (
            "id",
            "name",
            "description",
            "supplier",
            "supplier_name",
            "unit_cost",
            "stock",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "supplier_name",
            "created_at",
            "updated_at",
        )

    def validate_supplier(self, supplier):
        if not supplier.is_active:
            raise serializers.ValidationError(
                "No puedes asociar un proveedor inactivo."
            )

        return supplier


class OrderPartSerializer(serializers.ModelSerializer):
    part = serializers.PrimaryKeyRelatedField(
        queryset=Part.objects.filter(is_active=True),
    )

    quantity = serializers.IntegerField(min_value=1)

    part_name = serializers.CharField(
        source="part.name",
        read_only=True,
    )

    supplier_name = serializers.CharField(
        source="supplier.name",
        read_only=True,
    )

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderPart
        fields = (
            "id",
            "order",
            "part",
            "part_name",
            "supplier",
            "supplier_name",
            "quantity",
            "unit_cost",
            "subtotal",
            "note",
            "created_by_username",
            "created_at",
        )

        read_only_fields = (
            "id",
            "order",
            "part_name",
            "supplier",
            "supplier_name",
            "unit_cost",
            "subtotal",
            "created_by_username",
            "created_at",
        )

    def get_subtotal(self, obj):
        return f"{obj.subtotal:.2f}"


class OrderPartCorrectionSerializer(serializers.Serializer):
    """
    Entrada para HU-24.

    Solo se corrigen directamente cantidad o nota.
    El motivo siempre es obligatorio.
    """

    field_name = serializers.ChoiceField(
        choices=OrderPartCorrectionHistory.Field.choices,
    )

    new_value = serializers.CharField(
        allow_blank=True,
        trim_whitespace=False,
    )

    reason = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
    )

    def validate_reason(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Debes indicar el motivo de la corrección."
            )

        return value.strip()

    def validate(self, attrs):
        field_name = attrs["field_name"]
        new_value = attrs["new_value"]

        if field_name == OrderPartCorrectionHistory.Field.QUANTITY:
            try:
                quantity = int(str(new_value).strip())
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    {
                        "new_value": (
                            "La nueva cantidad debe ser un número entero."
                        )
                    }
                )

            if quantity < 1:
                raise serializers.ValidationError(
                    {
                        "new_value": (
                            "La nueva cantidad debe ser mayor o igual a 1."
                        )
                    }
                )

            attrs["normalized_value"] = quantity
            return attrs

        if field_name == OrderPartCorrectionHistory.Field.NOTE:
            note = str(new_value)

            if len(note) > 250:
                raise serializers.ValidationError(
                    {
                        "new_value": (
                            "La nota no puede superar los 250 caracteres."
                        )
                    }
                )

            attrs["normalized_value"] = note
            return attrs

        raise serializers.ValidationError(
            {
                "field_name": (
                    "El campo seleccionado no puede corregirse directamente."
                )
            }
        )


class OrderPartCorrectionHistorySerializer(
    serializers.ModelSerializer
):
    field_display = serializers.CharField(
        source="get_field_name_display",
        read_only=True,
    )

    class Meta:
        model = OrderPartCorrectionHistory
        fields = (
            "id",
            "order_part",
            "field_name",
            "field_display",
            "old_value",
            "new_value",
            "reason",
            "changed_by_username",
            "changed_by_role",
            "changed_at",
        )

        read_only_fields = fields
