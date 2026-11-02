from unittest.mock import patch

from django.core.exceptions import ValidationError
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


class OrderChatNotificationTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_hu36",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tecnico_hu36",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="ayudante_hu36",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente HU36",
            phone="912345678",
            email="cliente.hu36@example.com",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model="Galaxy HU36",
            imei="123456789012345",
            color="Negro",
            observations="Dato interno HU36.",
            created_by=self.admin,
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("service-order-list-create"),
            {
                "client": self.customer.pk,
                "equipment": self.equipment.pk,
                "reported_issue": "Equipo no enciende.",
                "initial_observations": "Observación interna HU36.",
                "received_accessories": "Cargador.",
                "deposit_amount": "25000.00",
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

    def public_chat_url(self):
        return reverse(
            "public-order-chat",
            kwargs={
                "tracking_code": self.order.tracking_code,
            },
        )

    def internal_detail_url(self, conversation):
        return reverse(
            "order-chat-conversation-detail",
            kwargs={"pk": conversation.pk},
        )

    def create_conversation(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.public_chat_url(),
            {"body": "Hola, necesito información de mi equipo."},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        return OrderChatConversation.objects.get(
            order=self.order
        )

    def set_preferred_channel(self, channel):
        self.order.preferred_notification_channel = channel
        self.order.save(
            update_fields=[
                "preferred_notification_channel",
                "updated_at",
            ]
        )

    @patch(
        "orders.views.EmailMessage.send",
        return_value=1,
    )
    def test_email_reply_creates_sent_notification(
        self,
        mocked_send,
    ):
        conversation = self.create_conversation()
        self.set_preferred_channel(
            ServiceOrder.NotificationChannel.EMAIL
        )

        self.client.force_authenticate(user=self.technician)

        response = self.client.post(
            self.internal_detail_url(conversation),
            {"body": "Tu equipo está siendo revisado."},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        staff_message = OrderChatMessage.objects.get(
            conversation=conversation,
            sender_type=OrderChatMessage.SenderType.STAFF,
        )

        notification = OrderChatNotification.objects.get(
            message=staff_message,
        )

        self.assertEqual(
            notification.order,
            self.order,
        )
        self.assertEqual(
            notification.conversation,
            conversation,
        )
        self.assertEqual(
            notification.channel,
            ServiceOrder.NotificationChannel.EMAIL,
        )
        self.assertEqual(
            notification.status,
            OrderChatNotification.Status.SENT,
        )
        self.assertEqual(
            notification.destination,
            self.customer.email,
        )
        self.assertEqual(
            notification.triggered_by,
            self.technician,
        )

        self.assertEqual(
            response.data["notification_result"]["status"],
            OrderChatNotification.Status.SENT,
        )

        mocked_send.assert_called_once_with(
            using="default"
        )

    @patch(
        "orders.views.EmailMessage.send",
        side_effect=RuntimeError("SMTP no disponible"),
    )
    def test_email_failure_keeps_chat_message_and_records_failure(
        self,
        mocked_send,
    ):
        conversation = self.create_conversation()
        self.set_preferred_channel(
            ServiceOrder.NotificationChannel.EMAIL
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.internal_detail_url(conversation),
            {"body": "Respuesta que debe conservarse."},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        staff_message = OrderChatMessage.objects.get(
            conversation=conversation,
            sender_type=OrderChatMessage.SenderType.STAFF,
        )

        self.assertEqual(
            staff_message.body,
            "Respuesta que debe conservarse.",
        )

        notification = OrderChatNotification.objects.get(
            message=staff_message,
        )

        self.assertEqual(
            notification.status,
            OrderChatNotification.Status.FAILED,
        )
        self.assertIn(
            "SMTP no disponible",
            notification.detail,
        )

        conversation.refresh_from_db()

        self.assertEqual(
            conversation.status,
            OrderChatConversation.Status.ANSWERED,
        )

        mocked_send.assert_called_once_with(
            using="default"
        )

    def test_whatsapp_reply_is_prepared_with_tracking_code(self):
        conversation = self.create_conversation()
        self.set_preferred_channel(
            ServiceOrder.NotificationChannel.WHATSAPP
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.internal_detail_url(conversation),
            {"body": "Tenemos novedades sobre tu reparación."},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        notification = OrderChatNotification.objects.get(
            conversation=conversation,
        )

        self.assertEqual(
            notification.channel,
            ServiceOrder.NotificationChannel.WHATSAPP,
        )
        self.assertEqual(
            notification.status,
            OrderChatNotification.Status.PREPARED,
        )
        self.assertEqual(
            notification.destination,
            "56912345678",
        )
        self.assertIn(
            self.order.tracking_code,
            notification.prepared_message,
        )
        self.assertIn(
            "https://wa.me/56912345678",
            notification.action_url,
        )

        self.assertEqual(
            response.data["notification_result"]["status"],
            OrderChatNotification.Status.PREPARED,
        )
        self.assertEqual(
            response.data["notification_result"]["action_url"],
            notification.action_url,
        )

    def test_client_message_does_not_create_notification(self):
        self.set_preferred_channel(
            ServiceOrder.NotificationChannel.EMAIL
        )

        self.create_conversation()

        self.assertEqual(
            OrderChatNotification.objects.count(),
            0,
        )

    def test_email_without_destination_records_failed_notification(self):
        conversation = self.create_conversation()

        self.order.preferred_notification_channel = (
            ServiceOrder.NotificationChannel.EMAIL
        )

        # Se modifica directamente para simular un dato que desaparece
        # después de haber configurado el canal preferido.
        Client.objects.filter(
            pk=self.customer.pk
        ).update(email="")

        self.customer.refresh_from_db()
        self.order.save(
            update_fields=[
                "preferred_notification_channel",
                "updated_at",
            ]
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.internal_detail_url(conversation),
            {"body": "Respuesta sin correo disponible."},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        notification = OrderChatNotification.objects.get(
            conversation=conversation,
        )

        self.assertEqual(
            notification.status,
            OrderChatNotification.Status.FAILED,
        )
        self.assertEqual(
            notification.destination,
            "",
        )
        self.assertIn(
            "correo electrónico",
            notification.detail,
        )

        self.assertTrue(
            conversation.messages.filter(
                sender_type=OrderChatMessage.SenderType.STAFF,
            ).exists()
        )

    def test_whatsapp_without_destination_records_failed_notification(self):
        conversation = self.create_conversation()

        self.order.preferred_notification_channel = (
            ServiceOrder.NotificationChannel.WHATSAPP
        )

        Client.objects.filter(
            pk=self.customer.pk
        ).update(phone="")

        self.customer.refresh_from_db()
        self.order.save(
            update_fields=[
                "preferred_notification_channel",
                "updated_at",
            ]
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.internal_detail_url(conversation),
            {"body": "Respuesta sin teléfono disponible."},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        notification = OrderChatNotification.objects.get(
            conversation=conversation,
        )

        self.assertEqual(
            notification.status,
            OrderChatNotification.Status.FAILED,
        )
        self.assertEqual(
            notification.destination,
            "",
        )
        self.assertIn(
            "teléfono",
            notification.detail,
        )

    def test_reply_without_preferred_channel_keeps_message(self):
        conversation = self.create_conversation()

        self.assertEqual(
            self.order.preferred_notification_channel,
            "",
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.internal_detail_url(conversation),
            {"body": "Respuesta sin canal configurado."},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["notification_result"]["status"],
            "FAILED",
        )
        self.assertIn(
            "canal preferido",
            response.data["notification_result"]["detail"],
        )

        self.assertEqual(
            OrderChatNotification.objects.count(),
            0,
        )
        self.assertTrue(
            conversation.messages.filter(
                sender_type=OrderChatMessage.SenderType.STAFF,
                body="Respuesta sin canal configurado.",
            ).exists()
        )

    @patch(
        "orders.views.EmailMessage.send",
        return_value=1,
    )
    def test_internal_detail_exposes_notification_history(
        self,
        mocked_send,
    ):
        conversation = self.create_conversation()
        self.set_preferred_channel(
            ServiceOrder.NotificationChannel.EMAIL
        )

        self.client.force_authenticate(user=self.admin)

        reply_response = self.client.post(
            self.internal_detail_url(conversation),
            {"body": "Respuesta con historial."},
            format="json",
        )

        self.assertEqual(
            reply_response.status_code,
            status.HTTP_201_CREATED,
        )

        response = self.client.get(
            self.internal_detail_url(conversation)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn(
            "notifications",
            response.data,
        )
        self.assertEqual(
            len(response.data["notifications"]),
            1,
        )
        self.assertEqual(
            response.data["notifications"][0]["channel"],
            ServiceOrder.NotificationChannel.EMAIL,
        )
        self.assertEqual(
            response.data["notifications"][0]["status"],
            OrderChatNotification.Status.SENT,
        )

        mocked_send.assert_called_once_with(
            using="default"
        )

    @patch(
        "orders.views.EmailMessage.send",
        return_value=1,
    )
    def test_public_chat_does_not_expose_notification_history(
        self,
        mocked_send,
    ):
        conversation = self.create_conversation()
        self.set_preferred_channel(
            ServiceOrder.NotificationChannel.EMAIL
        )

        self.client.force_authenticate(user=self.admin)

        reply_response = self.client.post(
            self.internal_detail_url(conversation),
            {"body": "Respuesta privada del taller."},
            format="json",
        )

        self.assertEqual(
            reply_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.public_chat_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertNotIn(
            "notifications",
            response.data,
        )
        self.assertNotIn(
            self.customer.email,
            str(response.data),
        )
        self.assertNotIn(
            self.customer.phone,
            str(response.data),
        )

        mocked_send.assert_called_once_with(
            using="default"
        )

    def test_notification_model_rejects_client_message(self):
        conversation = self.create_conversation()
        client_message = conversation.messages.get(
            sender_type=OrderChatMessage.SenderType.CLIENT
        )

        with self.assertRaises(Exception):
            OrderChatNotification.objects.create(
                order=self.order,
                conversation=conversation,
                message=client_message,
                channel=ServiceOrder.NotificationChannel.EMAIL,
                status=OrderChatNotification.Status.SENT,
                destination=self.customer.email,
                triggered_by=self.admin,
            )

    def test_same_message_and_channel_cannot_be_duplicated(self):
        conversation = self.create_conversation()

        self.client.force_authenticate(user=self.admin)

        staff_message = OrderChatMessage.objects.create(
            conversation=conversation,
            sender_type=OrderChatMessage.SenderType.STAFF,
            sender_user=self.admin,
            body="Mensaje para validar duplicados.",
        )

        OrderChatNotification.objects.create(
            order=self.order,
            conversation=conversation,
            message=staff_message,
            channel=ServiceOrder.NotificationChannel.EMAIL,
            status=OrderChatNotification.Status.SENT,
            destination=self.customer.email,
            triggered_by=self.admin,
        )

        with self.assertRaises(ValidationError):
            OrderChatNotification.objects.create(
                order=self.order,
                conversation=conversation,
                message=staff_message,
                channel=ServiceOrder.NotificationChannel.EMAIL,
                status=OrderChatNotification.Status.SENT,
                destination=self.customer.email,
                triggered_by=self.admin,
            )

    def test_helper_cannot_reply_or_trigger_notification(self):
        conversation = self.create_conversation()
        self.set_preferred_channel(
            ServiceOrder.NotificationChannel.WHATSAPP
        )

        self.client.force_authenticate(user=self.helper)

        response = self.client.post(
            self.internal_detail_url(conversation),
            {"body": "Respuesta no autorizada."},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            OrderChatNotification.objects.count(),
            0,
        )
        self.assertFalse(
            conversation.messages.filter(
                sender_type=OrderChatMessage.SenderType.STAFF,
            ).exists()
        )

    @patch(
        "orders.views.EmailMessage.send",
        return_value=1,
    )
    def test_email_notice_uses_same_tracking_code(
        self,
        mocked_send,
    ):
        conversation = self.create_conversation()
        self.set_preferred_channel(
            ServiceOrder.NotificationChannel.EMAIL
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.internal_detail_url(conversation),
            {"body": "Nueva respuesta disponible."},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        notification = OrderChatNotification.objects.get(
            conversation=conversation
        )

        self.assertEqual(
            notification.order.tracking_code,
            self.order.tracking_code,
        )

        # No se crea ni almacena ningún segundo código.
        self.assertNotIn(
            "tracking_code",
            response.data["notification_result"],
        )

        mocked_send.assert_called_once_with(
            using="default"
        )
