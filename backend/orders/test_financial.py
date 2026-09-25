
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment
from inventory.models import OrderPart, Part, Supplier

from .models import OrderFinancial, ServiceOrder


class OrderFinancialTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_financial",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tech_financial",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="helper_financial",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente financiero",
            phone="912345678",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model="Equipo financiero",
            created_by=self.admin,
        )

        self.order = ServiceOrder.objects.create(
            client=self.customer,
            equipment=self.equipment,
            reported_issue="Falla para prueba financiera.",
            created_by=self.admin,
        )

        self.supplier = Supplier.objects.create(
            name="Proveedor financiero",
        )

        self.part = Part.objects.create(
            name="Pantalla de prueba",
            supplier=self.supplier,
            unit_cost=Decimal("15000.00"),
            stock=5,
        )

        # HU-13: uso histórico de dos repuestos a $15.000.
        OrderPart.objects.create(
            order=self.order,
            part=self.part,
            supplier=self.supplier,
            quantity=2,
            unit_cost=Decimal("15000.00"),
            created_by=self.admin,
        )

        self.url = reverse(
            "order-financial",
            kwargs={"pk": self.order.pk},
        )

        self.client.force_authenticate(user=self.admin)

    def save_financial(self, **changes):
        payload = {
            "price_charged": "60000.00",
            "labor_cost": "10000.00",
            "other_direct_cost": "5000.00",
            "notes": "Prueba financiera HU-14.",
        }

        payload.update(changes)

        return self.client.patch(
            self.url,
            payload,
            format="json",
        )

    def test_without_financial_record_margin_is_pending(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            response.data["has_financial_record"]
        )

        self.assertIsNone(
            response.data["price_charged"]
        )

        self.assertEqual(
            response.data["parts_cost"],
            "30000.00",
        )

        self.assertEqual(
            response.data["total_direct_cost"],
            "30000.00",
        )

        self.assertIsNone(
            response.data["estimated_margin"]
        )

    def test_create_financial_and_calculate_margin(self):
        response = self.save_financial()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            OrderFinancial.objects.count(),
            1,
        )

        self.assertEqual(
            response.data["parts_cost"],
            "30000.00",
        )

        self.assertEqual(
            response.data["labor_cost"],
            "10000.00",
        )

        self.assertEqual(
            response.data["other_direct_cost"],
            "5000.00",
        )

        self.assertEqual(
            response.data["total_direct_cost"],
            "45000.00",
        )

        self.assertEqual(
            response.data["estimated_margin"],
            "15000.00",
        )

        self.assertEqual(
            response.data["estimated_margin_percent"],
            "25.00",
        )

    def test_second_patch_updates_existing_record(self):
        self.save_financial()

        response = self.client.patch(
            self.url,
            {
                "price_charged": "70000.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            OrderFinancial.objects.count(),
            1,
        )

        self.assertEqual(
            response.data["price_charged"],
            "70000.00",
        )

        self.assertEqual(
            response.data["total_direct_cost"],
            "45000.00",
        )

        self.assertEqual(
            response.data["estimated_margin"],
            "25000.00",
        )

    def test_catalog_price_change_preserves_historical_cost(self):
        self.save_financial()

        # Cambia el precio actual del catálogo.
        self.part.unit_cost = Decimal("25000.00")
        self.part.save(
            update_fields=["unit_cost", "updated_at"]
        )

        response = self.client.get(self.url)

        # La orden conserva el costo histórico de HU-13.
        self.assertEqual(
            response.data["parts_cost"],
            "30000.00",
        )

        self.assertEqual(
            response.data["total_direct_cost"],
            "45000.00",
        )

        self.assertEqual(
            response.data["estimated_margin"],
            "15000.00",
        )

    def test_new_part_usage_updates_total_without_duplication(self):
        self.save_financial()

        # Se utiliza un repuesto adicional de $5.000.
        OrderPart.objects.create(
            order=self.order,
            part=self.part,
            supplier=self.supplier,
            quantity=1,
            unit_cost=Decimal("5000.00"),
            created_by=self.admin,
        )

        response = self.client.get(self.url)

        self.assertEqual(
            response.data["parts_cost"],
            "35000.00",
        )

        self.assertEqual(
            response.data["total_direct_cost"],
            "50000.00",
        )

        self.assertEqual(
            response.data["estimated_margin"],
            "10000.00",
        )

    def test_zero_price_has_no_margin_percentage(self):
        response = self.save_financial(
            price_charged="0.00",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["estimated_margin"],
            "-45000.00",
        )

        self.assertIsNone(
            response.data["estimated_margin_percent"]
        )

    def test_negative_cost_is_rejected(self):
        response = self.save_financial(
            labor_cost="-1000.00",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertFalse(
            OrderFinancial.objects.filter(
                order=self.order
            ).exists()
        )

    def test_negative_price_is_rejected(self):
        response = self.save_financial(
            price_charged="-5000.00",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertFalse(
            OrderFinancial.objects.filter(
                order=self.order
            ).exists()
        )

    def test_technician_can_read_but_cannot_modify(self):
        self.client.force_authenticate(
            user=self.technician
        )

        read_response = self.client.get(self.url)

        self.assertEqual(
            read_response.status_code,
            status.HTTP_200_OK,
        )

        write_response = self.client.patch(
            self.url,
            {
                "price_charged": "60000.00",
            },
            format="json",
        )

        self.assertEqual(
            write_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_helper_cannot_read_financial_information(self):
        self.client.force_authenticate(
            user=self.helper
        )

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_anonymous_user_cannot_access_financial_information(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )