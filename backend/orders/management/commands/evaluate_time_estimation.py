from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from orders.models import OrderTechnicalReport, ServiceOrder
from orders.services import calculate_order_times


MINIMUM_CASES = 30

FINAL_STATUSES = {
    ServiceOrder.Status.DELIVERED,
    ServiceOrder.Status.CLOSED,
    ServiceOrder.Status.REJECTED,
}

# Una orden rechazada podría no haber tenido una reparación efectiva.
# Por eso se revisa por separado y no entra automáticamente como
# candidato para estimar el tiempo técnico de una reparación.
POTENTIAL_TRAINING_STATUSES = {
    ServiceOrder.Status.DELIVERED,
    ServiceOrder.Status.CLOSED,
}


class Command(BaseCommand):
    help = (
        "Evalúa la cantidad y calidad inicial de los datos "
        "disponibles para el experimento de HU-17. "
        "No entrena modelos ni modifica la base de datos."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--minimum",
            type=int,
            default=MINIMUM_CASES,
            help=(
                "Mínimo operativo preliminar para volver a evaluar "
                "el conjunto de datos. Por defecto: 30."
            ),
        )

    def handle(self, *args, **options):
        minimum = options["minimum"]

        if minimum < 1:
            raise CommandError(
                "El mínimo debe ser mayor o igual a 1."
            )

        evaluated_at = timezone.now()

        orders = list(
            ServiceOrder.objects.select_related(
                "equipment"
            ).all()
        )

        report_order_ids = set(
            OrderTechnicalReport.objects.values_list(
                "order_id",
                flat=True,
            )
        )

        total_orders = len(orders)

        status_counts = Counter()
        equipment_type_counts = Counter()

        finalized_count = 0
        rejected_count = 0

        valid_history_count = 0
        invalid_history_count = 0

        missing_equipment_type = 0
        missing_brand = 0
        missing_model = 0

        technical_times = []

        # Estos casos solo cumplen condiciones técnicas preliminares.
        # NO se consideran datos operacionales reales verificados.
        preliminary_candidates = 0

        for order in orders:
            status_counts[
                order.get_status_display()
            ] += 1

            equipment = order.equipment

            equipment_type = (
                equipment.get_equipment_type_display()
                if equipment.equipment_type
                else "Sin tipo"
            )

            equipment_type_counts[equipment_type] += 1

            if not equipment.equipment_type:
                missing_equipment_type += 1

            if not (equipment.brand or "").strip():
                missing_brand += 1

            if not (equipment.model or "").strip():
                missing_model += 1

            if order.status in FINAL_STATUSES:
                finalized_count += 1

            if order.status == ServiceOrder.Status.REJECTED:
                rejected_count += 1

            try:
                times = calculate_order_times(
                    order,
                    as_of=evaluated_at,
                )
            except ValueError:
                invalid_history_count += 1
                continue

            valid_history_count += 1

            technical_seconds = times["technical_seconds"]

            technical_times.append(
                technical_seconds
            )

            # Esta comprobación solo identifica candidatos desde
            # el punto de vista técnico. No verifica si el registro
            # corresponde a una reparación real del negocio.
            if (
                order.status in POTENTIAL_TRAINING_STATUSES
                and order.id in report_order_ids
                and technical_seconds > 0
            ):
                preliminary_candidates += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "HU-17 — Evaluación inicial de datos "
                "para estimación del tiempo técnico"
            )
        )

        self.stdout.write(
            f"Fecha de evaluación: {evaluated_at.isoformat()}"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "IMPORTANTE: esta ejecución consulta la base "
                "de datos local del proyecto."
            )
        )

        self.stdout.write(
            "La presencia de una orden en la base de datos "
            "no demuestra que corresponda a una reparación "
            "real del negocio."
        )

        self.stdout.write(
            "El comando no dispone actualmente de un campo "
            "que permita distinguir automáticamente los "
            "registros operacionales de los registros de prueba."
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_LABEL(
                "1. Cantidad de registros"
            )
        )

        self.stdout.write(
            f"Órdenes registradas: {total_orders}"
        )

        self.stdout.write(
            f"Órdenes en estado final: {finalized_count}"
        )

        self.stdout.write(
            f"Órdenes rechazadas: {rejected_count}"
        )

        self.stdout.write(
            "Órdenes con informe técnico: "
            f"{len(report_order_ids)}"
        )

        self.stdout.write(
            f"Historiales válidos: {valid_history_count}"
        )

        self.stdout.write(
            f"Historiales inválidos: {invalid_history_count}"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_LABEL(
                "2. Distribución por estado"
            )
        )

        if status_counts:
            for status, count in sorted(
                status_counts.items()
            ):
                self.stdout.write(
                    f"- {status}: {count}"
                )
        else:
            self.stdout.write(
                "- No existen órdenes registradas."
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_LABEL(
                "3. Distribución por tipo de equipo"
            )
        )

        if equipment_type_counts:
            for equipment_type, count in sorted(
                equipment_type_counts.items()
            ):
                self.stdout.write(
                    f"- {equipment_type}: {count}"
                )
        else:
            self.stdout.write(
                "- No existen equipos para evaluar."
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_LABEL(
                "4. Completitud de variables estructuradas"
            )
        )

        self.stdout.write(
            f"Tipo de equipo faltante: {missing_equipment_type}"
        )

        self.stdout.write(
            f"Marca faltante: {missing_brand}"
        )

        self.stdout.write(
            f"Modelo faltante: {missing_model}"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_LABEL(
                "5. Tiempos técnicos"
            )
        )

        if technical_times:
            minimum_hours = min(technical_times) / 3600
            maximum_hours = max(technical_times) / 3600

            self.stdout.write(
                "Tiempo técnico acumulado mínimo: "
                f"{minimum_hours:.2f} h"
            )

            self.stdout.write(
                "Tiempo técnico acumulado máximo: "
                f"{maximum_hours:.2f} h"
            )

            self.stdout.write(
                "Estos valores pueden incluir órdenes abiertas; "
                "no deben interpretarse automáticamente como "
                "tiempos finales de reparaciones reales."
            )
        else:
            self.stdout.write(
                "No existen tiempos técnicos calculables."
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_LABEL(
                "6. Revisión preliminar para Machine Learning"
            )
        )

        self.stdout.write(
            "Casos técnicamente candidatos: "
            f"{preliminary_candidates}"
        )

        self.stdout.write(
            "Criterios preliminares: orden entregada o cerrada, "
            "informe técnico, historial válido y tiempo "
            "técnico mayor que cero."
        )

        self.stdout.write(
            "Procedencia operacional real: "
            "NO VERIFICABLE AUTOMÁTICAMENTE."
        )

        self.stdout.write(
            "Casos reales validados para entrenamiento: "
            "NO DETERMINADO."
        )

        self.stdout.write(
            "Los candidatos técnicos no deben confundirse "
            "con casos reales aptos para entrenamiento."
        )

        if rejected_count:
            self.stdout.write(
                "Las órdenes rechazadas requieren revisión "
                "individual antes de considerar su utilidad "
                "para un conjunto predictivo."
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_LABEL(
                "7. Posibles problemas de representatividad"
            )
        )

        if total_orders == 0:
            self.stdout.write(
                "- No existen registros disponibles."
            )
        else:
            equipment_name, equipment_count = (
                equipment_type_counts.most_common(1)[0]
            )

            concentration = (
                equipment_count / total_orders
            ) * 100

            self.stdout.write(
                f"- Tipo predominante en los registros: "
                f"{equipment_name} ({concentration:.1f}%)."
            )

            if concentration >= 70:
                self.stdout.write(
                    "- Existe una concentración alta en "
                    "un solo tipo de equipo."
                )

            if total_orders < minimum:
                self.stdout.write(
                    "- El conjunto registrado es reducido."
                )

            if finalized_count == 0:
                self.stdout.write(
                    "- No existen órdenes en estado final."
                )

        self.stdout.write(
            "- Esta distribución no representa necesariamente "
            "la actividad real del negocio."
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_LABEL(
                "8. Privacidad"
            )
        )

        self.stdout.write(
            "El comando muestra resultados agregados."
        )

        self.stdout.write(
            "No exporta nombres, RUT, teléfonos, correos, "
            "IMEI, números de serie, códigos de seguimiento "
            "ni fotografías."
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_LABEL(
                "9. Decisión HU-17"
            )
        )

        self.stdout.write(
            f"Mínimo operativo preliminar: {minimum} casos "
            "reales, finalizados, válidos y anonimizados."
        )

        self.stdout.write(
            "Candidatos identificados automáticamente: "
            f"{preliminary_candidates}."
        )

        if preliminary_candidates < minimum:
            self.stdout.write(
                "El conjunto ni siquiera alcanza el mínimo "
                "preliminar de candidatos técnicos."
            )
        else:
            self.stdout.write(
                "Se alcanzó el mínimo preliminar de candidatos "
                "técnicos, pero esto no acredita su procedencia "
                "real ni su suficiencia estadística."
            )

        self.stdout.write(
            self.style.WARNING(
                "DECISIÓN: NO ENTRENAR NI INTEGRAR "
                "AUTOMÁTICAMENTE UN MODELO PREDICTIVO."
            )
        )

        self.stdout.write(
            "Antes de iniciar el experimento deberá prepararse "
            "y validarse un conjunto de reparaciones reales, "
            "finalizadas y anonimizadas."
        )

        self.stdout.write(
            "También deberán revisarse la calidad, la diversidad "
            "y la representatividad de esos datos."
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_LABEL(
                "10. Metodología futura"
            )
        )

        self.stdout.write(
            "Variable objetivo: tiempo técnico final en horas."
        )

        self.stdout.write(
            "Línea base: mediana del tiempo técnico del "
            "conjunto de entrenamiento."
        )

        self.stdout.write(
            "Métrica principal: MAE en horas."
        )

        self.stdout.write(
            "Métrica complementaria: RMSE en horas."
        )

        self.stdout.write(
            "Semilla reproducible: random_state = 42."
        )

        self.stdout.write(
            "La evaluación predictiva se realizará solamente "
            "cuando exista un conjunto operacional apto."
        )

        self.stdout.write("")