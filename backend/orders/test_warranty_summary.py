from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment
from inventory.models import OrderPart, Part, Supplier

from .models import (
    OrderWarranty,
    OrderWarrantyHistory,
    ServiceOrder,
)


class OrderWarrantySummaryTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_resumen_garantias",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tecnico_resumen_garantias",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="ayudante_resumen_garantias",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente ficticio TEC-02",
            phone="912345678",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Marca de prueba",
            model="Equipo ficticio",
            created_by=self.admin,
        )

        self.first_order = ServiceOrder.objects.create(
            client=self.customer,
            equipment=self.equipment,
            reported_issue="Primera falla ficticia.",
            created_by=self.admin,
        )

        self.second_order = ServiceOrder.objects.create(
            client=self.customer,
            equipment=self.equipment,
            reported_issue="Segunda falla ficticia.",
            created_by=self.admin,
        )

        self.supplier = Supplier.objects.create(
            name="Proveedor ficticio original",
        )

        self.part = Part.objects.create(
            name="Pantalla de prueba",
            supplier=self.supplier,
            unit_cost=Decimal("15000.00"),
            stock=5,
        )

        self.order_part = OrderPart.objects.create(
            order=self.second_order,
            part=self.part,
            supplier=self.supplier,
            quantity=1,
            unit_cost=Decimal("15000.00"),
            created_by=self.admin,
        )

        self.today = timezone.localdate()

        self.list_url = reverse(
            "order-warranty-summary-list"
        )

        self.client.force_authenticate(
            user=self.admin
        )

    def create_order(self):
        return ServiceOrder.objects.create(
            client=self.customer,
            equipment=self.equipment,
            reported_issue="Falla adicional ficticia.",
            created_by=self.admin,
        )

    def create_service_warranty(
        self,
        *,
        order=None,
        starts_on=None,
        ends_on=None,
        is_applicable=True,
    ):
        order = order or self.first_order

        if is_applicable:
            starts_on = (
                starts_on
                if starts_on is not None
                else self.today
            )
            ends_on = (
                ends_on
                if ends_on is not None
                else self.today + timedelta(days=90)
            )
            conditions = "Garantía ficticia del servicio."
        else:
            starts_on = None
            ends_on = None
            conditions = ""

        return OrderWarranty.objects.create(
            order=order,
            warranty_type=OrderWarranty.WarrantyType.SERVICE,
            is_applicable=is_applicable,
            starts_on=starts_on,
            ends_on=ends_on,
            conditions=conditions,
            created_by=self.admin,
            updated_by=self.admin,
        )

    def create_part_warranty(self):
        return OrderWarranty.objects.create(
            order=self.second_order,
            order_part=self.order_part,
            warranty_type=OrderWarranty.WarrantyType.PART,
            is_applicable=True,
            starts_on=self.today - timedelta(days=90),
            ends_on=self.today - timedelta(days=1),
            conditions="Garantía ficticia del repuesto.",
            created_by=self.admin,
            updated_by=self.admin,
        )

    def test_empty_summary_returns_empty_list(self):
        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            [],
        )

    def test_admin_can_list_warranties_from_different_orders(self):
        service_warranty = self.create_service_warranty()
        part_warranty = self.create_part_warranty()

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            2,
        )

        warranties_by_id = {
            item["id"]: item
            for item in response.data
        }

        service_data = warranties_by_id[
            service_warranty.pk
        ]

        self.assertEqual(
            service_data["tracking_code"],
            self.first_order.tracking_code,
        )

        self.assertEqual(
            service_data["warranty_type"],
            "SERVICE",
        )

        self.assertEqual(
            service_data["status"],
            "ACTIVE",
        )

        self.assertIsNone(
            service_data["part_name"]
        )

        self.assertIsNone(
            service_data["supplier_name"]
        )

        part_data = warranties_by_id[
            part_warranty.pk
        ]

        self.assertEqual(
            part_data["tracking_code"],
            self.second_order.tracking_code,
        )

        self.assertEqual(
            part_data["warranty_type"],
            "PART",
        )

        self.assertEqual(
            part_data["status"],
            "EXPIRED",
        )

        self.assertEqual(
            part_data["part_name"],
            "Pantalla de prueba",
        )

        self.assertEqual(
            part_data["supplier_name"],
            "Proveedor ficticio original",
        )

    def test_technician_can_read_summary(self):
        self.create_service_warranty()

        self.client.force_authenticate(
            user=self.technician
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    def test_helper_cannot_read_summary(self):
        self.create_service_warranty()

        self.client.force_authenticate(
            user=self.helper
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_anonymous_user_cannot_read_summary(self):
        self.create_service_warranty()

        self.client.force_authenticate(
            user=None
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_summary_is_read_only(self):
        self.create_service_warranty()

        response = self.client.post(
            self.list_url,
            {
                "warranty_type": "SERVICE",
                "conditions": "Intento de creación.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        self.assertEqual(
            OrderWarranty.objects.count(),
            1,
        )

    def test_get_does_not_modify_warranties_or_history(self):
        warranty = self.create_service_warranty()

        original_updated_at = warranty.updated_at

        warranties_before = OrderWarranty.objects.count()
        history_before = OrderWarrantyHistory.objects.count()

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        warranty.refresh_from_db()

        self.assertEqual(
            OrderWarranty.objects.count(),
            warranties_before,
        )

        self.assertEqual(
            OrderWarrantyHistory.objects.count(),
            history_before,
        )

        self.assertEqual(
            warranty.updated_at,
            original_updated_at,
        )

    def test_summary_preserves_historical_supplier(self):
        self.create_part_warranty()

        new_supplier = Supplier.objects.create(
            name="Proveedor ficticio nuevo",
        )

        self.part.supplier = new_supplier
        self.part.save()

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        self.assertEqual(
            response.data[0]["supplier_name"],
            "Proveedor ficticio original",
        )

    def test_summary_does_not_expose_client_personal_data(self):
        self.create_service_warranty()

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        item = response.data[0]

        self.assertNotIn("rut", item)
        self.assertNotIn("client_rut", item)
        self.assertNotIn("client_name", item)
        self.assertNotIn("phone", item)
        self.assertNotIn("email", item)

    # HU-33: búsqueda por código, nombre y RUT.

    def test_search_by_tracking_code(self):
        first_warranty = self.create_service_warranty()
        second_warranty = self.create_part_warranty()

        response = self.client.get(
            self.list_url,
            {
                "q": self.first_order.tracking_code,
            },
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
            first_warranty.id,
        )

        self.assertNotEqual(
            response.data[0]["id"],
            second_warranty.id,
        )

    def test_search_by_partial_tracking_code(self):
        warranty = self.create_service_warranty()

        partial_code = self.first_order.tracking_code[-6:]

        response = self.client.get(
            self.list_url,
            {
                "q": partial_code,
            },
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
            warranty.id,
        )

    def test_search_by_client_name(self):
        warranty = self.create_service_warranty()

        response = self.client.get(
            self.list_url,
            {
                "q": "ficticio TEC-02",
            },
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
            warranty.id,
        )

    def test_search_by_formatted_rut(self):
        warranty = self.create_service_warranty()

        response = self.client.get(
            self.list_url,
            {
                "q": "12.345.678-5",
            },
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
            warranty.id,
        )

    def test_search_by_unformatted_rut(self):
        warranty = self.create_service_warranty()

        response = self.client.get(
            self.list_url,
            {
                "q": "123456785",
            },
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
            warranty.id,
        )

    def test_search_without_matches_returns_empty_list(self):
        self.create_service_warranty()

        response = self.client.get(
            self.list_url,
            {
                "q": "cliente inexistente xyz",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            [],
        )

    # HU-33: filtros por estado.

    def test_filter_active_warranties(self):
        active = self.create_service_warranty()
        expired = self.create_part_warranty()

        response = self.client.get(
            self.list_url,
            {
                "status": "ACTIVE",
            },
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
            active.id,
        )

        self.assertNotEqual(
            response.data[0]["id"],
            expired.id,
        )

    def test_filter_expired_warranties(self):
        self.create_service_warranty()
        expired = self.create_part_warranty()

        response = self.client.get(
            self.list_url,
            {
                "status": "EXPIRED",
            },
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
            expired.id,
        )

    def test_filter_not_started_warranties(self):
        future_order = self.create_order()

        future = self.create_service_warranty(
            order=future_order,
            starts_on=self.today + timedelta(days=10),
            ends_on=self.today + timedelta(days=40),
        )

        self.create_service_warranty()

        response = self.client.get(
            self.list_url,
            {
                "status": "NOT_STARTED",
            },
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
            future.id,
        )

    def test_filter_not_applicable_warranties(self):
        not_applicable_order = self.create_order()

        not_applicable = self.create_service_warranty(
            order=not_applicable_order,
            is_applicable=False,
        )

        self.create_service_warranty()

        response = self.client.get(
            self.list_url,
            {
                "status": "NOT_APPLICABLE",
            },
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
            not_applicable.id,
        )

    # HU-33: filtros por tipo.

    def test_filter_service_warranties(self):
        service_warranty = self.create_service_warranty()
        self.create_part_warranty()

        response = self.client.get(
            self.list_url,
            {
                "type": "SERVICE",
            },
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
            service_warranty.id,
        )

    def test_filter_part_warranties(self):
        self.create_service_warranty()
        part_warranty = self.create_part_warranty()

        response = self.client.get(
            self.list_url,
            {
                "type": "PART",
            },
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
            part_warranty.id,
        )

    def test_search_and_filters_can_be_combined(self):
        service_warranty = self.create_service_warranty()
        self.create_part_warranty()

        response = self.client.get(
            self.list_url,
            {
                "q": self.first_order.tracking_code,
                "status": "ACTIVE",
                "type": "SERVICE",
            },
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
            service_warranty.id,
        )

    def test_invalid_status_returns_400(self):
        self.create_service_warranty()

        response = self.client.get(
            self.list_url,
            {
                "status": "ESTADO_INVALIDO",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "detail",
            response.data,
        )

    def test_invalid_type_returns_400(self):
        self.create_service_warranty()

        response = self.client.get(
            self.list_url,
            {
                "type": "TIPO_INVALIDO",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "detail",
            response.data,
        )