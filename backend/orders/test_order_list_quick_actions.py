from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment

from .models import (
    OrderChatConversation,
    OrderWarranty,
    ServiceOrder,
)


class OrderListQuickActionsTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_order_actions",
            role=User.Role.ADMIN,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente acciones rápidas",
            phone="912345678",
            email="acciones@example.com",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model="Galaxy Actions",
            created_by=self.admin,
        )

        self.order = ServiceOrder.objects.create(
            client=self.customer,
            equipment=self.equipment,
            reported_issue="Equipo de prueba.",
            created_by=self.admin,
        )

        self.client.force_authenticate(user=self.admin)
        self.url = reverse("service-order-list-create")

    def get_order_row(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        rows = (
            response.data
            if isinstance(response.data, list)
            else response.data["results"]
        )

        return next(
            row
            for row in rows
            if row["id"] == self.order.id
        )

    def test_order_without_warranty_or_chat_has_empty_quick_actions(self):
        row = self.get_order_row()

        self.assertIsNone(
            row["chat_conversation_id"]
        )
        self.assertEqual(
            row["warranty_summary"],
            {
                "count": 0,
                "status": None,
                "status_display": "No ingresada",
            },
        )

    def test_order_exposes_chat_id_and_current_warranty_status(self):
        conversation = OrderChatConversation.objects.create(
            order=self.order,
        )

        today = timezone.localdate()

        OrderWarranty.objects.create(
            order=self.order,
            warranty_type=OrderWarranty.WarrantyType.SERVICE,
            is_applicable=True,
            starts_on=today - timedelta(days=1),
            ends_on=today + timedelta(days=30),
            conditions="Cobertura de servicio para prueba.",
            created_by=self.admin,
            updated_by=self.admin,
        )

        row = self.get_order_row()

        self.assertEqual(
            row["chat_conversation_id"],
            conversation.id,
        )
        self.assertEqual(
            row["warranty_summary"],
            {
                "count": 1,
                "status": OrderWarranty.WarrantyStatus.ACTIVE,
                "status_display": "Vigente",
            },
        )
