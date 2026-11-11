from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment

from .models import OrderWarranty, ServiceOrder
from .warranty_request_models import WarrantyRequest
from .warranty_request_serializers import WarrantyRequestReadSerializer


class WarrantyRequestClientIdentificationTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_warranty_identification",
            role=User.Role.ADMIN,
        )
        self.today = timezone.localdate()

    def create_order_with_warranty(self, client, suffix):
        equipment = Equipment.objects.create(
            client=client,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model=f"Equipo {suffix}",
            created_by=self.admin,
        )

        order = ServiceOrder.objects.create(
            client=client,
            equipment=equipment,
            reported_issue="Falla de prueba.",
            created_by=self.admin,
        )

        warranty = OrderWarranty.objects.create(
            order=order,
            warranty_type=OrderWarranty.WarrantyType.SERVICE,
            is_applicable=True,
            starts_on=self.today - timedelta(days=1),
            ends_on=self.today + timedelta(days=30),
            conditions="Cobertura de prueba.",
            created_by=self.admin,
            updated_by=self.admin,
        )

        return order, warranty

    def test_passport_is_snapshotted_in_warranty_request(self):
        client = Client.objects.create(
            identification_type=Client.IdentificationType.PASSPORT,
            document_number="ve123abc",
            name="Cliente pasaporte",
            phone="912345678",
            created_by=self.admin,
            updated_by=self.admin,
        )

        order, warranty = self.create_order_with_warranty(
            client,
            "pasaporte",
        )

        request = WarrantyRequest.objects.create(
            order=order,
            warranty=warranty,
            requested_on=self.today,
            problem_description="Falla cubierta.",
            created_by=self.admin,
        )

        self.assertEqual(
            request.client_identification_type_snapshot,
            Client.IdentificationType.PASSPORT,
        )
        self.assertEqual(
            request.client_identification_number_snapshot,
            "VE123ABC",
        )
        self.assertEqual(
            request.client_rut_snapshot,
            "",
        )

        data = WarrantyRequestReadSerializer(request).data

        self.assertEqual(
            data["client_identification"],
            "Pasaporte: VE123ABC",
        )

    def test_client_without_document_can_create_warranty_request(self):
        client = Client.objects.create(
            identification_type=Client.IdentificationType.NONE,
            name="Cliente sin documento",
            email="sin.documento@example.com",
            created_by=self.admin,
            updated_by=self.admin,
        )

        order, warranty = self.create_order_with_warranty(
            client,
            "sin-documento",
        )

        request = WarrantyRequest.objects.create(
            order=order,
            warranty=warranty,
            requested_on=self.today,
            problem_description="Falla cubierta.",
            created_by=self.admin,
        )

        self.assertEqual(
            request.client_identification_type_snapshot,
            Client.IdentificationType.NONE,
        )
        self.assertEqual(
            request.client_identification_number_snapshot,
            "",
        )
        self.assertEqual(
            request.client_rut_snapshot,
            "",
        )

        data = WarrantyRequestReadSerializer(request).data

        self.assertEqual(
            data["client_identification"],
            "Sin documento",
        )
