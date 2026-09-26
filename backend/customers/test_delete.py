
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from devices.models import Equipment
from orders.models import ServiceOrder

from .models import Client, ClientChangeHistory


class ClientDeletionTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_eliminar_cliente",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tecnico_eliminar_cliente",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="ayudante_eliminar_cliente",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente ficticio para eliminación",
            phone="912345678",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.url = reverse(
            "client-detail",
            kwargs={"pk": self.customer.pk},
        )

        self.client.force_authenticate(user=self.admin)

    def create_equipment(self):
        return Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Marca ficticia",
            model="Modelo de prueba",
            created_by=self.admin,
            updated_by=self.admin,
        )

    def test_admin_can_delete_client_without_related_records(self):
        customer_id = self.customer.pk

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Client.objects.filter(pk=customer_id).exists()
        )

    def test_anonymous_user_cannot_delete_client(self):
        self.client.force_authenticate(user=None)

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertTrue(
            Client.objects.filter(pk=self.customer.pk).exists()
        )

    def test_technician_cannot_delete_client(self):
        self.client.force_authenticate(user=self.technician)

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertTrue(
            Client.objects.filter(pk=self.customer.pk).exists()
        )

    def test_helper_cannot_delete_client(self):
        self.client.force_authenticate(user=self.helper)

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertTrue(
            Client.objects.filter(pk=self.customer.pk).exists()
        )

    def test_client_with_equipment_cannot_be_deleted(self):
        equipment = self.create_equipment()

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertTrue(
            Client.objects.filter(pk=self.customer.pk).exists()
        )

        self.assertTrue(
            Equipment.objects.filter(pk=equipment.pk).exists()
        )

    def test_client_with_service_order_cannot_be_deleted(self):
        equipment = self.create_equipment()

        order = ServiceOrder.objects.create(
            client=self.customer,
            equipment=equipment,
            reported_issue="Falla ficticia para prueba.",
            created_by=self.admin,
        )

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertTrue(
            Client.objects.filter(pk=self.customer.pk).exists()
        )

        self.assertTrue(
            Equipment.objects.filter(pk=equipment.pk).exists()
        )

        self.assertTrue(
            ServiceOrder.objects.filter(pk=order.pk).exists()
        )

    def test_client_with_change_history_cannot_be_deleted(self):
        history = ClientChangeHistory.objects.create(
            client=self.customer,
            changed_by=self.admin,
            changes={
                "name": {
                    "from": "Nombre anterior ficticio",
                    "to": self.customer.name,
                }
            },
        )

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertTrue(
            Client.objects.filter(pk=self.customer.pk).exists()
        )

        self.assertTrue(
            ClientChangeHistory.objects.filter(
                pk=history.pk
            ).exists()
        )

    def test_delete_nonexistent_client_returns_404(self):
        response = self.client.delete(
            reverse(
                "client-detail",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )