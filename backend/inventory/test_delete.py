
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment
from orders.models import ServiceOrder

from .models import OrderPart, Part, Supplier


class SupplierDeletionTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_eliminar_proveedor",
            role=User.Role.ADMIN,
        )
        self.technician = User.objects.create_user(
            username="tecnico_eliminar_proveedor",
            role=User.Role.TECH,
        )
        self.helper = User.objects.create_user(
            username="ayudante_eliminar_proveedor",
            role=User.Role.HELPER,
        )

        self.supplier = Supplier.objects.create(
            name="Proveedor ficticio para eliminación",
        )

        self.url = reverse(
            "supplier-detail",
            kwargs={"pk": self.supplier.pk},
        )

        self.client.force_authenticate(user=self.admin)

    def create_part(self):
        return Part.objects.create(
            name="Repuesto ficticio",
            supplier=self.supplier,
            unit_cost=Decimal("15000.00"),
            stock=5,
        )

    def create_order(self):
        customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente ficticio del inventario",
            phone="912345678",
        )

        equipment = Equipment.objects.create(
            client=customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Marca ficticia",
            model="Modelo de prueba",
        )

        return ServiceOrder.objects.create(
            client=customer,
            equipment=equipment,
            reported_issue="Falla ficticia para prueba.",
            created_by=self.admin,
        )

    def test_admin_can_delete_supplier_without_related_records(self):
        supplier_id = self.supplier.pk

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Supplier.objects.filter(pk=supplier_id).exists()
        )

    def test_admin_can_delete_inactive_supplier_without_relations(self):
        self.supplier.is_active = False
        self.supplier.save(update_fields=["is_active"])

        supplier_id = self.supplier.pk

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Supplier.objects.filter(pk=supplier_id).exists()
        )

    def test_anonymous_user_cannot_delete_supplier(self):
        self.client.force_authenticate(user=None)

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertTrue(
            Supplier.objects.filter(pk=self.supplier.pk).exists()
        )

    def test_technician_cannot_delete_supplier(self):
        self.client.force_authenticate(user=self.technician)

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertTrue(
            Supplier.objects.filter(pk=self.supplier.pk).exists()
        )

    def test_helper_cannot_delete_supplier(self):
        self.client.force_authenticate(user=self.helper)

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertTrue(
            Supplier.objects.filter(pk=self.supplier.pk).exists()
        )

    def test_supplier_with_part_cannot_be_deleted(self):
        part = self.create_part()

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertIn("detail", response.data)

        self.assertTrue(
            Supplier.objects.filter(pk=self.supplier.pk).exists()
        )

        self.assertTrue(
            Part.objects.filter(pk=part.pk).exists()
        )

    def test_supplier_in_order_history_cannot_be_deleted(self):
        """
        El proveedor histórico debe conservarse aunque el
        repuesto se haya reasignado a otro proveedor.
        """
        part = self.create_part()
        order = self.create_order()

        usage = OrderPart.objects.create(
            order=order,
            part=part,
            supplier=self.supplier,
            quantity=1,
            unit_cost=Decimal("15000.00"),
            created_by=self.admin,
        )

        another_supplier = Supplier.objects.create(
            name="Proveedor ficticio actual",
        )

        part.supplier = another_supplier
        part.save(update_fields=["supplier", "updated_at"])

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertTrue(
            Supplier.objects.filter(pk=self.supplier.pk).exists()
        )

        usage.refresh_from_db()

        self.assertEqual(
            usage.supplier_id,
            self.supplier.pk,
        )

        self.assertEqual(
            part.supplier_id,
            another_supplier.pk,
        )

    def test_delete_nonexistent_supplier_returns_404(self):
        response = self.client.delete(
            reverse(
                "supplier-detail",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


class PartDeletionTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_eliminar_repuesto",
            role=User.Role.ADMIN,
        )
        self.technician = User.objects.create_user(
            username="tecnico_eliminar_repuesto",
            role=User.Role.TECH,
        )
        self.helper = User.objects.create_user(
            username="ayudante_eliminar_repuesto",
            role=User.Role.HELPER,
        )

        self.supplier = Supplier.objects.create(
            name="Proveedor ficticio de repuestos",
        )

        self.part = Part.objects.create(
            name="Pantalla ficticia",
            supplier=self.supplier,
            unit_cost=Decimal("15000.00"),
            stock=5,
        )

        self.url = reverse(
            "part-detail",
            kwargs={"pk": self.part.pk},
        )

        self.client.force_authenticate(user=self.admin)

    def create_order_usage(self):
        customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente ficticio para repuesto",
            phone="912345678",
        )

        equipment = Equipment.objects.create(
            client=customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Marca ficticia",
            model="Modelo de prueba",
        )

        order = ServiceOrder.objects.create(
            client=customer,
            equipment=equipment,
            reported_issue="Falla ficticia para prueba.",
            created_by=self.admin,
        )

        return OrderPart.objects.create(
            order=order,
            part=self.part,
            supplier=self.supplier,
            quantity=1,
            unit_cost=self.part.unit_cost,
            created_by=self.admin,
        )

    def test_admin_can_delete_part_without_order_usages(self):
        part_id = self.part.pk

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Part.objects.filter(pk=part_id).exists()
        )

        # Eliminar el repuesto no elimina a su proveedor.
        self.assertTrue(
            Supplier.objects.filter(pk=self.supplier.pk).exists()
        )

    def test_admin_can_delete_inactive_part_without_order_usages(self):
        self.part.is_active = False
        self.part.save(update_fields=["is_active"])

        part_id = self.part.pk

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Part.objects.filter(pk=part_id).exists()
        )

    def test_anonymous_user_cannot_delete_part(self):
        self.client.force_authenticate(user=None)

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertTrue(
            Part.objects.filter(pk=self.part.pk).exists()
        )

    def test_technician_cannot_delete_part(self):
        self.client.force_authenticate(user=self.technician)

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertTrue(
            Part.objects.filter(pk=self.part.pk).exists()
        )

    def test_helper_cannot_delete_part(self):
        self.client.force_authenticate(user=self.helper)

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertTrue(
            Part.objects.filter(pk=self.part.pk).exists()
        )

    def test_part_used_in_order_cannot_be_deleted(self):
        usage = self.create_order_usage()

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertIn("detail", response.data)

        self.assertTrue(
            Part.objects.filter(pk=self.part.pk).exists()
        )

        self.assertTrue(
            OrderPart.objects.filter(pk=usage.pk).exists()
        )

    def test_inactive_part_used_in_order_cannot_be_deleted(self):
        usage = self.create_order_usage()

        self.part.is_active = False
        self.part.save(update_fields=["is_active"])

        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertTrue(
            Part.objects.filter(pk=self.part.pk).exists()
        )

        self.assertTrue(
            OrderPart.objects.filter(pk=usage.pk).exists()
        )

    def test_delete_nonexistent_part_returns_404(self):
        response = self.client.delete(
            reverse(
                "part-detail",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )