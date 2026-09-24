from django.utils import timezone

from .models import ServiceOrder


# Clasificación de los diez estados existentes.
STATUS_CATEGORIES = {
    ServiceOrder.Status.RECEIVED: "WAITING",
    ServiceOrder.Status.DIAGNOSIS: "TECHNICAL",
    ServiceOrder.Status.AUTHORIZATION: "WAITING",
    ServiceOrder.Status.PART: "WAITING",
    ServiceOrder.Status.REPAIR: "TECHNICAL",
    ServiceOrder.Status.TESTING: "TECHNICAL",
    ServiceOrder.Status.READY: "WAITING",
    ServiceOrder.Status.REJECTED: "WAITING",
    ServiceOrder.Status.DELIVERED: "EXCLUDED",
    ServiceOrder.Status.CLOSED: "EXCLUDED",
}


def format_duration(seconds):
    """
    Convierte una duración numérica en un texto legible.

    Ejemplos:
    5063.558 segundos -> 1 h 24 min 24 s
    259200 segundos -> 3 d
    """
    total_seconds = int(seconds + 0.5)

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)

    parts = []

    if days:
        parts.append(f"{days} d")

    if hours:
        parts.append(f"{hours} h")

    if minutes:
        parts.append(f"{minutes} min")

    if remaining_seconds or not parts:
        parts.append(f"{remaining_seconds} s")

    return " ".join(parts)


def calculate_order_times(order, as_of=None):
    """
    Calcula los tiempos de una orden a partir de su historial.

    TECHNICAL: tiempo transcurrido en etapas técnicas.
    WAITING: tiempo transcurrido en etapas de espera.
    EXCLUDED: etapas que no suman a los indicadores.

    Los valores numéricos se expresan en segundos.
    Los campos terminados en _display son para presentación.
    """

    reference_time = as_of or timezone.now()

    history = list(
        order.status_history.order_by("changed_at", "id")
    )

    if not history:
        raise ValueError(
            "La orden no tiene historial de estados. "
            "No es posible calcular tiempos verificables."
        )

    if history[0].from_status is not None:
        raise ValueError(
            "El historial no contiene un registro inicial válido."
        )

    if history[-1].to_status != order.status:
        raise ValueError(
            "El estado actual no coincide con el último "
            "registro del historial."
        )

    technical_ms = 0
    waiting_ms = 0

    by_status_ms = {
        state: 0
        for state in STATUS_CATEGORIES
    }

    segments = []

    for index, event in enumerate(history):
        next_event = (
            history[index + 1]
            if index + 1 < len(history)
            else None
        )

        current_status = event.to_status

        if current_status not in STATUS_CATEGORIES:
            raise ValueError(
                f"Estado desconocido en el historial: {current_status}"
            )

        if next_event is not None:
            if next_event.from_status != current_status:
                raise ValueError(
                    "El historial contiene una transición "
                    "que no coincide con el estado anterior."
                )

        category = STATUS_CATEGORIES[current_status]
        start_at = event.changed_at

        if next_event is not None:
            end_at = next_event.changed_at
        elif category == "EXCLUDED":
            # Entregado y cerrado no siguen acumulando tiempo.
            end_at = start_at
        else:
            # La etapa actual sigue acumulando tiempo.
            end_at = reference_time

        if end_at < start_at:
            raise ValueError(
                "El historial contiene fechas inconsistentes."
            )

        elapsed_ms = round(
            (end_at - start_at).total_seconds() * 1000
        )

        # Se conserva el tiempo transcurrido, pero los estados
        # excluidos no suman a los indicadores.
        duration_ms = (
            0
            if category == "EXCLUDED"
            else elapsed_ms
        )

        if category == "TECHNICAL":
            technical_ms += duration_ms

        elif category == "WAITING":
            waiting_ms += duration_ms

        by_status_ms[current_status] += duration_ms

        elapsed_seconds = elapsed_ms / 1000
        duration_seconds = duration_ms / 1000

        segments.append(
            {
                "history_id": event.id,
                "status": current_status,
                "status_display": (
                    ServiceOrder.Status(current_status).label
                ),
                "category": category,
                "started_at": start_at.isoformat(),
                "ended_at": end_at.isoformat(),
                "elapsed_seconds": elapsed_seconds,
                "elapsed_display": format_duration(
                    elapsed_seconds
                ),
                "duration_seconds": duration_seconds,
                "duration_display": format_duration(
                    duration_seconds
                ),
                "is_running": (
                    next_event is None
                    and category != "EXCLUDED"
                ),
            }
        )

    technical_seconds = technical_ms / 1000
    waiting_seconds = waiting_ms / 1000
    total_seconds = technical_seconds + waiting_seconds

    return {
        "order_id": order.id,
        "tracking_code": order.tracking_code,
        "current_status": order.status,
        "calculated_at": reference_time.isoformat(),

        "technical_seconds": technical_seconds,
        "technical_display": format_duration(
            technical_seconds
        ),

        "waiting_seconds": waiting_seconds,
        "waiting_display": format_duration(
            waiting_seconds
        ),

        "total_seconds": total_seconds,
        "total_display": format_duration(
            total_seconds
        ),

        "by_status": {
            state: duration_ms / 1000
            for state, duration_ms in by_status_ms.items()
        },

        "by_status_display": {
            state: format_duration(duration_ms / 1000)
            for state, duration_ms in by_status_ms.items()
        },

        "segments": segments,
    }