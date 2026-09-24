from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment

from .models import (
    OrderStatusHistory,
    OrderTechnicalReport,
    OrderTechnicalReportHistory,
    ServiceOrder,
)


class ServiceOrderStatusTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_prueba",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tecnico_prueba",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="ayudante_prueba",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente de pruebas",
            phone="912345678",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.NOTEBOOK,
            brand="Lenovo",
            model="Equipo de pruebas",
            created_by=self.admin,
        )

        self.client.force_authenticate(user=self.admin)

    def create_order(self):
        response = self.client.post(
            reverse("service-order-list-create"),
            {
                "client": self.customer.id,
                "equipment": self.equipment.id,
                "reported_issue": "Falla utilizada para pruebas.",
                "initial_observations": "Orden de prueba.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        return ServiceOrder.objects.get(
            pk=response.data["id"]
        )

    def create_technical_report(self, order):
        response = self.client.post(
            reverse(
                "order-technical-report",
                kwargs={"pk": order.pk},
            ),
            {
                "diagnosis": "Diagnóstico original.",
                "repair_actions": "Revisión del equipo.",
                "repair_observations": "Sin observaciones adicionales.",
                "parts_description": "",
                "result": OrderTechnicalReport.Result.REPARADO,
                "technician": self.technician.pk,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        return OrderTechnicalReport.objects.get(
            order=order
        )

    def test_new_order_creates_initial_history(self):
        order = self.create_order()

        self.assertEqual(
            order.status,
            ServiceOrder.Status.RECEIVED,
        )

        history = list(
            OrderStatusHistory.objects.filter(order=order)
        )

        self.assertEqual(len(history), 1)
        self.assertIsNone(history[0].from_status)
        self.assertEqual(
            history[0].to_status,
            ServiceOrder.Status.RECEIVED,
        )
        self.assertEqual(
            history[0].changed_by,
            self.admin,
        )

    def test_technician_can_make_valid_transition(self):
        order = self.create_order()

        self.client.force_authenticate(
            user=self.technician
        )

        response = self.client.patch(
            reverse(
                "order-status",
                kwargs={"pk": order.pk},
            ),
            {
                "status": ServiceOrder.Status.DIAGNOSIS,
                "note": "Inicio de diagnóstico.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            ServiceOrder.Status.DIAGNOSIS,
        )

        history = list(
            order.status_history.order_by("changed_at", "id")
        )

        self.assertEqual(len(history), 2)
        self.assertEqual(
            history[1].from_status,
            ServiceOrder.Status.RECEIVED,
        )
        self.assertEqual(
            history[1].to_status,
            ServiceOrder.Status.DIAGNOSIS,
        )
        self.assertEqual(
            history[1].changed_by,
            self.technician,
        )

    def test_invalid_transition_preserves_status_and_history(self):
        order = self.create_order()

        response = self.client.patch(
            reverse(
                "order-status",
                kwargs={"pk": order.pk},
            ),
            {
                "status": ServiceOrder.Status.READY,
                "note": "Intento de salto de estado.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            ServiceOrder.Status.RECEIVED,
        )
        self.assertEqual(
            order.status_history.count(),
            1,
        )

    def test_general_patch_cannot_change_status(self):
        order = self.create_order()

        response = self.client.patch(
            reverse(
                "service-order-detail",
                kwargs={"pk": order.pk},
            ),
            {
                "status": ServiceOrder.Status.CLOSED,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            ServiceOrder.Status.RECEIVED,
        )
        self.assertEqual(
            order.status_history.count(),
            1,
        )

    def test_helper_can_read_but_cannot_change_status(self):
        order = self.create_order()

        self.client.force_authenticate(
            user=self.helper
        )

        status_url = reverse(
            "order-status",
            kwargs={"pk": order.pk},
        )

        read_response = self.client.get(status_url)

        self.assertEqual(
            read_response.status_code,
            status.HTTP_200_OK,
        )

        change_response = self.client.patch(
            status_url,
            {
                "status": ServiceOrder.Status.DIAGNOSIS,
            },
            format="json",
        )

        self.assertEqual(
            change_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            ServiceOrder.Status.RECEIVED,
        )
        self.assertEqual(
            order.status_history.count(),
            1,
        )

    def test_delivered_and_closed_orders_reject_new_report(self):
        for final_status in (
            ServiceOrder.Status.DELIVERED,
            ServiceOrder.Status.CLOSED,
        ):
            with self.subTest(final_status=final_status):
                order = self.create_order()

                # Preparamos el estado final solo en la base
                # de datos de prueba.
                ServiceOrder.objects.filter(
                    pk=order.pk
                ).update(
                    status=final_status
                )

                response = self.client.post(
                    reverse(
                        "order-technical-report",
                        kwargs={"pk": order.pk},
                    ),
                    {
                        "diagnosis": "Diagnóstico de prueba.",
                        "repair_actions": "Revisión del equipo.",
                        "result": (
                            OrderTechnicalReport.Result.REPARADO
                        ),
                        "technician": self.technician.pk,
                    },
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

                self.assertFalse(
                    OrderTechnicalReport.objects.filter(
                        order=order
                    ).exists()
                )

    def test_delivered_and_closed_orders_reject_report_changes(self):
        for final_status in (
            ServiceOrder.Status.DELIVERED,
            ServiceOrder.Status.CLOSED,
        ):
            with self.subTest(final_status=final_status):
                order = self.create_order()
                report = self.create_technical_report(order)

                self.assertEqual(
                    OrderTechnicalReportHistory.objects.filter(
                        report=report
                    ).count(),
                    1,
                )

                # Simulamos un estado final sin afectar
                # las órdenes reales del proyecto.
                ServiceOrder.objects.filter(
                    pk=order.pk
                ).update(
                    status=final_status
                )

                report_url = reverse(
                    "order-technical-report",
                    kwargs={"pk": order.pk},
                )

                response = self.client.patch(
                    report_url,
                    {
                        "diagnosis": (
                            "Intento de modificar el diagnóstico."
                        ),
                    },
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

                report.refresh_from_db()

                self.assertEqual(
                    report.diagnosis,
                    "Diagnóstico original.",
                )

                self.assertEqual(
                    OrderTechnicalReportHistory.objects.filter(
                        report=report
                    ).count(),
                    1,
                )

                # El informe sigue disponible para consulta.
                read_response = self.client.get(
                    report_url
                )

                self.assertEqual(
                    read_response.status_code,
                    status.HTTP_200_OK,
                )