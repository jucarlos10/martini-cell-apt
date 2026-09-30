from decimal import Decimal

from inventory.models import OrderPart

from .models import OrderFinancial


ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def calculate_order_financials(order):
    """
    Calcula los costos y el margen estimado de una orden.

    El costo de repuestos proviene exclusivamente de OrderPart,
    utilizando las cantidades y costos históricos de HU-13.

    HU-25 excluye de los costos vigentes los usos de repuestos
    que hayan sido anulados, manteniendo sus antecedentes para
    trazabilidad.
    """

    financial = OrderFinancial.objects.filter(
        order=order
    ).first()

    # Una orden puede no tener todavía datos financieros.
    price = financial.price_charged if financial else None
    labor_cost = financial.labor_cost if financial else ZERO
    other_cost = financial.other_direct_cost if financial else ZERO
    notes = financial.notes if financial else ""

    # Se suman solo las utilizaciones vigentes. Los usos anulados
    # se conservan históricamente, pero ya no forman parte del
    # costo actual de repuestos de la orden.
    usages = OrderPart.objects.filter(
        order=order,
        is_cancelled=False,
    ).values_list("quantity", "unit_cost")

    parts_cost = sum(
        (quantity * unit_cost for quantity, unit_cost in usages),
        ZERO,
    )

    total_cost = parts_cost + labor_cost + other_cost

    # None significa que todavía no se ha definido un precio.
    margin = None
    margin_percent = None

    if price is not None:
        margin = price - total_cost

        # Con precio cero no se puede calcular un porcentaje.
        if price > ZERO:
            margin_percent = (
                margin / price * Decimal("100")
            ).quantize(CENT)

    def money(value):
        if value is None:
            return None

        return str(value.quantize(CENT))

    return {
        "order_id": order.id,
        "tracking_code": order.tracking_code,
        "has_financial_record": financial is not None,
        "price_charged": money(price),
        "parts_cost": money(parts_cost),
        "labor_cost": money(labor_cost),
        "other_direct_cost": money(other_cost),
        "total_direct_cost": money(total_cost),
        "estimated_margin": money(margin),
        "estimated_margin_percent": money(margin_percent),
        "notes": notes,
    }
