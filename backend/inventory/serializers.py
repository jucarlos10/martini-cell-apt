
from rest_framework import serializers

from .models import Supplier, Part, OrderPart


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