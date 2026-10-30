from unittest.mock import patch

from django.test import override_settings
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
from .whatsapp_cloud import (
    WhatsAppCloudRequestError,
    WhatsAppSendResult,
)


class WhatsAppCloudReceptionReceiptTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_tec04_receipt",
            role=User.Role.ADMIN,
        )

        self.customer = Client.objects.create(
            rut="33.333.333-3",
            name="Cliente TEC04 Recepción",
            phone="912345678",
            email="cliente.recepcion.tec04@example.com",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model="Receipt Cloud",
            imei="323456789012345",
            color="Azul",
            observations="Dato interno del equipo.",
            created_by=self.admin,
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("service-order-list-create"),
            {
                "client": self.customer.pk,
                "equipment": self.equipment.pk,
                "reported_issue": "Pantalla dañada.",
                "initial_observations": "Observación privada.",
                "received_accessories": "Sin accesorios.",
                "deposit_amount": "10000.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.order = ServiceOrder.objects.get(
            pk=response.data["id"]
        )

    def delivery_url(self):
        return reverse(
            "order-reception-receipt-delivery",
            kwargs={"pk": self.order.pk},
        )

    def whatsapp_payload(self):
        return {
            "delivery_method": (
                OrderReceptionReceiptDelivery
                .DeliveryMethod.WHATSAPP
            ),
        }

    @override_settings(
        WHATSAPP_CLOUD_API_ENABLED=True,
        WHATSAPP_CLOUD_FALLBACK_TO_WA_ME=True,
        WHATSAPP_TEMPLATE_RECEPTION="martini_recepcion_orden",
        WHATSAPP_TEMPLATE_LANGUAGE="es_CL",
    )
    @patch("orders.views.send_template_message")
    def test_reception_receipt_sends_cloud_template_successfully(
        self,
        mocked_send,
    ):
        mocked_send.return_value = WhatsAppSendResult(
            message_id="wamid.RECEIPT-001",
            destination="56912345678",
            template_name="martini_recepcion_orden",
        )

        response = self.client.post(
            self.delivery_url(),
            self.whatsapp_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.preferred_notification_channel,
            ServiceOrder.NotificationChannel.WHATSAPP,
        )

        receipt = OrderReceptionReceipt.objects.get(
            order=self.order,
        )

        delivery = OrderReceptionReceiptDelivery.objects.get(
            receipt=receipt,
            delivery_method=(
                OrderReceptionReceiptDelivery
                .DeliveryMethod.WHATSAPP
            ),
        )

        self.assertEqual(
            delivery.status,
            OrderReceptionReceiptDelivery.DeliveryStatus.SENT,
        )
        self.assertEqual(
            delivery.destination,
            "56912345678",
        )
        self.assertIn(
            "WhatsApp Cloud API",
            delivery.detail,
        )
        self.assertIn(
            "wamid.RECEIPT-001",
            delivery.detail,
        )

        self.assertEqual(
            response.data["delivery"]["status"],
            OrderReceptionReceiptDelivery.DeliveryStatus.SENT,
        )
        self.assertEqual(
            response.data["whatsapp_url"],
            "",
        )
        self.assertEqual(
            response.data["message"],
            "",
        )

        mocked_send.assert_called_once()

        call_kwargs = mocked_send.call_args.kwargs

        self.assertEqual(
            call_kwargs["to"],
            "56912345678",
        )
        self.assertEqual(
            call_kwargs["template_name"],
            "martini_recepcion_orden",
        )
        self.assertEqual(
            call_kwargs["body_parameters"],
            [
                self.order.tracking_code,
            ],
        )
        self.assertEqual(
            call_kwargs["language_code"],
            "es_CL",
        )

    @override_settings(
        WHATSAPP_CLOUD_API_ENABLED=True,
        WHATSAPP_CLOUD_FALLBACK_TO_WA_ME=True,
        WHATSAPP_TEMPLATE_RECEPTION="martini_recepcion_orden",
        WHATSAPP_TEMPLATE_LANGUAGE="es_CL",
    )
    @patch("orders.views.send_template_message")
    def test_reception_cloud_failure_uses_manual_fallback(
        self,
        mocked_send,
    ):
        mocked_send.side_effect = WhatsAppCloudRequestError(
            "Meta temporalmente no disponible."
        )

        response = self.client.post(
            self.delivery_url(),
            self.whatsapp_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.preferred_notification_channel,
            ServiceOrder.NotificationChannel.WHATSAPP,
        )

        receipt = OrderReceptionReceipt.objects.get(
            order=self.order,
        )

        delivery = OrderReceptionReceiptDelivery.objects.get(
            receipt=receipt,
            delivery_method=(
                OrderReceptionReceiptDelivery
                .DeliveryMethod.WHATSAPP
            ),
        )

        self.assertEqual(
            delivery.status,
            OrderReceptionReceiptDelivery.DeliveryStatus.PREPARED,
        )
        self.assertIn(
            "respaldo manual",
            delivery.detail,
        )
        self.assertIn(
            "Meta temporalmente no disponible",
            delivery.detail,
        )
        self.assertIn(
            "https://wa.me/56912345678",
            response.data["whatsapp_url"],
        )
        self.assertIn(
            self.order.tracking_code,
            response.data["message"],
        )

    @override_settings(
        WHATSAPP_CLOUD_API_ENABLED=True,
        WHATSAPP_CLOUD_FALLBACK_TO_WA_ME=False,
        WHATSAPP_TEMPLATE_RECEPTION="martini_recepcion_orden",
        WHATSAPP_TEMPLATE_LANGUAGE="es_CL",
    )
    @patch("orders.views.send_template_message")
    def test_reception_cloud_failure_without_fallback_records_failed(
        self,
        mocked_send,
    ):
        mocked_send.side_effect = WhatsAppCloudRequestError(
            "Meta rechazó el envío."
        )

        response = self.client.post(
            self.delivery_url(),
            self.whatsapp_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_502_BAD_GATEWAY,
        )

        self.assertTrue(
            ServiceOrder.objects.filter(
                pk=self.order.pk
            ).exists()
        )

        self.assertTrue(
            OrderReceptionReceipt.objects.filter(
                order=self.order,
            ).exists()
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.preferred_notification_channel,
            ServiceOrder.NotificationChannel.WHATSAPP,
        )

        receipt = OrderReceptionReceipt.objects.get(
            order=self.order,
        )

        delivery = OrderReceptionReceiptDelivery.objects.get(
            receipt=receipt,
            delivery_method=(
                OrderReceptionReceiptDelivery
                .DeliveryMethod.WHATSAPP
            ),
        )

        self.assertEqual(
            delivery.status,
            OrderReceptionReceiptDelivery.DeliveryStatus.FAILED,
        )
        self.assertEqual(
            delivery.destination,
            "56912345678",
        )
        self.assertIn(
            "WhatsApp Cloud API",
            delivery.detail,
        )
        self.assertIn(
            "Meta rechazó el envío",
            delivery.detail,
        )

        self.assertEqual(
            response.data["delivery"]["status"],
            OrderReceptionReceiptDelivery.DeliveryStatus.FAILED,
        )
