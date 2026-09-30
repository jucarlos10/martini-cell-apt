from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment
from orders.models import ServiceOrder


class HU26PermissionMatrixTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_hu26",
            role=User.Role.ADMIN,
        )
        self.technician = User.objects.create_user(
            username="tech_hu26",
            role=User.Role.TECH,
        )
        self.helper = User.objects.create_user(
            username="helper_hu26",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente HU26",
            phone="912345678",
            email="hu26@example.com",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model="Equipo HU26",
            imei="123456789012345",
            serial_number="HU26-001",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.order = ServiceOrder.objects.create(
            client=self.customer,
            equipment=self.equipment,
            reported_issue="Falla de prueba HU26",
            initial_observations="Orden base para matriz de permisos.",
            created_by=self.admin,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_helper_can_create_client(self):
        self.authenticate(self.helper)

        response = self.client.post(
            reverse("client-list-create"),
            {
                "rut": "11.111.111-1",
                "name": "Cliente creado por helper",
                "phone": "923456789",
                "email": "helper@example.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        created = Client.objects.get(pk=response.data["id"])
        self.assertEqual(created.created_by, self.helper)
        self.assertEqual(created.updated_by, self.helper)

    def test_helper_cannot_modify_client(self):
        self.authenticate(self.helper)

        response = self.client.patch(
            reverse(
                "client-detail",
                kwargs={"pk": self.customer.pk},
            ),
            {"name": "Cambio no permitido"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.name, "Cliente HU26")

    def test_technician_can_modify_client(self):
        self.authenticate(self.technician)

        response = self.client.patch(
            reverse(
                "client-detail",
                kwargs={"pk": self.customer.pk},
            ),
            {"name": "Cliente modificado por técnico"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_helper_cannot_read_client_change_history(self):
        self.authenticate(self.helper)

        response = self.client.get(
            reverse(
                "client-change-history",
                kwargs={"pk": self.customer.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_helper_can_create_equipment(self):
        self.authenticate(self.helper)

        response = self.client.post(
            reverse("equipment-list-create"),
            {
                "client": self.customer.pk,
                "equipment_type": Equipment.EquipmentType.NOTEBOOK,
                "brand": "Lenovo",
                "model": "Notebook HU26",
                "serial_number": "HU26-002",
                "color": "Negro",
                "observations": "Equipo ingresado por helper.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        created = Equipment.objects.get(pk=response.data["id"])
        self.assertEqual(created.created_by, self.helper)
        self.assertEqual(created.updated_by, self.helper)

    def test_helper_cannot_modify_equipment(self):
        self.authenticate(self.helper)

        response = self.client.patch(
            reverse(
                "equipment-detail",
                kwargs={"pk": self.equipment.pk},
            ),
            {"brand": "Cambio no permitido"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.equipment.refresh_from_db()
        self.assertEqual(self.equipment.brand, "Samsung")

    def test_technician_can_modify_equipment(self):
        self.authenticate(self.technician)

        response = self.client.patch(
            reverse(
                "equipment-detail",
                kwargs={"pk": self.equipment.pk},
            ),
            {"brand": "Samsung actualizado"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_helper_can_create_service_order(self):
        self.authenticate(self.helper)

        response = self.client.post(
            reverse("service-order-list-create"),
            {
                "client": self.customer.pk,
                "equipment": self.equipment.pk,
                "reported_issue": "Orden creada por helper",
                "initial_observations": "Recepción HU26",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        created = ServiceOrder.objects.get(pk=response.data["id"])
        self.assertEqual(created.created_by, self.helper)

    def test_helper_cannot_modify_service_order(self):
        self.authenticate(self.helper)

        response = self.client.patch(
            reverse(
                "service-order-detail",
                kwargs={"pk": self.order.pk},
            ),
            {"reported_issue": "Cambio no permitido"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.order.refresh_from_db()
        self.assertEqual(
            self.order.reported_issue,
            "Falla de prueba HU26",
        )

    def test_technician_can_modify_service_order(self):
        self.authenticate(self.technician)

        response = self.client.patch(
            reverse(
                "service-order-detail",
                kwargs={"pk": self.order.pk},
            ),
            {"reported_issue": "Actualizado por técnico"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_helper_cannot_read_technical_report_history(self):
        self.authenticate(self.helper)

        response = self.client.get(
            reverse(
                "order-technical-report-history",
                kwargs={"pk": self.order.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
