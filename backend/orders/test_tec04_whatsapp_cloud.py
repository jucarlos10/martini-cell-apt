import json
from io import BytesIO
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment

from .models import (
    OrderStatusNotification,
    ServiceOrder,
)
from .whatsapp_cloud import (
    WhatsAppCloudConfigurationError,
    WhatsAppCloudRequestError,
    WhatsAppSendResult,
    send_template_message,
)


class WhatsAppCloudServiceTests(SimpleTestCase):

    @override_settings(
        WHATSAPP_CLOUD_API_ENABLED=True,
        WHATSAPP_CLOUD_API_BASE_URL="https://graph.facebook.com",
        WHATSAPP_CLOUD_API_VERSION="v99.0",
        WHATSAPP_CLOUD_PHONE_NUMBER_ID="123456789",
        WHATSAPP_CLOUD_ACCESS_TOKEN="token-secreto-de-prueba",
        WHATSAPP_CLOUD_TIMEOUT=10,
        WHATSAPP_TEMPLATE_LANGUAGE="es_CL",
    )
    @patch("orders.whatsapp_cloud.urlopen")
    def test_send_template_message_returns_meta_message_id(
        self,
        mocked_urlopen,
    ):
        response = MagicMock()
        response.status = 200
        response.read.return_value = json.dumps(
            {
                "messaging_product": "whatsapp",
                "contacts": [
                    {
                        "input": "56912345678",
                        "wa_id": "56912345678",
                    }
                ],
                "messages": [
                    {
                        "id": "wamid.TEST-123",
                    }
                ],
            }
        ).encode("utf-8")

        mocked_urlopen.return_value.__enter__.return_value = response

        result = send_template_message(
            to="+56 9 1234 5678",
            template_name="martini_estado_orden",
            body_parameters=[
                "MC-ABC123",
                "Diagnóstico",
            ],
        )

        self.assertEqual(
            result.message_id,
            "wamid.TEST-123",
        )
        self.assertEqual(
            result.destination,
            "56912345678",
        )
        self.assertEqual(
            result.template_name,
            "martini_estado_orden",
        )

        mocked_urlopen.assert_called_once()

        request = mocked_urlopen.call_args.args[0]
        timeout = mocked_urlopen.call_args.kwargs["timeout"]

        self.assertEqual(
            request.full_url,
            (
                "https://graph.facebook.com/"
                "v99.0/123456789/messages"
            ),
        )
        self.assertEqual(timeout, 10)

        authorization = request.get_header("Authorization")
        self.assertEqual(
            authorization,
            "Bearer token-secreto-de-prueba",
        )

        request_payload = json.loads(
            request.data.decode("utf-8")
        )

        self.assertEqual(
            request_payload["messaging_product"],
            "whatsapp",
        )
        self.assertEqual(
            request_payload["to"],
            "56912345678",
        )
        self.assertEqual(
            request_payload["type"],
            "template",
        )
        self.assertEqual(
            request_payload["template"]["name"],
            "martini_estado_orden",
        )
        self.assertEqual(
            request_payload["template"]["language"]["code"],
            "es_CL",
        )
        self.assertEqual(
            request_payload["template"]["components"][0][
                "parameters"
            ][0]["text"],
            "MC-ABC123",
        )
        self.assertEqual(
            request_payload["template"]["components"][0][
                "parameters"
            ][1]["text"],
            "Diagnóstico",
        )

    @override_settings(
        WHATSAPP_CLOUD_API_ENABLED=True,
        WHATSAPP_CLOUD_API_VERSION="",
        WHATSAPP_CLOUD_PHONE_NUMBER_ID="123456789",
        WHATSAPP_CLOUD_ACCESS_TOKEN="NO-DEBE-APARECER",
    )
    def test_configuration_error_does_not_expose_access_token(self):
        with self.assertRaises(
            WhatsAppCloudConfigurationError
        ) as context:
            send_template_message(
                to="56912345678",
                template_name="martini_estado_orden",
                body_parameters=[
                    "MC-ABC123",
                    "Diagnóstico",
                ],
            )

        self.assertIn(
            "WHATSAPP_CLOUD_API_VERSION",
            str(context.exception),
        )
        self.assertNotIn(
            "NO-DEBE-APARECER",
            str(context.exception),
        )

    @override_settings(
        WHATSAPP_CLOUD_API_ENABLED=True,
        WHATSAPP_CLOUD_API_BASE_URL="https://graph.facebook.com",
        WHATSAPP_CLOUD_API_VERSION="v99.0",
        WHATSAPP_CLOUD_PHONE_NUMBER_ID="123456789",
        WHATSAPP_CLOUD_ACCESS_TOKEN="token-secreto-de-prueba",
        WHATSAPP_CLOUD_TIMEOUT=10,
    )
    @patch("orders.whatsapp_cloud.urlopen")
    def test_missing_meta_message_id_is_treated_as_error(
        self,
        mocked_urlopen,
    ):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b'{"messages": []}'

        mocked_urlopen.return_value.__enter__.return_value = response

        with self.assertRaises(
            WhatsAppCloudRequestError
        ) as context:
            send_template_message(
                to="56912345678",
                template_name="martini_estado_orden",
            )

        self.assertIn(
            "identificador de mensaje",
            str(context.exception),
        )


class WhatsAppCloudStatusNotificationTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_tec04",
            role=User.Role.ADMIN,
        )

        self.customer = Client.objects.create(
            rut="11.111.111-1",
            name="Cliente TEC04",
            phone="912345678",
            email="cliente.tec04@example.com",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model="Cloud API",
            imei="123456789012346",
            color="Negro",
            observations="Dato interno TEC04.",
            created_by=self.admin,
        )

        self.client.force_authenticate(user=self.admin)

    def create_order(self):
        response = self.client.post(
            reverse("service-order-list-create"),
            {
                "client": self.customer.pk,
                "equipment": self.equipment.pk,
                "reported_issue": "Equipo no enciende.",
                "initial_observations": (
                    "Observación privada TEC04."
                ),
                "received_accessories": "Cargador.",
                "deposit_amount": "20000.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        order = ServiceOrder.objects.get(
            pk=response.data["id"]
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

        return order

    def change_to_diagnosis(self, order):
        return self.client.patch(
            reverse(
                "order-status",
                kwargs={"pk": order.pk},
            ),
            {
                "status": ServiceOrder.Status.DIAGNOSIS,
                "note": (
                    "Nota interna que no debe viajar a WhatsApp."
                ),
            },
            format="json",
        )

    @override_settings(
        WHATSAPP_CLOUD_API_ENABLED=True,
        WHATSAPP_CLOUD_FALLBACK_TO_WA_ME=True,
        WHATSAPP_TEMPLATE_STATUS_CHANGE="martini_estado_orden",
        WHATSAPP_TEMPLATE_LANGUAGE="es_CL",
    )
    @patch("orders.views.send_template_message")
    def test_status_change_sends_cloud_template_successfully(
        self,
        mocked_send,
    ):
        mocked_send.return_value = WhatsAppSendResult(
            message_id="wamid.STATUS-001",
            destination="56912345678",
            template_name="martini_estado_orden",
        )

        order = self.create_order()

        response = self.change_to_diagnosis(order)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        order.refresh_from_db()
        self.assertEqual(
            order.status,
            ServiceOrder.Status.DIAGNOSIS,
        )

        notification = OrderStatusNotification.objects.get(
            order=order,
        )

        self.assertEqual(
            notification.status,
            OrderStatusNotification.Status.SENT,
        )
        self.assertEqual(
            notification.destination,
            "56912345678",
        )
        self.assertEqual(
            notification.action_url,
            "",
        )
        self.assertEqual(
            notification.prepared_message,
            "",
        )
        self.assertIn(
            "WhatsApp Cloud API",
            notification.detail,
        )
        self.assertIn(
            "wamid.STATUS-001",
            notification.detail,
        )

        self.assertEqual(
            response.data["notification_result"]["status"],
            OrderStatusNotification.Status.SENT,
        )

        mocked_send.assert_called_once()

        call_kwargs = mocked_send.call_args.kwargs

        self.assertEqual(
            call_kwargs["to"],
            "56912345678",
        )
        self.assertEqual(
            call_kwargs["template_name"],
            "martini_estado_orden",
        )
        self.assertEqual(
            call_kwargs["body_parameters"],
            [
                order.tracking_code,
                "Diagnóstico",
            ],
        )
        self.assertEqual(
            call_kwargs["language_code"],
            "es_CL",
        )

    @override_settings(
        WHATSAPP_CLOUD_API_ENABLED=True,
        WHATSAPP_CLOUD_FALLBACK_TO_WA_ME=True,
        WHATSAPP_TEMPLATE_STATUS_CHANGE="martini_estado_orden",
        WHATSAPP_TEMPLATE_LANGUAGE="es_CL",
    )
    @patch("orders.views.send_template_message")
    def test_cloud_failure_uses_manual_fallback_without_rollback(
        self,
        mocked_send,
    ):
        mocked_send.side_effect = WhatsAppCloudRequestError(
            "Meta temporalmente no disponible."
        )

        order = self.create_order()

        response = self.change_to_diagnosis(order)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            ServiceOrder.Status.DIAGNOSIS,
        )

        notification = OrderStatusNotification.objects.get(
            order=order,
        )

        self.assertEqual(
            notification.status,
            OrderStatusNotification.Status.PREPARED,
        )
        self.assertIn(
            "https://wa.me/56912345678",
            notification.action_url,
        )
        self.assertIn(
            order.tracking_code,
            notification.prepared_message,
        )
        self.assertIn(
            "respaldo manual",
            notification.detail,
        )
        self.assertIn(
            "Meta temporalmente no disponible",
            notification.detail,
        )

        self.assertEqual(
            response.data["notification_result"]["status"],
            OrderStatusNotification.Status.PREPARED,
        )

    @override_settings(
        WHATSAPP_CLOUD_API_ENABLED=True,
        WHATSAPP_CLOUD_FALLBACK_TO_WA_ME=False,
        WHATSAPP_TEMPLATE_STATUS_CHANGE="martini_estado_orden",
        WHATSAPP_TEMPLATE_LANGUAGE="es_CL",
    )
    @patch("orders.views.send_template_message")
    def test_cloud_failure_without_fallback_records_failed_and_keeps_status(
        self,
        mocked_send,
    ):
        mocked_send.side_effect = WhatsAppCloudRequestError(
            "Meta rechazó el envío."
        )

        order = self.create_order()

        response = self.change_to_diagnosis(order)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            ServiceOrder.Status.DIAGNOSIS,
        )

        notification = OrderStatusNotification.objects.get(
            order=order,
        )

        self.assertEqual(
            notification.status,
            OrderStatusNotification.Status.FAILED,
        )
        self.assertEqual(
            notification.action_url,
            "",
        )
        self.assertEqual(
            notification.prepared_message,
            "",
        )
        self.assertIn(
            "WhatsApp Cloud API",
            notification.detail,
        )
        self.assertIn(
            "Meta rechazó el envío",
            notification.detail,
        )

        history = order.status_history.get(
            from_status=ServiceOrder.Status.RECEIVED,
            to_status=ServiceOrder.Status.DIAGNOSIS,
        )
        self.assertIsNotNone(history)

        self.assertEqual(
            response.data["notification_result"]["status"],
            OrderStatusNotification.Status.FAILED,
        )
