from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment

from .models import OrderSensitiveChangeHistory, ServiceOrder


class IntakePriceTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_recepcion",
            role=User.Role.ADMIN,
        )
        self.client.force_authenticate(user=self.admin)
        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente de ensayo",
            phone="912345678",
            created_by=self.admin,
        )
        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Marca",
            model="Modelo de ensayo",
            created_by=self.admin,
        )

    def create_order(self, **fields):
        return self.client.post(
            reverse("service-order-list-create"),
            {
                "client": self.customer.pk,
                "equipment": self.equipment.pk,
                "reported_issue": "Pantalla no enciende.",
                **fields,
            },
            format="json",
        )

    def test_intake_price_is_recorded_without_becoming_final_charge_or_public_data(self):
        response = self.create_order(intake_price="35000")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["intake_price"], "35000.00")
        self.assertEqual(response.data["client_phone"], "912345678")

        order = ServiceOrder.objects.get(pk=response.data["id"])
        self.assertEqual(order.intake_price, Decimal("35000.00"))

        financial = self.client.get(
            reverse("order-financial", kwargs={"pk": order.pk})
        )
        self.assertEqual(financial.status_code, status.HTTP_200_OK)
        self.assertIsNone(financial.data["price_charged"])

        self.client.force_authenticate(user=None)
        public = self.client.get(
            reverse("public-order-status", kwargs={"tracking_code": order.tracking_code})
        )
        self.assertEqual(public.status_code, status.HTTP_200_OK)
        self.assertNotIn("intake_price", public.data)
        self.assertNotIn("client_phone", public.data)
        self.assertNotIn("client_name", public.data)

    def test_price_correction_requires_reason_and_is_audited(self):
        response = self.create_order(intake_price="35000")
        order = ServiceOrder.objects.get(pk=response.data["id"])
        detail = reverse("service-order-detail", kwargs={"pk": order.pk})

        missing_reason = self.client.patch(detail, {"intake_price": "39000"}, format="json")
        self.assertEqual(missing_reason.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(order.sensitive_change_history.count(), 0)

        correction = self.client.patch(
            detail,
            {"intake_price": "39000", "change_reason": "Corrección de la cotización inicial."},
            format="json",
        )
        self.assertEqual(correction.status_code, status.HTTP_200_OK)
        history = OrderSensitiveChangeHistory.objects.get(order=order)
        self.assertEqual(history.field, OrderSensitiveChangeHistory.Field.INTAKE_PRICE)
        self.assertEqual(history.old_value, "35000.00")
        self.assertEqual(history.new_value, "39000.00")
        self.assertEqual(history.changed_by, self.admin)

    def test_negative_intake_price_is_rejected(self):
        response = self.create_order(intake_price="-1")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ServiceOrder.objects.count(), 0)

    def test_price_may_remain_unconfirmed(self):
        response = self.create_order()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["intake_price"])

    def test_order_and_receipt_data_work_with_client_without_rut(self):
        self.customer.rut = None
        self.customer.save(update_fields=["rut"])

        response = self.create_order(intake_price="35000")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["client_name"], "Cliente de ensayo")
        self.assertEqual(response.data["client_phone"], "912345678")
        self.assertEqual(response.data["intake_price"], "35000.00")
