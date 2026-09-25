
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment
from orders.models import ServiceOrder

from .models import OrderPart, Part, Supplier


class InventoryTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_inventory",
            role=User.Role.ADMIN,
        )

        self.helper = User.objects.create_user(
            username="helper_inventory",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente inventario",
            phone="912345678",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model="Equipo de prueba",
            created_by=self.admin,
        )

        self.order = ServiceOrder.objects.create(
            client=self.customer,
            equipment=self.equipment,
            reported_issue="Falla de prueba.",
            created_by=self.admin,
        )

        self.supplier = Supplier.objects.create(
            name="Proveedor de prueba",
            contact_name="Contacto de prueba",
        )

        self.part = Part.objects.create(
            name="Pantalla de prueba",
            supplier=self.supplier,
            unit_cost=Decimal("15000.00"),
            stock=5,
        )

        self.order_parts_url = reverse(
            "order-parts",
            kwargs={"order_id": self.order.pk},
        )

        self.client.force_authenticate(user=self.admin)

    def register_part(self, quantity=2):
        return self.client.post(
            self.order_parts_url,
            {
                "part": self.part.pk,
                "quantity": quantity,
                "note": "Repuesto utilizado en prueba.",
            },
            format="json",
        )

    def test_register_part_reduces_stock(self):
        response = self.register_part(quantity=2)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.part.refresh_from_db()

        self.assertEqual(self.part.stock, 3)
        self.assertEqual(OrderPart.objects.count(), 1)

        usage = OrderPart.objects.get()

        self.assertEqual(usage.order, self.order)
        self.assertEqual(usage.part, self.part)
        self.assertEqual(usage.quantity, 2)
        self.assertEqual(usage.created_by, self.admin)
        self.assertEqual(usage.subtotal, Decimal("30000.00"))

    def test_insufficient_stock_does_not_register_usage(self):
        response = self.register_part(quantity=6)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Stock insuficiente.",
        )

        self.part.refresh_from_db()

        self.assertEqual(self.part.stock, 5)
        self.assertEqual(OrderPart.objects.count(), 0)

    def test_zero_quantity_is_rejected(self):
        response = self.register_part(quantity=0)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.part.refresh_from_db()

        self.assertEqual(self.part.stock, 5)
        self.assertEqual(OrderPart.objects.count(), 0)

    def test_helper_can_read_but_cannot_register_usage(self):
        self.client.force_authenticate(user=self.helper)

        read_response = self.client.get(
            self.order_parts_url
        )

        self.assertEqual(
            read_response.status_code,
            status.HTTP_200_OK,
        )

        write_response = self.register_part(quantity=1)

        self.assertEqual(
            write_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.part.refresh_from_db()

        self.assertEqual(self.part.stock, 5)
        self.assertEqual(OrderPart.objects.count(), 0)

    def test_anonymous_user_cannot_access_order_parts(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.order_parts_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_closed_order_rejects_new_parts(self):
        ServiceOrder.objects.filter(
            pk=self.order.pk
        ).update(
            status=ServiceOrder.Status.CLOSED
        )

        response = self.register_part(quantity=1)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.part.refresh_from_db()

        self.assertEqual(self.part.stock, 5)
        self.assertEqual(OrderPart.objects.count(), 0)

    def test_inactive_supplier_rejects_usage(self):
        self.supplier.is_active = False
        self.supplier.save(update_fields=["is_active"])

        response = self.register_part(quantity=1)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.part.refresh_from_db()

        self.assertEqual(self.part.stock, 5)
        self.assertEqual(OrderPart.objects.count(), 0)

    def test_usage_preserves_historical_cost_and_supplier(self):
        response = self.register_part(quantity=2)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        usage = OrderPart.objects.get()

        original_supplier_id = usage.supplier_id
        original_unit_cost = usage.unit_cost

        another_supplier = Supplier.objects.create(
            name="Otro proveedor",
        )

        self.part.supplier = another_supplier
        self.part.unit_cost = Decimal("25000.00")
        self.part.save(
            update_fields=["supplier", "unit_cost", "updated_at"]
        )

        usage.refresh_from_db()

        self.assertEqual(
            usage.supplier_id,
            original_supplier_id,
        )

        self.assertEqual(
            usage.unit_cost,
            original_unit_cost,
        )

        self.assertEqual(
            usage.subtotal,
            Decimal("30000.00"),
        )

    def test_admin_can_create_supplier_and_part(self):
        supplier_response = self.client.post(
            reverse("supplier-list-create"),
            {
                "name": "Proveedor nuevo",
                "contact_name": "Contacto",
            },
            format="json",
        )

        self.assertEqual(
            supplier_response.status_code,
            status.HTTP_201_CREATED,
        )

        part_response = self.client.post(
            reverse("part-list-create"),
            {
                "name": "Batería de prueba",
                "supplier": supplier_response.data["id"],
                "unit_cost": "8500.00",
                "stock": 4,
            },
            format="json",
        )

        self.assertEqual(
            part_response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_helper_cannot_create_supplier(self):
        self.client.force_authenticate(user=self.helper)

        response = self.client.post(
            reverse("supplier-list-create"),
            {"name": "Proveedor no autorizado"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertFalse(
            Supplier.objects.filter(
                name="Proveedor no autorizado"
            ).exists()
        )