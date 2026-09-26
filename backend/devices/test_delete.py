
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from orders.models import ServiceOrder

from .models import Equipment


class EquipmentDeletionTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_eliminar_equipo",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tecnico_eliminar_equipo",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="ayudante_eliminar_equipo",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente ficticio para eliminación de equipo",
            phone="912345678",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Marca ficticia",
            model="Modelo de prueba",
            imei="123456789012345",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.url = reverse(
            "equipment-detail",
            kwargs={"pk": self.equipment.pk},
        )

        self.client.force_authenticate(user=self.admin)

    def create_order(self):
        return ServiceOrder.objects.create(
            client=self.customer,
            equipment=self.equipment,
            reported_issue="Falla ficticia para prueba.",
            created_by=self.admin,
        )

    def test_admin_can_delete_equipment_without_orders(self):
        equipment_id = self.equipment.pk

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Equipment.objects.filter(pk=equipment_id).exists()
        )

        # Eliminar un equipo no debe eliminar a su cliente.
        self.assertTrue(
            Client.objects.filter(pk=self.customer.pk).exists()
        )

    def test_admin_can_delete_inactive_equipment_without_orders(self):
        self.equipment.is_active = False
        self.equipment.save(update_fields=["is_active"])

        equipment_id = self.equipment.pk

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Equipment.objects.filter(pk=equipment_id).exists()
        )

    def test_anonymous_user_cannot_delete_equipment(self):
        self.client.force_authenticate(user=None)

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertTrue(
            Equipment.objects.filter(pk=self.equipment.pk).exists()
        )

    def test_technician_cannot_delete_equipment(self):
        self.client.force_authenticate(user=self.technician)

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertTrue(
            Equipment.objects.filter(pk=self.equipment.pk).exists()
        )

    def test_helper_cannot_delete_equipment(self):
        self.client.force_authenticate(user=self.helper)

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertTrue(
            Equipment.objects.filter(pk=self.equipment.pk).exists()
        )

    def test_equipment_with_service_order_cannot_be_deleted(self):
        order = self.create_order()

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertIn("detail", response.data)

        self.assertTrue(
            Equipment.objects.filter(pk=self.equipment.pk).exists()
        )

        self.assertTrue(
            ServiceOrder.objects.filter(pk=order.pk).exists()
        )

    def test_inactive_equipment_with_order_cannot_be_deleted(self):
        order = self.create_order()

        self.equipment.is_active = False
        self.equipment.save(update_fields=["is_active"])

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertTrue(
            Equipment.objects.filter(pk=self.equipment.pk).exists()
        )

        self.assertTrue(
            ServiceOrder.objects.filter(pk=order.pk).exists()
        )

    def test_delete_nonexistent_equipment_returns_404(self):
        response = self.client.delete(
            reverse(
                "equipment-detail",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )