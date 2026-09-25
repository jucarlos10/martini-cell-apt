from django.utils import timezone

from .models import ServiceOrder
from .services import calculate_order_times, format_duration


# HU-16: estados que se consideran finalizados
# para los indicadores operacionales.
FINAL_STATUSES = {
    ServiceOrder.Status.DELIVERED,
    ServiceOrder.Status.CLOSED,
}


def calculate_operational_indicators(start_date, end_date):
    """
    Calcula los indicadores operacionales del período indicado.

    Solo se consideran órdenes recibidas dentro del período.

    Los tiempos reutilizan la lógica implementada en HU-11.
    Si una orden tiene un historial inconsistente, se mantiene
    en los conteos generales, pero no participa en los
    promedios de tiempo.
    """

    calculated_at = timezone.now()

    orders = list(
        ServiceOrder.objects
        .filter(
            received_at__date__gte=start_date,
            received_at__date__lte=end_date,
        )
        .order_by("received_at", "id")
    )

    status_counts = {
        status_value: 0
        for status_value, _ in ServiceOrder.Status.choices
    }

    technical_total = 0
    waiting_total = 0
    total_duration = 0

    orders_with_time_data = 0
    orders_without_time_data = 0

    for order in orders:
        status_counts[order.status] += 1

        try:
            times = calculate_order_times(
                order,
                as_of=calculated_at,
            )
        except ValueError:
            orders_without_time_data += 1
            continue

        technical_total += times["technical_seconds"]
        waiting_total += times["waiting_seconds"]
        total_duration += times["total_seconds"]

        orders_with_time_data += 1

    def calculate_average(total):
        if orders_with_time_data == 0:
            return 0

        return total / orders_with_time_data

    average_technical = calculate_average(
        technical_total
    )

    average_waiting = calculate_average(
        waiting_total
    )

    average_total = calculate_average(
        total_duration
    )

    finalized_orders = sum(
        status_counts[status_value]
        for status_value in FINAL_STATUSES
    )

    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "calculated_at": calculated_at.isoformat(),

        "orders_received": len(orders),
        "orders_finalized": finalized_orders,

        "orders_with_time_data": orders_with_time_data,
        "orders_without_time_data": orders_without_time_data,

        "average_technical_seconds": average_technical,
        "average_technical_display": format_duration(
            average_technical
        ),

        "average_waiting_seconds": average_waiting,
        "average_waiting_display": format_duration(
            average_waiting
        ),

        "average_total_seconds": average_total,
        "average_total_display": format_duration(
            average_total
        ),

        "orders_by_status": [
            {
                "status": status_value,
                "status_display": status_label,
                "count": status_counts[status_value],
            }
            for status_value, status_label
            in ServiceOrder.Status.choices
        ],
    }