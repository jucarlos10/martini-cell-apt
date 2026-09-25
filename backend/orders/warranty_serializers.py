
from rest_framework import serializers

from inventory.models import OrderPart

from .models import OrderWarranty, OrderWarrantyHistory


class OrderWarrantyWriteSerializer(serializers.ModelSerializer):
    """
    Valida los datos recibidos para crear o actualizar
    una garantía.
    """

    order_part = serializers.PrimaryKeyRelatedField(
        queryset=OrderPart.objects.all(),
        required=False,
        allow_null=True,
    )

    change_note = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        write_only=True,
    )

    class Meta:
        model = OrderWarranty

        fields = (
            "warranty_type",
            "order_part",
            "is_applicable",
            "starts_on",
            "ends_on",
            "conditions",
            "change_note",
        )

    def validate(self, attrs):
        instance = self.instance

        warranty_type = attrs.get(
            "warranty_type",
            instance.warranty_type if instance else None,
        )

        order_part = attrs.get(
            "order_part",
            instance.order_part if instance else None,
        )

        is_applicable = attrs.get(
            "is_applicable",
            instance.is_applicable if instance else True,
        )

        starts_on = attrs.get(
            "starts_on",
            instance.starts_on if instance else None,
        )

        ends_on = attrs.get(
            "ends_on",
            instance.ends_on if instance else None,
        )

        conditions = attrs.get(
            "conditions",
            instance.conditions if instance else "",
        )

        order = self.context.get("order")

        if warranty_type == OrderWarranty.WarrantyType.SERVICE:
            if order_part is not None:
                raise serializers.ValidationError({
                    "order_part": (
                        "La garantía del servicio no debe "
                        "vincularse a un repuesto."
                    )
                })

        elif warranty_type == OrderWarranty.WarrantyType.PART:
            if order_part is None:
                raise serializers.ValidationError({
                    "order_part": (
                        "Selecciona el repuesto utilizado "
                        "en esta orden."
                    )
                })

            if order is not None and order_part.order_id != order.pk:
                raise serializers.ValidationError({
                    "order_part": (
                        "El repuesto seleccionado no pertenece "
                        "a esta orden."
                    )
                })

        if not is_applicable:
            if starts_on is not None or ends_on is not None:
                raise serializers.ValidationError({
                    "starts_on": (
                        "Una garantía que no aplica "
                        "no debe tener fechas."
                    )
                })

        else:
            if starts_on is None or ends_on is None:
                raise serializers.ValidationError({
                    "starts_on": (
                        "Indica las fechas de inicio "
                        "y término de la garantía."
                    )
                })

            if ends_on < starts_on:
                raise serializers.ValidationError({
                    "ends_on": (
                        "La fecha de término no puede ser "
                        "anterior a la fecha de inicio."
                    )
                })

            if not conditions.strip():
                raise serializers.ValidationError({
                    "conditions": (
                        "Indica las condiciones de la garantía."
                    )
                })

        if instance is not None:
            change_note = attrs.get("change_note", "")

            if not change_note.strip():
                raise serializers.ValidationError({
                    "change_note": (
                        "Indica el motivo de la modificación."
                    )
                })

        return attrs


class OrderWarrantyReadSerializer(serializers.ModelSerializer):
    """
    Presenta los datos actuales y la vigencia calculada.
    """

    status = serializers.CharField(
        source="current_status",
        read_only=True,
    )

    warranty_type_display = serializers.CharField(
        source="get_warranty_type_display",
        read_only=True,
    )

    part_name = serializers.SerializerMethodField()
    supplier_name = serializers.SerializerMethodField()

    class Meta:
        model = OrderWarranty

        fields = (
            "id",
            "order",
            "warranty_type",
            "warranty_type_display",
            "order_part",
            "part_name",
            "supplier_name",
            "is_applicable",
            "starts_on",
            "ends_on",
            "conditions",
            "status",
            "created_at",
            "updated_at",
        )

    def get_part_name(self, obj):
        if obj.order_part_id is None:
            return None

        return obj.order_part.part.name

    def get_supplier_name(self, obj):
        if obj.order_part_id is None:
            return None

        return obj.order_part.supplier.name


class OrderWarrantyHistorySerializer(serializers.ModelSerializer):
    """
    Presenta las revisiones conservadas de una garantía.
    """

    class Meta:
        model = OrderWarrantyHistory

        fields = (
            "id",
            "warranty",
            "revision",
            "action",
            "order",
            "warranty_type",
            "order_part",
            "is_applicable",
            "starts_on",
            "ends_on",
            "conditions",
            "change_note",
            "changed_by_username",
            "changed_at",
        )