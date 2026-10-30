from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment

from .models import (
    OrderReceptionReceipt,
    OrderReceptionReceiptDelivery,
    ServiceOrder,
)


class OrderReceptionReceiptTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_hu34",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tecnico_hu34",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="ayudante_hu34",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente HU34",
            phone="912345678",
            email="cliente.hu34@example.com",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model="Galaxy HU34",
            imei="123456789012345",
            color="Negro",
            observations="Dato interno del equipo.",
            created_by=self.admin,
        )

        self.client.force_authenticate(user=self.admin)

    def create_order(
        self,
        *,
        customer=None,
        equipment=None,
        reported_issue="Pantalla no enciende.",
        initial_observations="Equipo con marcas de uso.",
        received_accessories="Cargador y funda.",
        deposit_amount="15000.00",
    ):
        customer = customer or self.customer
        equipment = equipment or self.equipment

        response = self.client.post(
            reverse("service-order-list-create"),
            {
                "client": customer.pk,
                "equipment": equipment.pk,
                "reported_issue": reported_issue,
                "initial_observations": initial_observations,
                "received_accessories": received_accessories,
                "deposit_amount": deposit_amount,
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

    def receipt_url(self, order):
        return reverse(
            "order-reception-receipt",
            kwargs={"pk": order.pk},
        )

    def delivery_url(self, order):
        return reverse(
            "order-reception-receipt-delivery",
            kwargs={"pk": order.pk},
        )

    def test_order_keeps_single_tracking_code_for_receipt(self):
        order = self.create_order()

        response = self.client.post(
            self.receipt_url(order),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["tracking_code"],
            order.tracking_code,
        )

        self.assertEqual(
            response.data["snapshot"]["order"]["tracking_code"],
            order.tracking_code,
        )

        self.assertTrue(
            order.tracking_code.startswith("MC-")
        )

    def test_receipt_contains_expected_reception_snapshot(self):
        order = self.create_order()

        response = self.client.post(
            self.receipt_url(order),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        snapshot = response.data["snapshot"]

        self.assertEqual(
            snapshot["client"]["name"],
            self.customer.name,
        )
        self.assertEqual(
            snapshot["client"]["phone"],
            self.customer.phone,
        )
        self.assertEqual(
            snapshot["client"]["email"],
            self.customer.email,
        )

        self.assertEqual(
            snapshot["equipment"]["brand"],
            self.equipment.brand,
        )
        self.assertEqual(
            snapshot["equipment"]["model"],
            self.equipment.model,
        )
        self.assertEqual(
            snapshot["equipment"]["type"],
            self.equipment.equipment_type,
        )

        self.assertEqual(
            snapshot["reception"]["reported_issue"],
            "Pantalla no enciende.",
        )
        self.assertEqual(
            snapshot["reception"]["initial_observations"],
            "Equipo con marcas de uso.",
        )
        self.assertEqual(
            snapshot["reception"]["received_accessories"],
            "Cargador y funda.",
        )
        self.assertEqual(
            snapshot["reception"]["deposit_amount"],
            "15000.00",
        )
        self.assertEqual(
            snapshot["reception"]["received_by"],
            self.admin.username,
        )

        self.assertIn(
            "confirma la recepción",
            snapshot["reception"]["confirmation"],
        )

    def test_receipt_masks_equipment_identifier(self):
        order = self.create_order()

        response = self.client.post(
            self.receipt_url(order),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        equipment_snapshot = response.data["snapshot"]["equipment"]

        self.assertEqual(
            equipment_snapshot["identifier_label"],
            "IMEI",
        )
        self.assertEqual(
            equipment_snapshot["identifier"],
            "***********2345",
        )
        self.assertNotEqual(
            equipment_snapshot["identifier"],
            self.equipment.imei,
        )

    def test_existing_receipt_is_reused_without_changing_snapshot(self):
        order = self.create_order(
            reported_issue="Falla original.",
        )

        first_response = self.client.post(
            self.receipt_url(order),
            {},
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        receipt_id = first_response.data["id"]
        original_snapshot = first_response.data["snapshot"]

        update_response = self.client.patch(
            reverse(
                "service-order-detail",
                kwargs={"pk": order.pk},
            ),
            {
                "reported_issue": "Falla modificada después.",
            },
            format="json",
        )

        self.assertEqual(
            update_response.status_code,
            status.HTTP_200_OK,
        )

        second_response = self.client.post(
            self.receipt_url(order),
            {},
            format="json",
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            second_response.data["id"],
            receipt_id,
        )
        self.assertEqual(
            second_response.data["snapshot"],
            original_snapshot,
        )
        self.assertEqual(
            second_response.data["snapshot"]["reception"]["reported_issue"],
            "Falla original.",
        )

        self.assertEqual(
            OrderReceptionReceipt.objects.filter(
                order=order
            ).count(),
            1,
        )

    def test_get_receipt_returns_existing_receipt(self):
        order = self.create_order()

        create_response = self.client.post(
            self.receipt_url(order),
            {},
            format="json",
        )

        self.assertEqual(
            create_response.status_code,
            status.HTTP_201_CREATED,
        )

        get_response = self.client.get(
            self.receipt_url(order)
        )

        self.assertEqual(
            get_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            get_response.data["id"],
            create_response.data["id"],
        )

    def test_helper_cannot_generate_receipt(self):
        order = self.create_order()

        self.client.force_authenticate(
            user=self.helper
        )

        response = self.client.post(
            self.receipt_url(order),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_technician_can_generate_receipt(self):
        order = self.create_order()

        self.client.force_authenticate(
            user=self.technician
        )

        response = self.client.post(
            self.receipt_url(order),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        receipt = OrderReceptionReceipt.objects.get(
            order=order
        )

        self.assertEqual(
            receipt.generated_by,
            self.technician,
        )

    @patch(
        "orders.views.EmailMessage.send",
        return_value=1,
    )
    def test_email_delivery_sets_preferred_channel_and_history(
        self,
        mocked_send,
    ):
        order = self.create_order()

        response = self.client.post(
            self.delivery_url(order),
            {
                "delivery_method": (
                    OrderReceptionReceiptDelivery
                    .DeliveryMethod.EMAIL
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.preferred_notification_channel,
            ServiceOrder.NotificationChannel.EMAIL,
        )

        delivery = (
            OrderReceptionReceiptDelivery.objects
            .get(
                receipt__order=order,
                delivery_method=(
                    OrderReceptionReceiptDelivery
                    .DeliveryMethod.EMAIL
                ),
            )
        )

        self.assertEqual(
            delivery.status,
            OrderReceptionReceiptDelivery.DeliveryStatus.SENT,
        )
        self.assertEqual(
            delivery.destination,
            self.customer.email,
        )
        self.assertEqual(
            delivery.delivered_by,
            self.admin,
        )

        mocked_send.assert_called_once_with(
            using="default"
        )

    @patch(
        "orders.views.EmailMessage.send",
        side_effect=RuntimeError("SMTP no disponible"),
    )
    def test_email_failure_does_not_delete_order(
        self,
        mocked_send,
    ):
        order = self.create_order()

        response = self.client.post(
            self.delivery_url(order),
            {
                "delivery_method": (
                    OrderReceptionReceiptDelivery
                    .DeliveryMethod.EMAIL
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_502_BAD_GATEWAY,
        )

        self.assertTrue(
            ServiceOrder.objects.filter(
                pk=order.pk
            ).exists()
        )

        receipt = OrderReceptionReceipt.objects.get(
            order=order
        )

        delivery = receipt.deliveries.get(
            delivery_method=(
                OrderReceptionReceiptDelivery
                .DeliveryMethod.EMAIL
            )
        )

        self.assertEqual(
            delivery.status,
            OrderReceptionReceiptDelivery.DeliveryStatus.FAILED,
        )
        self.assertIn(
            "SMTP no disponible",
            delivery.detail,
        )

        mocked_send.assert_called_once_with(
            using="default"
        )

    def test_email_delivery_requires_registered_email(self):
        customer = Client.objects.create(
            rut="11.111.111-1",
            name="Cliente sin correo",
            phone="987654321",
            email="",
            created_by=self.admin,
        )

        equipment = Equipment.objects.create(
            client=customer,
            equipment_type=Equipment.EquipmentType.NOTEBOOK,
            brand="Lenovo",
            model="ThinkPad HU34",
            serial_number="SERIEHU34001",
            created_by=self.admin,
        )

        order = self.create_order(
            customer=customer,
            equipment=equipment,
        )

        response = self.client.post(
            self.delivery_url(order),
            {
                "delivery_method": (
                    OrderReceptionReceiptDelivery
                    .DeliveryMethod.EMAIL
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertFalse(
            OrderReceptionReceiptDelivery.objects.filter(
                receipt__order=order,
            ).exists()
        )

    def test_whatsapp_delivery_is_prepared_and_sets_preferred_channel(self):
        order = self.create_order()

        response = self.client.post(
            self.delivery_url(order),
            {
                "delivery_method": (
                    OrderReceptionReceiptDelivery
                    .DeliveryMethod.WHATSAPP
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.preferred_notification_channel,
            ServiceOrder.NotificationChannel.WHATSAPP,
        )

        self.assertIn(
            "https://wa.me/56912345678",
            response.data["whatsapp_url"],
        )
        self.assertIn(
            order.tracking_code,
            response.data["message"],
        )

        delivery = (
            OrderReceptionReceiptDelivery.objects
            .get(
                receipt__order=order,
                delivery_method=(
                    OrderReceptionReceiptDelivery
                    .DeliveryMethod.WHATSAPP
                ),
            )
        )

        self.assertEqual(
            delivery.status,
            OrderReceptionReceiptDelivery.DeliveryStatus.PREPARED,
        )
        self.assertEqual(
            delivery.destination,
            "56912345678",
        )

    def test_print_delivery_uses_email_as_default_notification_channel(self):
        order = self.create_order()

        response = self.client.post(
            self.delivery_url(order),
            {
                "delivery_method": (
                    OrderReceptionReceiptDelivery
                    .DeliveryMethod.PRINT
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.preferred_notification_channel,
            ServiceOrder.NotificationChannel.EMAIL,
        )

        delivery = (
            OrderReceptionReceiptDelivery.objects
            .get(
                receipt__order=order,
                delivery_method=(
                    OrderReceptionReceiptDelivery
                    .DeliveryMethod.PRINT
                ),
            )
        )

        self.assertEqual(
            delivery.status,
            OrderReceptionReceiptDelivery.DeliveryStatus.PRINTED,
        )
        self.assertEqual(
            delivery.destination,
            "",
        )

    def test_print_without_email_requires_whatsapp_preference(self):
        customer = Client.objects.create(
            rut="11.111.111-1",
            name="Cliente impresión HU34",
            phone="987654321",
            email="",
            created_by=self.admin,
        )

        equipment = Equipment.objects.create(
            client=customer,
            equipment_type=Equipment.EquipmentType.TABLET,
            brand="Apple",
            model="iPad HU34",
            serial_number="SERIEHU34002",
            created_by=self.admin,
        )

        order = self.create_order(
            customer=customer,
            equipment=equipment,
        )

        first_response = self.client.post(
            self.delivery_url(order),
            {
                "delivery_method": (
                    OrderReceptionReceiptDelivery
                    .DeliveryMethod.PRINT
                ),
            },
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        order.preferred_notification_channel = (
            ServiceOrder.NotificationChannel.WHATSAPP
        )
        order.save(
            update_fields=[
                "preferred_notification_channel",
                "updated_at",
            ]
        )

        second_response = self.client.post(
            self.delivery_url(order),
            {
                "delivery_method": (
                    OrderReceptionReceiptDelivery
                    .DeliveryMethod.PRINT
                ),
            },
            format="json",
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_201_CREATED,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.preferred_notification_channel,
            ServiceOrder.NotificationChannel.WHATSAPP,
        )

    def test_invalid_delivery_method_is_rejected(self):
        order = self.create_order()

        response = self.client.post(
            self.delivery_url(order),
            {
                "delivery_method": "SMS",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertFalse(
            OrderReceptionReceiptDelivery.objects.filter(
                receipt__order=order,
            ).exists()
        )
