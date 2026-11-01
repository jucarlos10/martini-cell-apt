from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment

from .models import (
    OrderChatConversation,
    OrderChatMessage,
    OrderChatNotification,
    ServiceOrder,
)
from .whatsapp_cloud import (
    WhatsAppCloudRequestError,
    WhatsAppSendResult,
)


class WhatsAppCloudChatNotificationTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_tec04_chat",
            role=User.Role.ADMIN,
        )

        self.customer = Client.objects.create(
            rut="22.222.222-2",
            name="Cliente TEC04 Chat",
            phone="912345678",
            email="cliente.chat.tec04@example.com",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Apple",
            model="Chat Cloud",
            imei="223456789012345",
            color="Negro",
            observations="Dato interno del equipo.",
            created_by=self.admin,
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("service-order-list-create"),
            {
                "client": self.customer.pk,
                "equipment": self.equipment.pk,
                "reported_issue": "Equipo no carga.",
                "initial_observations": "Observación privada.",
                "received_accessories": "Cable.",
                "deposit_amount": "15000.00",
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

        self.order.preferred_notification_channel = (
            ServiceOrder.NotificationChannel.WHATSAPP
        )
        self.order.save(
            update_fields=[
                "preferred_notification_channel",
                "updated_at",
            ]
        )

        self.client.force_authenticate(user=None)

        response = self.client.post(
            reverse(
                "public-order-chat",
                kwargs={
                    "tracking_code": self.order.tracking_code,
                },
            ),
            {
                "body": "¿Cómo va mi reparación?",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.conversation = OrderChatConversation.objects.get(
            order=self.order
        )

        self.client.force_authenticate(user=self.admin)

    def detail_url(self):
        return reverse(
            "order-chat-conversation-detail",
            kwargs={"pk": self.conversation.pk},
        )

    @override_settings(
        WHATSAPP_CLOUD_API_ENABLED=True,
        WHATSAPP_CLOUD_FALLBACK_TO_WA_ME=True,
        WHATSAPP_TEMPLATE_CHAT_REPLY="martini_respuesta_chat",
        WHATSAPP_TEMPLATE_LANGUAGE="es_CL",
    )
    @patch("orders.views.send_template_message")
    def test_chat_reply_sends_cloud_template_successfully(
        self,
        mocked_send,
    ):
        mocked_send.return_value = WhatsAppSendResult(
            message_id="wamid.CHAT-001",
            destination="56912345678",
            template_name="martini_respuesta_chat",
        )

        staff_body = (
            "Contenido interno de respuesta que no debe ir en la plantilla."
        )

        response = self.client.post(
            self.detail_url(),
            {
                "body": staff_body,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        staff_message = OrderChatMessage.objects.get(
            conversation=self.conversation,
            sender_type=OrderChatMessage.SenderType.STAFF,
        )

        self.assertEqual(
            staff_message.body,
            staff_body,
        )

        notification = OrderChatNotification.objects.get(
            message=staff_message,
        )

        self.assertEqual(
            notification.status,
            OrderChatNotification.Status.SENT,
        )
        self.assertEqual(
            notification.destination,
            "56912345678",
        )
        self.assertEqual(
            notification.prepared_message,
            "",
        )
        self.assertEqual(
            notification.action_url,
            "",
        )
        self.assertIn(
            "WhatsApp Cloud API",
            notification.detail,
        )
        self.assertIn(
            "wamid.CHAT-001",
            notification.detail,
        )

        self.assertEqual(
            response.data["notification_result"]["status"],
            OrderChatNotification.Status.SENT,
        )

        mocked_send.assert_called_once()

        call_kwargs = mocked_send.call_args.kwargs
        tracking_url = (
            "https://martini-cell-frontend.vercel.app/consulta?codigo="
            f"{self.order.tracking_code}"
        )

        self.assertEqual(
            call_kwargs["to"],
            "56912345678",
        )
        self.assertEqual(
            call_kwargs["template_name"],
            "martini_respuesta_chat",
        )
        self.assertEqual(
            call_kwargs["body_parameters"],
            [
                self.order.tracking_code,
                tracking_url,
            ],
        )
        self.assertEqual(
            call_kwargs["language_code"],
            "es_CL",
        )

        self.assertNotIn(
            staff_body,
            str(call_kwargs),
        )

    @override_settings(
        WHATSAPP_CLOUD_API_ENABLED=True,
        WHATSAPP_CLOUD_FALLBACK_TO_WA_ME=True,
        WHATSAPP_TEMPLATE_CHAT_REPLY="martini_respuesta_chat",
        WHATSAPP_TEMPLATE_LANGUAGE="es_CL",
    )
    @patch("orders.views.send_template_message")
    def test_chat_cloud_failure_uses_manual_fallback_and_keeps_reply(
        self,
        mocked_send,
    ):
        mocked_send.side_effect = WhatsAppCloudRequestError(
            "Meta temporalmente no disponible."
        )

        response = self.client.post(
            self.detail_url(),
            {
                "body": "Respuesta que debe persistir.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            self.conversation.messages.filter(
                sender_type=OrderChatMessage.SenderType.STAFF,
                body="Respuesta que debe persistir.",
            ).exists()
        )

        notification = OrderChatNotification.objects.get(
            conversation=self.conversation,
        )

        self.assertEqual(
            notification.status,
            OrderChatNotification.Status.PREPARED,
        )
        self.assertIn(
            "https://wa.me/56912345678",
            notification.action_url,
        )
        self.assertIn(
            self.order.tracking_code,
            notification.prepared_message,
        )
        self.assertIn(
            "https://martini-cell-frontend.vercel.app/consulta?codigo=",
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

        self.conversation.refresh_from_db()

        self.assertEqual(
            self.conversation.status,
            OrderChatConversation.Status.ANSWERED,
        )

    @override_settings(
        WHATSAPP_CLOUD_API_ENABLED=True,
        WHATSAPP_CLOUD_FALLBACK_TO_WA_ME=False,
        WHATSAPP_TEMPLATE_CHAT_REPLY="martini_respuesta_chat",
        WHATSAPP_TEMPLATE_LANGUAGE="es_CL",
    )
    @patch("orders.views.send_template_message")
    def test_chat_cloud_failure_without_fallback_records_failed_and_keeps_reply(
        self,
        mocked_send,
    ):
        mocked_send.side_effect = WhatsAppCloudRequestError(
            "Meta rechazó el envío."
        )

        response = self.client.post(
            self.detail_url(),
            {
                "body": "Respuesta persistente aunque falle Meta.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        staff_message = OrderChatMessage.objects.get(
            conversation=self.conversation,
            sender_type=OrderChatMessage.SenderType.STAFF,
        )

        self.assertEqual(
            staff_message.body,
            "Respuesta persistente aunque falle Meta.",
        )

        notification = OrderChatNotification.objects.get(
            message=staff_message,
        )

        self.assertEqual(
            notification.status,
            OrderChatNotification.Status.FAILED,
        )
        self.assertEqual(
            notification.prepared_message,
            "",
        )
        self.assertEqual(
            notification.action_url,
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

        self.conversation.refresh_from_db()

        self.assertEqual(
            self.conversation.status,
            OrderChatConversation.Status.ANSWERED,
        )

        self.assertEqual(
            response.data["notification_result"]["status"],
            OrderChatNotification.Status.FAILED,
        )
