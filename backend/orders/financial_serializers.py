
from decimal import Decimal

from rest_framework import serializers

from .models import OrderFinancial


class OrderFinancialSerializer(serializers.ModelSerializer):
    """
    Valida los datos financieros ingresados por el usuario.

    El costo de repuestos y los márgenes no se reciben
    desde el formulario: se calculan en el servidor.
    """

    price_charged = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        allow_null=True,
    )

    labor_cost = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
    )

    other_direct_cost = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
    )

    class Meta:
        model = OrderFinancial

        fields = (
            "id",
            "order",
            "price_charged",
            "labor_cost",
            "other_direct_cost",
            "notes",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "order",
            "created_at",
            "updated_at",
        )