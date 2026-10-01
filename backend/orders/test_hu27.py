from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment

from .models import OrderSensitiveChangeHistory, ServiceOrder


class OrderSensitiveChangeHistoryTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_hu27",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tecnico_hu27",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="ayudante_hu27",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente HU27 Alfa",
            phone="912345678",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.other_customer = Client.objects.create(
            rut="11.111.111-1",
            name="Cliente HU27 Beta",
            phone="923456789",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Marca Alfa",
            model="Modelo Uno",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.same_customer_equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.NOTEBOOK,
            brand="Marca Alfa",
            model="Modelo Dos",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.other_equipment = Equipment.objects.create(
            client=self.other_customer,
            equipment_type=Equipment.EquipmentType.NOTEBOOK,
            brand="Marca Beta",
            model="Modelo Tres",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.client.force_authenticate(user=self.admin)

        self.order = self.create_order()

    def create_order(self):
        response = self.client.post(
            reverse("service-order-list-create"),
            {
                "client": self.customer.pk,
                "equipment": self.equipment.pk,
                "reported_issue": "Falla inicial HU-27.",
                "initial_observations": "Observación inicial HU-27.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        return ServiceOrder.objects.get(pk=response.data["id"])

    def detail_url(self):
        return reverse(
            "service-order-detail",
            kwargs={"pk": self.order.pk},
        )

    def sensitive_history_url(self):
        return reverse(
            "order-sensitive-change-history",
            kwargs={"pk": self.order.pk},
        )

    def test_reported_issue_change_is_audited(self):
        response = self.client.patch(
            self.detail_url(),
            {
                "reported_issue": "Falla actualizada HU-27.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.reported_issue,
            "Falla actualizada HU-27.",
        )

        history = OrderSensitiveChangeHistory.objects.get(
            order=self.order
        )

        self.assertEqual(
            history.field,
            OrderSensitiveChangeHistory.Field.REPORTED_ISSUE,
        )
        self.assertEqual(
            history.old_value,
            "Falla inicial HU-27.",
        )
        self.assertEqual(
            history.new_value,
            "Falla actualizada HU-27.",
        )
        self.assertEqual(history.reason, "")
        self.assertEqual(history.changed_by, self.admin)
        self.assertEqual(
            history.changed_by_username,
            self.admin.username,
        )
        self.assertEqual(
            history.changed_by_role,
            User.Role.ADMIN,
        )

    def test_initial_observations_change_is_audited_by_technician(self):
        self.client.force_authenticate(user=self.technician)

        response = self.client.patch(
            self.detail_url(),
            {
                "initial_observations": (
                    "Observación modificada por técnico."
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        history = OrderSensitiveChangeHistory.objects.get(
            order=self.order
        )

        self.assertEqual(
            history.field,
            OrderSensitiveChangeHistory.Field.INITIAL_OBSERVATIONS,
        )
        self.assertEqual(
            history.changed_by,
            self.technician,
        )
        self.assertEqual(
            history.changed_by_username,
            self.technician.username,
        )
        self.assertEqual(
            history.changed_by_role,
            User.Role.TECH,
        )

    def test_equipment_change_requires_reason(self):
        response = self.client.patch(
            self.detail_url(),
            {
                "equipment": self.same_customer_equipment.pk,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("change_reason", response.data)

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.equipment,
            self.equipment,
        )
        self.assertFalse(
            OrderSensitiveChangeHistory.objects.filter(
                order=self.order
            ).exists()
        )

    def test_equipment_change_with_reason_is_audited(self):
        reason = "Equipo corregido tras revisión de recepción."

        response = self.client.patch(
            self.detail_url(),
            {
                "equipment": self.same_customer_equipment.pk,
                "change_reason": reason,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.equipment,
            self.same_customer_equipment,
        )

        history = OrderSensitiveChangeHistory.objects.get(
            order=self.order
        )

        self.assertEqual(
            history.field,
            OrderSensitiveChangeHistory.Field.EQUIPMENT,
        )
        self.assertEqual(
            history.old_value,
            {
                "id": self.equipment.pk,
                "description": "Marca Alfa Modelo Uno",
            },
        )
        self.assertEqual(
            history.new_value,
            {
                "id": self.same_customer_equipment.pk,
                "description": "Marca Alfa Modelo Dos",
            },
        )
        self.assertEqual(history.reason, reason)

    def test_client_and_equipment_change_with_reason_creates_two_entries(self):
        reason = "Corrección de asociación registrada en recepción."

        response = self.client.patch(
            self.detail_url(),
            {
                "client": self.other_customer.pk,
                "equipment": self.other_equipment.pk,
                "change_reason": reason,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.client,
            self.other_customer,
        )
        self.assertEqual(
            self.order.equipment,
            self.other_equipment,
        )

        history = OrderSensitiveChangeHistory.objects.filter(
            order=self.order
        ).order_by("id")

        self.assertEqual(history.count(), 2)

        client_history = history.get(
            field=OrderSensitiveChangeHistory.Field.CLIENT
        )
        equipment_history = history.get(
            field=OrderSensitiveChangeHistory.Field.EQUIPMENT
        )

        self.assertEqual(
            client_history.old_value,
            {
                "id": self.customer.pk,
                "name": self.customer.name,
            },
        )
        self.assertEqual(
            client_history.new_value,
            {
                "id": self.other_customer.pk,
                "name": self.other_customer.name,
            },
        )
        self.assertEqual(client_history.reason, reason)

        self.assertEqual(
            equipment_history.old_value,
            {
                "id": self.equipment.pk,
                "description": "Marca Alfa Modelo Uno",
            },
        )
        self.assertEqual(
            equipment_history.new_value,
            {
                "id": self.other_equipment.pk,
                "description": "Marca Beta Modelo Tres",
            },
        )
        self.assertEqual(equipment_history.reason, reason)

    def test_same_value_does_not_create_audit_entry(self):
        response = self.client.patch(
            self.detail_url(),
            {
                "reported_issue": self.order.reported_issue,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertFalse(
            OrderSensitiveChangeHistory.objects.filter(
                order=self.order
            ).exists()
        )

    def test_helper_cannot_modify_sensitive_order_data(self):
        self.client.force_authenticate(user=self.helper)

        response = self.client.patch(
            self.detail_url(),
            {
                "reported_issue": "Cambio que no debe aplicarse.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.reported_issue,
            "Falla inicial HU-27.",
        )
        self.assertFalse(
            OrderSensitiveChangeHistory.objects.filter(
                order=self.order
            ).exists()
        )

    def test_delivered_and_closed_orders_are_immutable(self):
        for order_status in (
            ServiceOrder.Status.DELIVERED,
            ServiceOrder.Status.CLOSED,
        ):
            with self.subTest(order_status=order_status):
                ServiceOrder.objects.filter(
                    pk=self.order.pk
                ).update(status=order_status)

                self.order.refresh_from_db()

                response = self.client.patch(
                    self.detail_url(),
                    {
                        "reported_issue": (
                            f"Cambio rechazado en {order_status}."
                        ),
                    },
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

                self.order.refresh_from_db()

                self.assertEqual(
                    self.order.reported_issue,
                    "Falla inicial HU-27.",
                )
                self.assertFalse(
                    OrderSensitiveChangeHistory.objects.filter(
                        order=self.order
                    ).exists()
                )

    def test_admin_can_read_sensitive_change_history(self):
        self.client.patch(
            self.detail_url(),
            {
                "reported_issue": "Falla auditada para consulta.",
            },
            format="json",
        )

        response = self.client.get(
            self.sensitive_history_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["field"],
            OrderSensitiveChangeHistory.Field.REPORTED_ISSUE,
        )
        self.assertEqual(
            response.data[0]["old_value"],
            "Falla inicial HU-27.",
        )
        self.assertEqual(
            response.data[0]["new_value"],
            "Falla auditada para consulta.",
        )
        self.assertEqual(
            response.data[0]["changed_by_username"],
            self.admin.username,
        )

    def test_technician_can_read_sensitive_change_history(self):
        self.client.patch(
            self.detail_url(),
            {
                "reported_issue": "Cambio visible para técnico.",
            },
            format="json",
        )

        self.client.force_authenticate(user=self.technician)

        response = self.client.get(
            self.sensitive_history_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 1)

    def test_helper_cannot_read_sensitive_change_history(self):
        self.client.patch(
            self.detail_url(),
            {
                "reported_issue": "Cambio privado de auditoría.",
            },
            format="json",
        )

        self.client.force_authenticate(user=self.helper)

        response = self.client.get(
            self.sensitive_history_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_anonymous_user_cannot_read_sensitive_change_history(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.sensitive_history_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_audit_endpoint_does_not_allow_delete(self):
        self.client.patch(
            self.detail_url(),
            {
                "reported_issue": "Cambio que debe conservarse.",
            },
            format="json",
        )

        self.assertEqual(
            OrderSensitiveChangeHistory.objects.filter(
                order=self.order
            ).count(),
            1,
        )

        response = self.client.delete(
            self.sensitive_history_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            OrderSensitiveChangeHistory.objects.filter(
                order=self.order
            ).count(),
            1,
        )

    def test_change_and_audit_are_atomic(self):
        original_issue = self.order.reported_issue

        with patch(
            "orders.serializers."
            "OrderSensitiveChangeHistory.objects.create",
            side_effect=RuntimeError(
                "Fallo simulado al crear auditoría HU-27."
            ),
        ):
            with self.assertRaises(RuntimeError):
                self.client.patch(
                    self.detail_url(),
                    {
                        "reported_issue": (
                            "Este cambio debe revertirse."
                        ),
                    },
                    format="json",
                )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.reported_issue,
            original_issue,
        )
        self.assertFalse(
            OrderSensitiveChangeHistory.objects.filter(
                order=self.order
            ).exists()
        )

    def test_nonexistent_order_sensitive_history_returns_404(self):
        response = self.client.get(
            reverse(
                "order-sensitive-change-history",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
