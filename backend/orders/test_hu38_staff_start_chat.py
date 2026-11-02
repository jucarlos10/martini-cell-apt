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


class OrderChatStaffStartTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_hu38",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tecnico_hu38",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="ayudante_hu38",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente HU38",
            phone="912345678",
            email="cliente.hu38@example.com",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model="Galaxy HU38",
            imei="123456789012345",
            color="Negro",
            observations="Dato interno HU38.",
            created_by=self.admin,
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("service-order-list-create"),
            {
                "client": self.customer.pk,
                "equipment": self.equipment.pk,
                "reported_issue": "Equipo no enciende.",
                "initial_observations": "Observación interna HU38.",
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

    def internal_list_url(self):
        return reverse(
            "order-chat-conversation-list"
        )

    def internal_status_url(self, conversation):
        return reverse(
            "order-chat-conversation-status",
            kwargs={"pk": conversation.pk},
        )

    def public_chat_url(self):
        return reverse(
            "public-order-chat",
            kwargs={
                "tracking_code": self.order.tracking_code,
            },
        )

    def start_from_staff(
        self,
        user=None,
        tracking_code=None,
        body="Hola. Martini Cell tiene una actualización para tu orden.",
    ):
        self.client.force_authenticate(
            user=user or self.admin
        )

        return self.client.post(
            self.internal_list_url(),
            {
                "tracking_code": (
                    tracking_code
                    if tracking_code is not None
                    else self.order.tracking_code
                ),
                "body": body,
            },
            format="json",
        )

    def test_admin_can_start_chat_before_client_writes(self):
        response = self.start_from_staff()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertTrue(
            response.data["conversation_created"]
        )

        conversation = OrderChatConversation.objects.get(
            order=self.order
        )

        self.assertEqual(
            conversation.status,
            OrderChatConversation.Status.ANSWERED,
        )
        self.assertEqual(
            conversation.messages.count(),
            1,
        )

        message = conversation.messages.get()

        self.assertEqual(
            message.sender_type,
            OrderChatMessage.SenderType.STAFF,
        )
        self.assertEqual(
            message.sender_user,
            self.admin,
        )
        self.assertEqual(
            message.body,
            (
                "Hola. Martini Cell tiene una "
                "actualización para tu orden."
            ),
        )
        self.assertIsNotNone(
            message.read_by_staff_at,
        )
        self.assertIsNone(
            message.read_by_client_at,
        )

        self.assertEqual(
            response.data["tracking_code"],
            self.order.tracking_code,
        )
        self.assertIn(
            "/consulta?codigo=",
            response.data["public_tracking_url"],
        )
        self.assertIn(
            self.order.tracking_code,
            response.data["public_tracking_url"],
        )

        # Una orden antigua o recién creada puede no tener todavía
        # un canal preferido. El mensaje debe persistir igualmente.
        self.assertEqual(
            response.data["notification_result"]["status"],
            "FAILED",
        )
        self.assertEqual(
            OrderChatNotification.objects.count(),
            0,
        )

    def test_technician_can_start_chat(self):
        response = self.start_from_staff(
            user=self.technician,
            body="Mensaje iniciado por técnico.",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        message = OrderChatMessage.objects.get(
            conversation__order=self.order
        )

        self.assertEqual(
            message.sender_user,
            self.technician,
        )
        self.assertEqual(
            message.body,
            "Mensaje iniciado por técnico.",
        )

    def test_staff_start_reuses_existing_conversation(self):
        first_response = self.start_from_staff(
            body="Primer mensaje de Martini Cell."
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        conversation = OrderChatConversation.objects.get(
            order=self.order
        )

        second_response = self.start_from_staff(
            body="Segundo mensaje de Martini Cell."
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertFalse(
            second_response.data["conversation_created"]
        )

        self.assertEqual(
            OrderChatConversation.objects.filter(
                order=self.order
            ).count(),
            1,
        )

        conversation.refresh_from_db()

        self.assertEqual(
            conversation.messages.count(),
            2,
        )

        self.assertEqual(
            list(
                conversation.messages.values_list(
                    "body",
                    flat=True,
                )
            ),
            [
                "Primer mensaje de Martini Cell.",
                "Segundo mensaje de Martini Cell.",
            ],
        )

    def test_tracking_code_is_case_insensitive(self):
        response = self.start_from_staff(
            tracking_code=self.order.tracking_code.lower(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            OrderChatConversation.objects.filter(
                order=self.order
            ).exists()
        )

    def test_invalid_tracking_code_returns_404_without_creating_chat(self):
        response = self.start_from_staff(
            tracking_code="MC-NOEXISTE",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertFalse(
            OrderChatConversation.objects.filter(
                order=self.order
            ).exists()
        )

    def test_tracking_code_is_required(self):
        response = self.start_from_staff(
            tracking_code="",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "código de orden",
            response.data["detail"],
        )
        self.assertEqual(
            OrderChatConversation.objects.count(),
            0,
        )

    def test_message_body_is_required(self):
        response = self.start_from_staff(
            body="   ",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            OrderChatConversation.objects.count(),
            0,
        )

    def test_helper_cannot_start_chat(self):
        response = self.start_from_staff(
            user=self.helper,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            OrderChatConversation.objects.count(),
            0,
        )

    def test_unauthenticated_user_cannot_start_chat(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.internal_list_url(),
            {
                "tracking_code": self.order.tracking_code,
                "body": "Mensaje no autenticado.",
            },
            format="json",
        )

        self.assertIn(
            response.status_code,
            {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            },
        )
        self.assertEqual(
            OrderChatConversation.objects.count(),
            0,
        )

    def test_closed_chat_cannot_be_started_again_without_reopening(self):
        first_response = self.start_from_staff(
            body="Mensaje inicial."
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        conversation = OrderChatConversation.objects.get(
            order=self.order
        )

        self.client.force_authenticate(user=self.admin)

        close_response = self.client.patch(
            self.internal_status_url(conversation),
            {
                "status": (
                    OrderChatConversation.Status.CLOSED
                ),
            },
            format="json",
        )

        self.assertEqual(
            close_response.status_code,
            status.HTTP_200_OK,
        )

        response = self.start_from_staff(
            body="No debe guardarse mientras esté cerrado."
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )
        self.assertEqual(
            response.data["conversation_id"],
            conversation.pk,
        )

        conversation.refresh_from_db()

        self.assertEqual(
            conversation.messages.count(),
            1,
        )

    def test_staff_started_message_is_visible_in_public_chat(self):
        response = self.start_from_staff(
            body=(
                "Puedes revisar el seguimiento aquí: "
                "https://martini-cell-frontend.vercel.app/consulta"
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.client.force_authenticate(user=None)

        public_response = self.client.get(
            self.public_chat_url()
        )

        self.assertEqual(
            public_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            len(public_response.data["messages"]),
            1,
        )

        public_message = public_response.data["messages"][0]

        self.assertEqual(
            public_message["sender_name"],
            "Martini Cell",
        )
        self.assertIn(
            "https://martini-cell-frontend.vercel.app/consulta",
            public_message["body"],
        )

        serialized = str(public_response.data)

        self.assertNotIn(
            self.admin.username,
            serialized,
        )

        message = OrderChatMessage.objects.get(
            conversation__order=self.order
        )
        message.refresh_from_db()

        self.assertIsNotNone(
            message.read_by_client_at,
        )

    @override_settings(
        WHATSAPP_CLOUD_API_ENABLED=False,
        WHATSAPP_CLOUD_FALLBACK_TO_WA_ME=True,
    )
    def test_whatsapp_fallback_includes_direct_tracking_link(self):
        self.order.preferred_notification_channel = (
            ServiceOrder.NotificationChannel.WHATSAPP
        )
        self.order.save(
            update_fields=[
                "preferred_notification_channel",
                "updated_at",
            ]
        )

        response = self.start_from_staff(
            body="Tenemos novedades sobre tu reparación.",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        notification = OrderChatNotification.objects.get(
            order=self.order
        )

        self.assertEqual(
            notification.status,
            OrderChatNotification.Status.PREPARED,
        )
        self.assertIn(
            self.order.tracking_code,
            notification.prepared_message,
        )
        self.assertIn(
            "/consulta?codigo=",
            notification.prepared_message,
        )
        self.assertIn(
            self.order.tracking_code,
            notification.prepared_message,
        )
        self.assertIn(
            "https://wa.me/",
            notification.action_url,
        )

        self.assertEqual(
            response.data["notification_result"]["status"],
            OrderChatNotification.Status.PREPARED,
        )
