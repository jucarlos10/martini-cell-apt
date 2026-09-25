from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from customers.models import Client
from devices.models import Equipment

from .models import (
    OrderStatusHistory,
    OrderTechnicalReport,
    ServiceOrder,
)


class TimeEstimationCommandTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_hu17",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tecnico_hu17",
            role=User.Role.TECH,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente de prueba HU17",
            phone="912345678",
            created_by=self.admin,
        )

        self.start_at = timezone.now() - timedelta(hours=4)

    def run_evaluation(self, minimum=None):
        output = StringIO()

        options = {
            "stdout": output,
            "no_color": True,
        }

        if minimum is not None:
            options["minimum"] = minimum

        call_command(
            "evaluate_time_estimation",
            **options,
        )

        return output.getvalue()

    def create_order(
        self,
        equipment_type=Equipment.EquipmentType.CELULAR,
    ):
        equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=equipment_type,
            brand="Marca de prueba",
            model="Modelo de prueba",
            created_by=self.admin,
        )

        order = ServiceOrder.objects.create(
            client=self.customer,
            equipment=equipment,
            reported_issue="Falla utilizada para prueba HU-17.",
            created_by=self.admin,
        )

        initial_event = OrderStatusHistory.objects.create(
            order=order,
            from_status=None,
            to_status=ServiceOrder.Status.RECEIVED,
            changed_by=self.admin,
        )

        OrderStatusHistory.objects.filter(
            pk=initial_event.pk,
        ).update(
            changed_at=self.start_at,
        )

        return order

    def change_status(self, order, new_status, hours):
        event = OrderStatusHistory.objects.create(
            order=order,
            from_status=order.status,
            to_status=new_status,
            changed_by=self.admin,
        )

        OrderStatusHistory.objects.filter(
            pk=event.pk,
        ).update(
            changed_at=(
                self.start_at + timedelta(hours=hours)
            ),
        )

        ServiceOrder.objects.filter(
            pk=order.pk,
        ).update(
            status=new_status,
        )

        order.status = new_status

    def add_technical_report(self, order):
        return OrderTechnicalReport.objects.create(
            order=order,
            diagnosis="Diagnóstico de prueba.",
            repair_actions="Reparación de prueba.",
            result=OrderTechnicalReport.Result.REPARADO,
            technician=self.technician,
            created_by=self.admin,
            updated_by=self.admin,
        )

    def create_finished_order(
        self,
        with_report=True,
        final_status=ServiceOrder.Status.DELIVERED,
    ):
        order = self.create_order()

        self.change_status(
            order,
            ServiceOrder.Status.DIAGNOSIS,
            hours=1,
        )

        self.change_status(
            order,
            final_status,
            hours=3,
        )

        if with_report:
            self.add_technical_report(order)

        return order

    def test_no_orders_reports_no_candidates(self):
        output = self.run_evaluation()

        self.assertIn(
            "Órdenes registradas: 0",
            output,
        )

        self.assertIn(
            "Casos técnicamente candidatos: 0",
            output,
        )

        self.assertIn(
            "Casos reales validados para entrenamiento: "
            "NO DETERMINADO.",
            output,
        )

        self.assertIn(
            "NO ENTRENAR NI INTEGRAR",
            output,
        )

    def test_open_orders_are_not_training_candidates(self):
        first_order = self.create_order()

        self.change_status(
            first_order,
            ServiceOrder.Status.DIAGNOSIS,
            hours=1,
        )

        self.add_technical_report(first_order)

        self.create_order(
            equipment_type=Equipment.EquipmentType.NOTEBOOK,
        )

        output = self.run_evaluation()

        self.assertIn(
            "Órdenes registradas: 2",
            output,
        )

        self.assertIn(
            "Órdenes en estado final: 0",
            output,
        )

        self.assertIn(
            "Órdenes con informe técnico: 1",
            output,
        )

        self.assertIn(
            "Historiales válidos: 2",
            output,
        )

        self.assertIn(
            "Casos técnicamente candidatos: 0",
            output,
        )

    def test_finished_order_with_report_is_preliminary_candidate(self):
        self.create_finished_order()

        output = self.run_evaluation()

        self.assertIn(
            "Órdenes en estado final: 1",
            output,
        )

        self.assertIn(
            "Historiales válidos: 1",
            output,
        )

        self.assertIn(
            "Casos técnicamente candidatos: 1",
            output,
        )

        self.assertIn(
            "Procedencia operacional real: "
            "NO VERIFICABLE AUTOMÁTICAMENTE.",
            output,
        )

        self.assertIn(
            "NO ENTRENAR NI INTEGRAR",
            output,
        )

    def test_finished_order_without_report_is_not_candidate(self):
        self.create_finished_order(
            with_report=False,
        )

        output = self.run_evaluation()

        self.assertIn(
            "Órdenes en estado final: 1",
            output,
        )

        self.assertIn(
            "Órdenes con informe técnico: 0",
            output,
        )

        self.assertIn(
            "Casos técnicamente candidatos: 0",
            output,
        )

    def test_rejected_order_is_not_automatically_candidate(self):
        self.create_finished_order(
            final_status=ServiceOrder.Status.REJECTED,
        )

        output = self.run_evaluation()

        self.assertIn(
            "Órdenes rechazadas: 1",
            output,
        )

        self.assertIn(
            "Casos técnicamente candidatos: 0",
            output,
        )

        self.assertIn(
            "Las órdenes rechazadas requieren revisión",
            output,
        )

    def test_invalid_history_is_excluded(self):
        order = self.create_order()

        # Alteramos el estado sin agregar la transición.
        # Esto ocurre únicamente en la base de pruebas.
        ServiceOrder.objects.filter(
            pk=order.pk,
        ).update(
            status=ServiceOrder.Status.DIAGNOSIS,
        )

        output = self.run_evaluation()

        self.assertIn(
            "Historiales válidos: 0",
            output,
        )

        self.assertIn(
            "Historiales inválidos: 1",
            output,
        )

        self.assertIn(
            "Casos técnicamente candidatos: 0",
            output,
        )

    def test_reaching_preliminary_minimum_does_not_authorize_ml(self):
        self.create_finished_order()

        # Se reduce el mínimo solo para comprobar la lógica
        # de decisión. No modifica el mínimo normal de 30.
        output = self.run_evaluation(
            minimum=1,
        )

        self.assertIn(
            "Casos técnicamente candidatos: 1",
            output,
        )

        self.assertIn(
            "Se alcanzó el mínimo preliminar",
            output,
        )

        self.assertIn(
            "Casos reales validados para entrenamiento: "
            "NO DETERMINADO.",
            output,
        )

        self.assertIn(
            "NO ENTRENAR NI INTEGRAR",
            output,
        )

    def test_invalid_minimum_is_rejected(self):
        with self.assertRaisesRegex(
            CommandError,
            "mayor o igual a 1",
        ):
            self.run_evaluation(
                minimum=0,
            )

    def test_output_does_not_expose_customer_information(self):
        self.create_order()

        output = self.run_evaluation()

        self.assertNotIn(
            self.customer.name,
            output,
        )

        self.assertNotIn(
            self.customer.rut,
            output,
        )

        self.assertNotIn(
            self.customer.phone,
            output,
        )

        self.assertIn(
            "El comando muestra resultados agregados.",
            output,
        )

    def test_command_does_not_modify_registered_orders(self):
        order = self.create_order()

        initial_status = order.status
        initial_history_count = order.status_history.count()

        self.run_evaluation()

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            initial_status,
        )

        self.assertEqual(
            order.status_history.count(),
            initial_history_count,
        )

        self.assertEqual(
            ServiceOrder.objects.count(),
            1,
        )