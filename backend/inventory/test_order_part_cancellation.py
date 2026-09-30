from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment
from orders.financial_services import calculate_order_financials
from orders.models import OrderWarranty, ServiceOrder

from .models import OrderPart, Part, Supplier


class OrderPartCancellationTests(APITestCase):
    """Pruebas de HU-25: anulación de repuestos en una orden."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_hu25",
            role=User.Role.ADMIN,
        )

        self.tech = User.objects.create_user(
            username="tech_hu25",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="helper_hu25",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="22.222.222-2",
            name="Cliente HU25",
            phone="922222222",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Motorola",
            model="HU25",
            created_by=self.admin,
        )

        self.order = ServiceOrder.objects.create(
            client=self.customer,
            equipment=self.equipment,
            reported_issue="Prueba HU-25.",
            created_by=self.admin,
        )

        self.other_order = ServiceOrder.objects.create(
            client=self.customer,
            equipment=self.equipment,
            reported_issue="Otra orden HU-25.",
            created_by=self.admin,
        )

        self.supplier = Supplier.objects.create(
            name="Proveedor HU25",
        )

        self.part = Part.objects.create(
            name="Batería HU25",
            supplier=self.supplier,
            unit_cost=Decimal("15000.00"),
            stock=10,
        )

        self.client.force_authenticate(user=self.admin)

        register_response = self.client.post(
            reverse(
                "order-parts",
                kwargs={"order_id": self.order.pk},
            ),
            {
                "part": self.part.pk,
                "quantity": 2,
                "note": "Uso inicial HU25.",
            },
            format="json",
        )

        self.assertEqual(
            register_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.usage = OrderPart.objects.get(
            pk=register_response.data["id"]
        )

        self.cancellation_url = reverse(
            "order-part-cancellation",
            kwargs={
                "order_id": self.order.pk,
                "order_part_id": self.usage.pk,
            },
        )

        self.correction_url = reverse(
            "order-part-correction",
            kwargs={
                "order_id": self.order.pk,
                "order_part_id": self.usage.pk,
            },
        )

    def cancel(self, reason="Repuesto asociado por error."):
        return self.client.post(
            self.cancellation_url,
            {"reason": reason},
            format="json",
        )

    def test_admin_can_cancel_usage_and_stock_returns_once(self):
        response = self.cancel(
            reason="El repuesto fue asociado a la orden equivocada."
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertTrue(self.usage.is_cancelled)
        self.assertEqual(
            self.usage.cancellation_reason,
            "El repuesto fue asociado a la orden equivocada.",
        )
        self.assertEqual(self.usage.cancelled_by, self.admin)
        self.assertEqual(
            self.usage.cancelled_by_username,
            self.admin.username,
        )
        self.assertEqual(
            self.usage.cancelled_by_role,
            self.admin.role,
        )
        self.assertIsNotNone(self.usage.cancelled_at)
        self.assertEqual(self.part.stock, 10)

        self.assertTrue(response.data["used_part"]["is_cancelled"])
        self.assertEqual(
            response.data["used_part"]["cancellation_reason"],
            "El repuesto fue asociado a la orden equivocada.",
        )

    def test_tech_can_cancel_usage(self):
        self.client.force_authenticate(user=self.tech)

        response = self.cancel(
            reason="Anulación realizada por técnico."
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertTrue(self.usage.is_cancelled)
        self.assertEqual(self.usage.cancelled_by, self.tech)
        self.assertEqual(
            self.usage.cancelled_by_username,
            self.tech.username,
        )
        self.assertEqual(self.part.stock, 10)

    def test_double_cancellation_does_not_return_stock_twice(self):
        first_response = self.cancel(
            reason="Primera anulación válida."
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
        )

        self.part.refresh_from_db()
        self.assertEqual(self.part.stock, 10)

        second_response = self.cancel(
            reason="Segundo intento no permitido."
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertTrue(self.usage.is_cancelled)
        self.assertEqual(self.part.stock, 10)
        self.assertEqual(
            self.usage.cancellation_reason,
            "Primera anulación válida.",
        )

    def test_reason_is_required_without_partial_changes(self):
        response = self.client.post(
            self.cancellation_url,
            {"reason": "   "},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertFalse(self.usage.is_cancelled)
        self.assertEqual(self.usage.cancellation_reason, "")
        self.assertIsNone(self.usage.cancelled_at)
        self.assertEqual(self.part.stock, 8)

    def test_helper_cannot_cancel_usage(self):
        self.client.force_authenticate(user=self.helper)

        response = self.cancel()

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertFalse(self.usage.is_cancelled)
        self.assertEqual(self.part.stock, 8)

    def test_usage_from_another_order_is_rejected(self):
        wrong_url = reverse(
            "order-part-cancellation",
            kwargs={
                "order_id": self.other_order.pk,
                "order_part_id": self.usage.pk,
            },
        )

        response = self.client.post(
            wrong_url,
            {"reason": "Orden equivocada."},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertFalse(self.usage.is_cancelled)
        self.assertEqual(self.part.stock, 8)

    def test_closed_order_rejects_cancellation(self):
        ServiceOrder.objects.filter(
            pk=self.order.pk
        ).update(
            status=ServiceOrder.Status.CLOSED
        )

        response = self.cancel()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertFalse(self.usage.is_cancelled)
        self.assertEqual(self.part.stock, 8)

    def test_delivered_order_rejects_cancellation(self):
        ServiceOrder.objects.filter(
            pk=self.order.pk
        ).update(
            status=ServiceOrder.Status.DELIVERED
        )

        response = self.cancel()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertFalse(self.usage.is_cancelled)
        self.assertEqual(self.part.stock, 8)

    def test_warranty_blocks_cancellation(self):
        OrderWarranty.objects.create(
            order=self.order,
            order_part=self.usage,
            warranty_type=OrderWarranty.WarrantyType.PART,
            is_applicable=False,
            created_by=self.admin,
        )

        response = self.cancel(
            reason="No debe anularse por garantía asociada."
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertFalse(self.usage.is_cancelled)
        self.assertEqual(self.part.stock, 8)

    def test_cancelled_usage_is_excluded_from_current_financial_cost(self):
        before = calculate_order_financials(self.order)

        self.assertEqual(
            before["parts_cost"],
            "30000.00",
        )

        response = self.cancel(
            reason="Consumo registrado por error."
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        after = calculate_order_financials(self.order)

        self.assertEqual(
            after["parts_cost"],
            "0.00",
        )

    def test_cancelled_usage_cannot_be_corrected(self):
        cancellation_response = self.cancel(
            reason="El uso deja de estar vigente."
        )

        self.assertEqual(
            cancellation_response.status_code,
            status.HTTP_200_OK,
        )

        correction_response = self.client.post(
            self.correction_url,
            {
                "field_name": "NOTE",
                "new_value": "No debe cambiar.",
                "reason": "Intento posterior a la anulación.",
            },
            format="json",
        )

        self.assertEqual(
            correction_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(self.usage.note, "Uso inicial HU25.")
        self.assertTrue(self.usage.is_cancelled)
        self.assertEqual(self.part.stock, 10)
