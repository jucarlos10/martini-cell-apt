from decimal import Decimal

from .financial_services import calculate_order_financials
from .models import OrderViabilityAssessment
from .services import calculate_order_times


RULE_VERSION = "HU16-v1"

MAX_DIFFICULTY_SCORE = 20
MAX_PARTS_SCORE = 20
MAX_MARGIN_SCORE = 25
MAX_TIME_SCORE = 20
MAX_WARRANTY_SCORE = 15

MAX_TOTAL_SCORE = (
    MAX_DIFFICULTY_SCORE
    + MAX_PARTS_SCORE
    + MAX_MARGIN_SCORE
    + MAX_TIME_SCORE
    + MAX_WARRANTY_SCORE
)


DIFFICULTY_SCORES = {
    OrderViabilityAssessment.Difficulty.LOW: 20,
    OrderViabilityAssessment.Difficulty.MEDIUM: 12,
    OrderViabilityAssessment.Difficulty.HIGH: 5,
}


WARRANTY_RISK_SCORES = {
    OrderViabilityAssessment.WarrantyRisk.LOW: 15,
    OrderViabilityAssessment.WarrantyRisk.MEDIUM: 9,
    OrderViabilityAssessment.WarrantyRisk.HIGH: 3,
}


def calculate_parts_factor(order):
    """
    Evalúa la disponibilidad observable de repuestos.

    La regla utiliza únicamente información registrada
    actualmente en HU-13.

    Si la orden no tiene repuestos registrados, el factor no
    descuenta puntaje. Esto significa únicamente que no existe
    una dependencia de repuestos registrada en el sistema.
    """

    usages = list(
        order.used_parts
        .select_related("part")
        .all()
    )

    if not usages:
        return {
            "key": "parts",
            "label": "Disponibilidad de repuestos",
            "score": MAX_PARTS_SCORE,
            "max_score": MAX_PARTS_SCORE,
            "explanation": (
                "No hay repuestos registrados para esta orden; "
                "este factor no descuenta puntaje."
            ),
        }

    unavailable_parts = [
        usage.part.name
        for usage in usages
        if not usage.part.is_active
    ]

    without_stock = [
        usage.part.name
        for usage in usages
        if usage.part.is_active
        and usage.part.stock == 0
    ]

    if unavailable_parts:
        score = 5
        explanation = (
            "Existe al menos un repuesto utilizado cuyo registro "
            "se encuentra inactivo en el catálogo."
        )

    elif without_stock:
        score = 10
        explanation = (
            "Existe al menos un repuesto utilizado sin stock "
            "actual disponible en el catálogo."
        )

    else:
        score = MAX_PARTS_SCORE
        explanation = (
            "Los repuestos registrados permanecen activos y "
            "con stock disponible en el catálogo."
        )

    return {
        "key": "parts",
        "label": "Disponibilidad de repuestos",
        "score": score,
        "max_score": MAX_PARTS_SCORE,
        "explanation": explanation,
    }


def calculate_margin_factor(order):
    """
    Evalúa el margen estimado utilizando exclusivamente
    la lógica financiera de HU-14.
    """

    financial = calculate_order_financials(order)

    margin_percent = financial[
        "estimated_margin_percent"
    ]

    if margin_percent is None:
        return {
            "key": "margin",
            "label": "Margen estimado",
            "score": None,
            "max_score": MAX_MARGIN_SCORE,
            "explanation": (
                "No existe información suficiente para calcular "
                "el margen estimado de la reparación."
            ),
            "available": False,
        }

    percentage = Decimal(margin_percent)

    if percentage >= Decimal("30"):
        score = 25

    elif percentage >= Decimal("15"):
        score = 20

    elif percentage >= Decimal("0"):
        score = 12

    else:
        score = 0

    return {
        "key": "margin",
        "label": "Margen estimado",
        "score": score,
        "max_score": MAX_MARGIN_SCORE,
        "explanation": (
            f"El margen estimado registrado es de "
            f"{percentage}%."
        ),
        "available": True,
    }


def calculate_time_factor(order):
    """
    Evalúa el tiempo técnico acumulado mediante HU-11.
    """

    try:
        times = calculate_order_times(order)
    except ValueError as error:
        return {
            "key": "time",
            "label": "Tiempo técnico",
            "score": None,
            "max_score": MAX_TIME_SCORE,
            "explanation": str(error),
            "available": False,
        }

    technical_seconds = times["technical_seconds"]
    technical_hours = technical_seconds / 3600

    if technical_hours <= 2:
        score = 20

    elif technical_hours <= 6:
        score = 15

    elif technical_hours <= 12:
        score = 8

    else:
        score = 3

    return {
        "key": "time",
        "label": "Tiempo técnico",
        "score": score,
        "max_score": MAX_TIME_SCORE,
        "explanation": (
            "Tiempo técnico acumulado: "
            f"{times['technical_display']}."
        ),
        "available": True,
    }


def calculate_viability_index(order):
    """
    Calcula el índice de viabilidad explicable de HU-16.

    El índice utiliza reglas explícitas y datos registrados
    en el sistema. No sustituye la evaluación profesional
    del técnico.
    """

    try:
        assessment = order.viability_assessment
    except OrderViabilityAssessment.DoesNotExist:
        return {
            "order_id": order.id,
            "tracking_code": order.tracking_code,
            "rule_version": RULE_VERSION,
            "is_calculable": False,
            "score": None,
            "max_score": MAX_TOTAL_SCORE,
            "level": None,
            "level_display": "Información insuficiente",
            "missing_factors": [
                "difficulty",
                "warranty_risk",
            ],
            "factors": [],
            "advisory": (
                "El índice es una herramienta de apoyo y no "
                "reemplaza la decisión profesional del técnico."
            ),
        }

    difficulty_score = DIFFICULTY_SCORES[
        assessment.difficulty
    ]

    difficulty_factor = {
        "key": "difficulty",
        "label": "Dificultad técnica",
        "score": difficulty_score,
        "max_score": MAX_DIFFICULTY_SCORE,
        "explanation": (
            "Dificultad registrada por el técnico: "
            f"{assessment.get_difficulty_display()}."
        ),
        "available": True,
    }

    parts_factor = calculate_parts_factor(order)
    parts_factor["available"] = True

    margin_factor = calculate_margin_factor(order)
    time_factor = calculate_time_factor(order)

    warranty_score = WARRANTY_RISK_SCORES[
        assessment.warranty_risk
    ]

    warranty_factor = {
        "key": "warranty_risk",
        "label": "Riesgo de garantía",
        "score": warranty_score,
        "max_score": MAX_WARRANTY_SCORE,
        "explanation": (
            "Riesgo de garantía registrado por el técnico: "
            f"{assessment.get_warranty_risk_display()}."
        ),
        "available": True,
    }

    factors = [
        difficulty_factor,
        parts_factor,
        margin_factor,
        time_factor,
        warranty_factor,
    ]

    missing_factors = [
        factor["key"]
        for factor in factors
        if not factor.get("available", True)
    ]

    if missing_factors:
        total_score = None
        level = None
        level_display = "Información insuficiente"
        is_calculable = False

    else:
        total_score = sum(
            factor["score"]
            for factor in factors
        )

        is_calculable = True

        if total_score >= 75:
            level = "HIGH"
            level_display = "Alta"

        elif total_score >= 50:
            level = "MEDIUM"
            level_display = "Media"

        else:
            level = "LOW"
            level_display = "Baja"

    return {
        "order_id": order.id,
        "tracking_code": order.tracking_code,
        "rule_version": RULE_VERSION,
        "is_calculable": is_calculable,
        "score": total_score,
        "max_score": MAX_TOTAL_SCORE,
        "level": level,
        "level_display": level_display,
        "missing_factors": missing_factors,
        "factors": factors,
        "assessment": {
            "difficulty": assessment.difficulty,
            "difficulty_display": (
                assessment.get_difficulty_display()
            ),
            "warranty_risk": assessment.warranty_risk,
            "warranty_risk_display": (
                assessment.get_warranty_risk_display()
            ),
            "notes": assessment.notes,
        },
        "advisory": (
            "El índice es una herramienta de apoyo y no "
            "reemplaza la decisión profesional del técnico."
        ),
    }