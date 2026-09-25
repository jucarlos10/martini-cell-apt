
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from django.urls import reverse

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


class OrderWarrantyTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_warranty",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tech_warranty",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="helper_warranty",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente garantía",
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
            reported_issue="Prueba de garantías.",
            created_by=self.admin,
        )

        self.other_order = ServiceOrder.objects.create(
            client=self.customer,
            equipment=self.equipment,
            reported_issue="Segunda orden de prueba.",
            created_by=self.admin,
        )

        self.supplier = Supplier.objects.create(
            name="Proveedor original",
        )

        self.part = Part.objects.create(
            name="Pantalla",
            supplier=self.supplier,
            unit_cost=Decimal("15000.00"),
            stock=5,
        )

        self.order_part = OrderPart.objects.create(
            order=self.order,
            part=self.part,
            supplier=self.supplier,
            quantity=1,
            unit_cost=Decimal("15000.00"),
            created_by=self.admin,
        )

        self.other_order_part = OrderPart.objects.create(
            order=self.other_order,
            part=self.part,
            supplier=self.supplier,
            quantity=1,
            unit_cost=Decimal("15000.00"),
            created_by=self.admin,
        )

        self.today = timezone.localdate()

        self.list_url = reverse(
            "order-warranty-list-create",
            kwargs={"pk": self.order.pk},
        )

        self.client.force_authenticate(user=self.admin)

    def service_payload(self, **changes):
        payload = {
            "warranty_type": "SERVICE",
            "is_applicable": True,
            "starts_on": self.today.isoformat(),
            "ends_on": (
                self.today + timedelta(days=90)
            ).isoformat(),
            "conditions": "Cubre la reparación realizada.",
        }
        payload.update(changes)
        return payload

    def create_service_warranty(self, **changes):
        return self.client.post(
            self.list_url,
            self.service_payload(**changes),
            format="json",
        )

    def detail_url(self, warranty_id):
        return reverse(
            "order-warranty-detail",
            kwargs={
                "pk": self.order.pk,
                "warranty_id": warranty_id,
            },
        )

    def history_url(self, warranty_id):
        return reverse(
            "order-warranty-history",
            kwargs={
                "pk": self.order.pk,
                "warranty_id": warranty_id,
            },
        )

    def test_create_service_warranty_and_first_revision(self):
        response = self.create_service_warranty()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(OrderWarranty.objects.count(), 1)
        self.assertEqual(OrderWarrantyHistory.objects.count(), 1)

        history = OrderWarrantyHistory.objects.get()
        self.assertEqual(history.revision, 1)
        self.assertEqual(history.action, "CREATED")
        self.assertEqual(
            history.changed_by_username,
            self.admin.username,
        )

    def test_part_warranty_uses_historical_supplier(self):
        response = self.client.post(
            self.list_url,
            {
                "warranty_type": "PART",
                "order_part": self.order_part.pk,
                "is_applicable": True,
                "starts_on": self.today.isoformat(),
                "ends_on": (
                    self.today + timedelta(days=30)
                ).isoformat(),
                "conditions": "Garantía de pantalla.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["supplier_name"],
            "Proveedor original",
        )

        # Cambia el proveedor del catálogo, no el histórico.
        new_supplier = Supplier.objects.create(
            name="Proveedor nuevo",
        )
        self.part.supplier = new_supplier
        self.part.save()

        read_response = self.client.get(
            self.detail_url(response.data["id"])
        )

        self.assertEqual(
            read_response.data["supplier_name"],
            "Proveedor original",
        )

    def test_warranty_is_active_on_end_date(self):
        response = self.create_service_warranty(
            ends_on=self.today.isoformat(),
        )

        self.assertEqual(response.data["status"], "ACTIVE")

    def test_warranty_not_started(self):
        response = self.create_service_warranty(
            starts_on=(
                self.today + timedelta(days=1)
            ).isoformat(),
        )

        self.assertEqual(
            response.data["status"],
            "NOT_STARTED",
        )

    def test_warranty_expired(self):
        response = self.create_service_warranty(
            starts_on=(
                self.today - timedelta(days=30)
            ).isoformat(),
            ends_on=(
                self.today - timedelta(days=1)
            ).isoformat(),
        )

        self.assertEqual(response.data["status"], "EXPIRED")

    def test_not_applicable_warranty(self):
        response = self.create_service_warranty(
            is_applicable=False,
            starts_on=None,
            ends_on=None,
            conditions="No aplica garantía.",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["status"],
            "NOT_APPLICABLE",
        )

    def test_reversed_dates_are_rejected(self):
        response = self.create_service_warranty(
            starts_on=(
                self.today + timedelta(days=10)
            ).isoformat(),
            ends_on=self.today.isoformat(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(OrderWarranty.objects.exists())
        self.assertFalse(OrderWarrantyHistory.objects.exists())

    def test_missing_conditions_are_rejected(self):
        response = self.create_service_warranty(
            conditions="",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(OrderWarranty.objects.exists())

    def test_not_applicable_warranty_rejects_dates(self):
        response = self.create_service_warranty(
            is_applicable=False,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(OrderWarranty.objects.exists())

    def test_part_from_another_order_is_rejected(self):
        response = self.client.post(
            self.list_url,
            {
                "warranty_type": "PART",
                "order_part": self.other_order_part.pk,
                "is_applicable": False,
                "conditions": "No aplica.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(OrderWarranty.objects.exists())

    def test_duplicate_service_warranty_is_rejected(self):
        first = self.create_service_warranty()
        second = self.create_service_warranty()

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(OrderWarranty.objects.count(), 1)
        self.assertEqual(OrderWarrantyHistory.objects.count(), 1)

    def test_update_creates_revision_without_losing_previous_data(self):
        created = self.create_service_warranty()
        warranty_id = created.data["id"]

        response = self.client.patch(
            self.detail_url(warranty_id),
            {
                "conditions": "Cobertura actualizada.",
                "change_note": "Se corrigieron las condiciones.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        revisions = list(
            OrderWarrantyHistory.objects.filter(
                warranty_id=warranty_id
            ).order_by("revision")
        )

        self.assertEqual(len(revisions), 2)
        self.assertEqual(revisions[0].revision, 1)
        self.assertEqual(
            revisions[0].conditions,
            "Cubre la reparación realizada.",
        )
        self.assertEqual(revisions[1].revision, 2)
        self.assertEqual(
            revisions[1].conditions,
            "Cobertura actualizada.",
        )
        self.assertEqual(
            revisions[1].change_note,
            "Se corrigieron las condiciones.",
        )

        history_response = self.client.get(
            self.history_url(warranty_id)
        )

        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(len(history_response.data), 2)

    def test_update_without_change_note_is_rejected(self):
        created = self.create_service_warranty()
        warranty_id = created.data["id"]

        response = self.client.patch(
            self.detail_url(warranty_id),
            {
                "conditions": "Cambio sin justificación.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        warranty = OrderWarranty.objects.get(pk=warranty_id)

        self.assertEqual(
            warranty.conditions,
            "Cubre la reparación realizada.",
        )
        self.assertEqual(
            warranty.history.count(),
            1,
        )

    def test_technician_can_manage_warranties(self):
        self.client.force_authenticate(
            user=self.technician
        )

        response = self.create_service_warranty()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            OrderWarrantyHistory.objects.get().changed_by,
            self.technician,
        )

    def test_helper_cannot_access_warranties(self):
        self.client.force_authenticate(user=self.helper)

        read_response = self.client.get(self.list_url)
        write_response = self.create_service_warranty()

        self.assertEqual(read_response.status_code, 403)
        self.assertEqual(write_response.status_code, 403)
        self.assertFalse(OrderWarranty.objects.exists())

    def test_anonymous_user_cannot_access_warranties(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )