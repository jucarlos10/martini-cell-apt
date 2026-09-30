from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment
from orders.financial_services import calculate_order_financials
from orders.models import OrderWarranty, ServiceOrder

from .models import (
    OrderPart,
    OrderPartCorrectionHistory,
    Part,
    Supplier,
)


class OrderPartCorrectionTests(APITestCase):
    """Pruebas de HU-24: corrección de repuestos en una orden."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_hu24",
            role=User.Role.ADMIN,
        )

        self.tech = User.objects.create_user(
            username="tech_hu24",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="helper_hu24",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="11.111.111-1",
            name="Cliente HU24",
            phone="911111111",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model="HU24",
            created_by=self.admin,
        )

        self.order = ServiceOrder.objects.create(
            client=self.customer,
            equipment=self.equipment,
            reported_issue="Prueba HU-24.",
            created_by=self.admin,
        )

        self.other_order = ServiceOrder.objects.create(
            client=self.customer,
            equipment=self.equipment,
            reported_issue="Otra orden HU-24.",
            created_by=self.admin,
        )

        self.supplier = Supplier.objects.create(
            name="Proveedor HU24",
        )

        self.part = Part.objects.create(
            name="Pantalla HU24",
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
                "note": "Uso inicial.",
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

        self.correction_url = reverse(
            "order-part-correction",
            kwargs={
                "order_id": self.order.pk,
                "order_part_id": self.usage.pk,
            },
        )

        self.history_url = reverse(
            "order-part-correction-history",
            kwargs={
                "order_id": self.order.pk,
                "order_part_id": self.usage.pk,
            },
        )

    def correct(self, field_name, new_value, reason="Corrección de prueba."):
        return self.client.post(
            self.correction_url,
            {
                "field_name": field_name,
                "new_value": new_value,
                "reason": reason,
            },
            format="json",
        )

    def test_admin_can_increase_quantity_and_stock_is_adjusted_once(self):
        response = self.correct("QUANTITY", "4")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(self.usage.quantity, 4)
        self.assertEqual(self.part.stock, 6)

        history = OrderPartCorrectionHistory.objects.get()
        self.assertEqual(history.field_name, "QUANTITY")
        self.assertEqual(history.old_value, "2")
        self.assertEqual(history.new_value, "4")
        self.assertEqual(history.changed_by, self.admin)

    def test_admin_can_decrease_quantity_and_stock_is_returned(self):
        response = self.correct("QUANTITY", "1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(self.usage.quantity, 1)
        self.assertEqual(self.part.stock, 9)

    def test_tech_can_correct_quantity(self):
        self.client.force_authenticate(user=self.tech)

        response = self.correct(
            "QUANTITY",
            "3",
            reason="Corrección realizada por técnico.",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(self.usage.quantity, 3)
        self.assertEqual(self.part.stock, 7)

        history = OrderPartCorrectionHistory.objects.get()
        self.assertEqual(history.changed_by, self.tech)

    def test_note_can_be_corrected_without_changing_stock(self):
        response = self.correct(
            "NOTE",
            "Nota corregida.",
            reason="La observación original estaba incompleta.",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(self.usage.note, "Nota corregida.")
        self.assertEqual(self.usage.quantity, 2)
        self.assertEqual(self.part.stock, 8)

        history = OrderPartCorrectionHistory.objects.get()
        self.assertEqual(history.field_name, "NOTE")
        self.assertEqual(history.old_value, "Uso inicial.")
        self.assertEqual(history.new_value, "Nota corregida.")

    def test_insufficient_stock_leaves_no_partial_changes(self):
        response = self.correct(
            "QUANTITY",
            "20",
            reason="Intento que debe fallar.",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["detail"],
            "Stock insuficiente.",
        )

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(self.usage.quantity, 2)
        self.assertEqual(self.part.stock, 8)
        self.assertEqual(
            OrderPartCorrectionHistory.objects.count(),
            0,
        )

    def test_helper_cannot_correct_usage(self):
        self.client.force_authenticate(user=self.helper)

        response = self.correct("QUANTITY", "3")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(self.usage.quantity, 2)
        self.assertEqual(self.part.stock, 8)
        self.assertEqual(
            OrderPartCorrectionHistory.objects.count(),
            0,
        )

    def test_usage_from_another_order_is_rejected(self):
        wrong_url = reverse(
            "order-part-correction",
            kwargs={
                "order_id": self.other_order.pk,
                "order_part_id": self.usage.pk,
            },
        )

        response = self.client.post(
            wrong_url,
            {
                "field_name": "QUANTITY",
                "new_value": "3",
                "reason": "Orden equivocada.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(self.usage.quantity, 2)
        self.assertEqual(self.part.stock, 8)

    def test_closed_order_rejects_correction(self):
        ServiceOrder.objects.filter(
            pk=self.order.pk
        ).update(
            status=ServiceOrder.Status.CLOSED
        )

        response = self.correct("QUANTITY", "3")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(self.usage.quantity, 2)
        self.assertEqual(self.part.stock, 8)

    def test_warranty_blocks_quantity_but_allows_note(self):
        OrderWarranty.objects.create(
            order=self.order,
            order_part=self.usage,
            warranty_type=OrderWarranty.WarrantyType.PART,
            is_applicable=False,
            created_by=self.admin,
        )

        quantity_response = self.correct(
            "QUANTITY",
            "3",
            reason="No debe modificar consumo con garantía.",
        )

        self.assertEqual(
            quantity_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        note_response = self.correct(
            "NOTE",
            "Nota administrativa corregida.",
            reason="Solo se corrige la nota.",
        )

        self.assertEqual(
            note_response.status_code,
            status.HTTP_200_OK,
        )

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(self.usage.quantity, 2)
        self.assertEqual(
            self.usage.note,
            "Nota administrativa corregida.",
        )
        self.assertEqual(self.part.stock, 8)

    def test_financial_parts_cost_uses_corrected_quantity(self):
        before = calculate_order_financials(self.order)

        self.assertEqual(
            before["parts_cost"],
            "30000.00",
        )

        response = self.correct(
            "QUANTITY",
            "3",
            reason="Cantidad registrada incorrectamente.",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        after = calculate_order_financials(self.order)

        self.assertEqual(
            after["parts_cost"],
            "45000.00",
        )

    def test_history_endpoint_returns_traceability(self):
        correction_response = self.correct(
            "NOTE",
            "Nota nueva.",
            reason="Corrección para validar historial.",
        )

        self.assertEqual(
            correction_response.status_code,
            status.HTTP_200_OK,
        )

        response = self.client.get(self.history_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        entry = response.data[0]

        self.assertEqual(entry["field_name"], "NOTE")
        self.assertEqual(entry["field_display"], "Nota")
        self.assertEqual(entry["old_value"], "Uso inicial.")
        self.assertEqual(entry["new_value"], "Nota nueva.")
        self.assertEqual(
            entry["reason"],
            "Corrección para validar historial.",
        )
        self.assertEqual(
            entry["changed_by_username"],
            self.admin.username,
        )
        self.assertEqual(
            entry["changed_by_role"],
            self.admin.role,
        )

        OrderPartCorrectionHistory.objects.filter(
            pk=entry["id"],
        ).update(changed_by=None)
        history_without_user = self.client.get(self.history_url)
        self.assertEqual(history_without_user.status_code, status.HTTP_200_OK)
        self.assertEqual(
            history_without_user.data[0]["changed_by_username"],
            self.admin.username,
        )
        self.assertEqual(
            history_without_user.data[0]["changed_by_role"],
            self.admin.role,
        )

    def test_same_value_is_rejected_without_history(self):
        response = self.correct(
            "QUANTITY",
            "2",
            reason="No existe cambio real.",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.usage.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(self.usage.quantity, 2)
        self.assertEqual(self.part.stock, 8)
        self.assertEqual(
            OrderPartCorrectionHistory.objects.count(),
            0,
        )
