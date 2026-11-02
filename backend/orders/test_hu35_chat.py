from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment

from .models import (
    OrderChatConversation,
    OrderChatMessage,
    ServiceOrder,
)


class OrderChatTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_hu35",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tecnico_hu35",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="ayudante_hu35",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente HU35",
            phone="912345678",
            email="cliente.hu35@example.com",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model="Galaxy HU35",
            imei="123456789012345",
            color="Negro",
            observations="Dato interno del equipo HU35.",
            created_by=self.admin,
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("service-order-list-create"),
            {
                "client": self.customer.pk,
                "equipment": self.equipment.pk,
                "reported_issue": "Equipo no enciende.",
                "initial_observations": "Observación interna HU35.",
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

    def internal_list_url(self):
        return reverse(
            "order-chat-conversation-list"
        )

    def internal_detail_url(self, conversation):
        return reverse(
            "order-chat-conversation-detail",
            kwargs={"pk": conversation.pk},
        )

    def internal_status_url(self, conversation):
        return reverse(
            "order-chat-conversation-status",
            kwargs={"pk": conversation.pk},
        )

    def send_public_message(self, body="Hola, quisiera saber el estado."):
        self.client.force_authenticate(user=None)

        return self.client.post(
            self.public_chat_url(),
            {"body": body},
            format="json",
        )

    def create_conversation(self):
        response = self.send_public_message()

        self.assertIn(
            response.status_code,
            {
                status.HTTP_200_OK,
                status.HTTP_201_CREATED,
            },
        )

        return OrderChatConversation.objects.get(
            order=self.order
        )

    def test_public_client_can_start_chat_with_tracking_code(self):
        response = self.send_public_message(
            "Hola Martini Cell."
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        conversation = OrderChatConversation.objects.get(
            order=self.order
        )

        self.assertEqual(
            conversation.status,
            OrderChatConversation.Status.NEW,
        )

        self.assertEqual(
            conversation.messages.count(),
            1,
        )

        message = conversation.messages.get()

        self.assertEqual(
            message.sender_type,
            OrderChatMessage.SenderType.CLIENT,
        )
        self.assertEqual(
            message.body,
            "Hola Martini Cell.",
        )
        self.assertIsNone(
            message.sender_user,
        )
        self.assertIsNotNone(
            message.read_by_client_at,
        )
        self.assertIsNone(
            message.read_by_staff_at,
        )

    def test_public_chat_reuses_same_conversation_for_order(self):
        first_response = self.send_public_message(
            "Primer mensaje."
        )
        second_response = self.send_public_message(
            "Segundo mensaje."
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            OrderChatConversation.objects.filter(
                order=self.order
            ).count(),
            1,
        )

        conversation = OrderChatConversation.objects.get(
            order=self.order
        )

        self.assertEqual(
            conversation.messages.count(),
            2,
        )

    def test_public_chat_invalid_tracking_code_returns_404(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            reverse(
                "public-order-chat",
                kwargs={"tracking_code": "MC-NOEXISTE"},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_public_chat_without_messages_returns_empty_conversation(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.public_chat_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["tracking_code"],
            self.order.tracking_code,
        )
        self.assertIsNone(
            response.data["status"],
        )
        self.assertEqual(
            response.data["messages"],
            [],
        )

    def test_public_response_does_not_expose_private_order_data(self):
        response = self.send_public_message(
            "Consulta pública."
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            set(response.data.keys()),
            {
                "tracking_code",
                "status",
                "status_display",
                "created_at",
                "updated_at",
                "messages",
            },
        )

        serialized = str(response.data)

        self.assertNotIn(
            self.customer.email,
            serialized,
        )
        self.assertNotIn(
            self.customer.phone,
            serialized,
        )
        self.assertNotIn(
            "25000",
            serialized,
        )
        self.assertNotIn(
            "Observación interna HU35.",
            serialized,
        )
        self.assertNotIn(
            self.admin.username,
            serialized,
        )

    def test_public_message_cannot_be_blank(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.public_chat_url(),
            {"body": "   "},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertFalse(
            OrderChatConversation.objects.filter(
                order=self.order
            ).exists()
        )

    def test_admin_can_list_chat_inbox_with_unread_count(self):
        conversation = self.create_conversation()

        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            self.internal_list_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            len(response.data),
            1,
        )
        self.assertEqual(
            response.data[0]["id"],
            conversation.pk,
        )
        self.assertEqual(
            response.data[0]["tracking_code"],
            self.order.tracking_code,
        )
        self.assertEqual(
            response.data[0]["client_name"],
            self.customer.name,
        )
        self.assertEqual(
            response.data[0]["unread_staff_count"],
            1,
        )

    def test_helper_cannot_access_internal_chat_inbox(self):
        self.create_conversation()

        self.client.force_authenticate(user=self.helper)

        response = self.client.get(
            self.internal_list_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_unauthenticated_user_cannot_access_internal_chat_inbox(self):
        self.create_conversation()

        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.internal_list_url()
        )

        self.assertIn(
            response.status_code,
            {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            },
        )

    def test_opening_internal_detail_marks_client_messages_as_read(self):
        conversation = self.create_conversation()

        message = conversation.messages.get()
        self.assertIsNone(
            message.read_by_staff_at,
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            self.internal_detail_url(conversation)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        message.refresh_from_db()

        self.assertIsNotNone(
            message.read_by_staff_at,
        )

    def test_technician_can_reply_and_chat_becomes_answered(self):
        conversation = self.create_conversation()

        self.client.force_authenticate(
            user=self.technician
        )

        response = self.client.post(
            self.internal_detail_url(conversation),
            {
                "body": (
                    "Hola, estamos revisando tu equipo."
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        conversation.refresh_from_db()

        self.assertEqual(
            conversation.status,
            OrderChatConversation.Status.ANSWERED,
        )

        staff_message = conversation.messages.filter(
            sender_type=OrderChatMessage.SenderType.STAFF
        ).get()

        self.assertEqual(
            staff_message.sender_user,
            self.technician,
        )
        self.assertEqual(
            staff_message.body,
            "Hola, estamos revisando tu equipo.",
        )
        self.assertIsNotNone(
            staff_message.read_by_staff_at,
        )
        self.assertIsNone(
            staff_message.read_by_client_at,
        )

    def test_helper_cannot_reply_to_chat(self):
        conversation = self.create_conversation()

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
            conversation.messages.count(),
            1,
        )

    def test_public_get_marks_staff_message_as_read_by_client(self):
        conversation = self.create_conversation()

        self.client.force_authenticate(user=self.admin)

        reply_response = self.client.post(
            self.internal_detail_url(conversation),
            {"body": "Respuesta de Martini Cell."},
            format="json",
        )

        self.assertEqual(
            reply_response.status_code,
            status.HTTP_201_CREATED,
        )

        staff_message = conversation.messages.filter(
            sender_type=OrderChatMessage.SenderType.STAFF
        ).get()

        self.assertIsNone(
            staff_message.read_by_client_at,
        )

        self.client.force_authenticate(user=None)

        public_response = self.client.get(
            self.public_chat_url()
        )

        self.assertEqual(
            public_response.status_code,
            status.HTTP_200_OK,
        )

        staff_message.refresh_from_db()

        self.assertIsNotNone(
            staff_message.read_by_client_at,
        )

    def test_public_chat_hides_internal_username_in_staff_messages(self):
        conversation = self.create_conversation()

        self.client.force_authenticate(user=self.admin)

        self.client.post(
            self.internal_detail_url(conversation),
            {"body": "Mensaje del personal."},
            format="json",
        )

        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.public_chat_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        serialized = str(response.data)

        self.assertIn(
            "Martini Cell",
            serialized,
        )
        self.assertNotIn(
            self.admin.username,
            serialized,
        )

    def test_new_client_message_after_staff_reply_becomes_pending(self):
        conversation = self.create_conversation()

        self.client.force_authenticate(user=self.admin)

        reply_response = self.client.post(
            self.internal_detail_url(conversation),
            {"body": "Primera respuesta."},
            format="json",
        )

        self.assertEqual(
            reply_response.status_code,
            status.HTTP_201_CREATED,
        )

        conversation.refresh_from_db()

        self.assertEqual(
            conversation.status,
            OrderChatConversation.Status.ANSWERED,
        )

        response = self.send_public_message(
            "Tengo otra consulta."
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        conversation.refresh_from_db()

        self.assertEqual(
            conversation.status,
            OrderChatConversation.Status.PENDING,
        )

    def test_messages_are_returned_in_chronological_order(self):
        conversation = self.create_conversation()

        self.send_public_message(
            "Segundo mensaje del cliente."
        )

        self.client.force_authenticate(user=self.admin)

        self.client.post(
            self.internal_detail_url(conversation),
            {"body": "Tercer mensaje del personal."},
            format="json",
        )

        response = self.client.get(
            self.internal_detail_url(conversation)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        bodies = [
            message["body"]
            for message in response.data["messages"]
        ]

        self.assertEqual(
            bodies,
            [
                "Hola, quisiera saber el estado.",
                "Segundo mensaje del cliente.",
                "Tercer mensaje del personal.",
            ],
        )

    def test_admin_can_close_conversation(self):
        conversation = self.create_conversation()

        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.internal_status_url(conversation),
            {
                "status": (
                    OrderChatConversation.Status.CLOSED
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        conversation.refresh_from_db()

        self.assertEqual(
            conversation.status,
            OrderChatConversation.Status.CLOSED,
        )
        self.assertIsNotNone(
            conversation.closed_at,
        )
        self.assertEqual(
            conversation.closed_by,
            self.admin,
        )

    def test_closed_conversation_blocks_client_and_staff_messages(self):
        conversation = self.create_conversation()

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

        self.client.force_authenticate(user=None)

        public_response = self.client.post(
            self.public_chat_url(),
            {"body": "Mensaje después del cierre."},
            format="json",
        )

        self.assertEqual(
            public_response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.client.force_authenticate(user=self.admin)

        staff_response = self.client.post(
            self.internal_detail_url(conversation),
            {"body": "Respuesta después del cierre."},
            format="json",
        )

        self.assertEqual(
            staff_response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertEqual(
            conversation.messages.count(),
            1,
        )

    def test_admin_can_reopen_closed_conversation_without_losing_history(self):
        conversation = self.create_conversation()

        original_message_ids = list(
            conversation.messages.values_list(
                "id",
                flat=True,
            )
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

        reopen_response = self.client.patch(
            self.internal_status_url(conversation),
            {
                "status": (
                    OrderChatConversation.Status.PENDING
                ),
            },
            format="json",
        )

        self.assertEqual(
            reopen_response.status_code,
            status.HTTP_200_OK,
        )

        conversation.refresh_from_db()

        self.assertEqual(
            conversation.status,
            OrderChatConversation.Status.PENDING,
        )
        self.assertIsNone(
            conversation.closed_at,
        )
        self.assertIsNone(
            conversation.closed_by,
        )

        self.assertEqual(
            list(
                conversation.messages.values_list(
                    "id",
                    flat=True,
                )
            ),
            original_message_ids,
        )

        self.client.force_authenticate(user=None)

        new_message_response = self.client.post(
            self.public_chat_url(),
            {"body": "Gracias por reabrir el chat."},
            format="json",
        )

        self.assertEqual(
            new_message_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            conversation.messages.count(),
            2,
        )

    def test_internal_inbox_can_filter_by_status_and_unread(self):
        conversation = self.create_conversation()

        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            f"{self.internal_list_url()}?status=NEW&unread=true"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            len(response.data),
            1,
        )
        self.assertEqual(
            response.data[0]["id"],
            conversation.pk,
        )

        self.client.get(
            self.internal_detail_url(conversation)
        )

        filtered_response = self.client.get(
            f"{self.internal_list_url()}?unread=true"
        )

        self.assertEqual(
            filtered_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            filtered_response.data,
            [],
        )

    def test_invalid_internal_status_filter_is_rejected(self):
        self.create_conversation()

        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            f"{self.internal_list_url()}?status=INVALID"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
