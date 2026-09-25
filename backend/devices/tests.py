from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from orders.models import OrderTechnicalReport, ServiceOrder

from .models import Equipment


class EquipmentManagementTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_equipos_tec01",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tecnico_equipos_tec01",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="ayudante_equipos_tec01",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente de prueba Alfa",
            phone="912345678",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.other_customer = Client.objects.create(
            rut="11.111.111-1",
            name="Cliente de prueba Beta",
            phone="923456789",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model="Equipo de prueba Alfa",
            imei="123456789012345",
            serial_number="SN-ABC-001",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.list_url = reverse("equipment-list-create")

        self.client.force_authenticate(
            user=self.admin
        )

    def detail_url(self, equipment):
        return reverse(
            "equipment-detail",
            kwargs={"pk": equipment.pk},
        )

    def history_url(self, equipment):
        return reverse(
            "equipment-history",
            kwargs={"pk": equipment.pk},
        )

    def create_payload(self):
        return {
            "client": self.customer.pk,
            "equipment_type": Equipment.EquipmentType.NOTEBOOK,
            "brand": "Lenovo",
            "model": "Notebook de prueba",
            "imei": "98765 43210-12345",
            "serial_number": " sn-xyz-002 ",
            "color": "Negro",
            "observations": "Equipo ficticio para TEC-01.",
        }

    def create_order(self, equipment, reported_issue):
        response = self.client.post(
            reverse("service-order-list-create"),
            {
                "client": equipment.client_id,
                "equipment": equipment.pk,
                "reported_issue": reported_issue,
                "initial_observations": (
                    "Orden ficticia para probar el historial."
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        return ServiceOrder.objects.get(
            pk=response.data["id"]
        )

    def test_anonymous_user_cannot_list_equipment(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_anonymous_user_cannot_create_equipment(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.list_url,
            self.create_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertEqual(
            Equipment.objects.count(),
            1,
        )

    def test_anonymous_user_cannot_read_equipment_detail(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.detail_url(self.equipment)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_anonymous_user_cannot_update_equipment(self):
        self.client.force_authenticate(user=None)

        response = self.client.patch(
            self.detail_url(self.equipment),
            {"brand": "Cambio no autorizado"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.equipment.refresh_from_db()

        self.assertEqual(
            self.equipment.brand,
            "Samsung",
        )

    def test_anonymous_user_cannot_read_equipment_history(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.history_url(self.equipment)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_authenticated_user_can_list_equipment(self):
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

        self.assertEqual(
            response.data[0]["id"],
            self.equipment.pk,
        )

    def test_helper_can_read_equipment_detail(self):
        self.client.force_authenticate(
            user=self.helper
        )

        response = self.client.get(
            self.detail_url(self.equipment)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["id"],
            self.equipment.pk,
        )

        self.assertEqual(
            response.data["client_name"],
            self.customer.name,
        )

    def test_technician_can_create_equipment_and_normalize_ids(self):
        self.client.force_authenticate(
            user=self.technician
        )

        response = self.client.post(
            self.list_url,
            self.create_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        created_equipment = Equipment.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            created_equipment.imei,
            "987654321012345",
        )

        self.assertEqual(
            created_equipment.serial_number,
            "SN-XYZ-002",
        )

        self.assertEqual(
            created_equipment.client,
            self.customer,
        )

        self.assertEqual(
            created_equipment.created_by,
            self.technician,
        )

        self.assertEqual(
            created_equipment.updated_by,
            self.technician,
        )

        self.assertEqual(
            response.data["client_name"],
            self.customer.name,
        )

    def test_blank_identifiers_are_stored_as_null(self):
        payload = self.create_payload()

        payload["imei"] = ""
        payload["serial_number"] = ""

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        created_equipment = Equipment.objects.get(
            pk=response.data["id"]
        )

        self.assertIsNone(created_equipment.imei)
        self.assertIsNone(created_equipment.serial_number)

    def test_multiple_equipment_can_have_no_identifiers(self):
        payload = self.create_payload()

        payload["imei"] = None
        payload["serial_number"] = None

        first_response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        second_response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertNotEqual(
            first_response.data["id"],
            second_response.data["id"],
        )

    def test_missing_client_is_rejected(self):
        payload = self.create_payload()
        payload.pop("client")

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("client", response.data)

    def test_nonexistent_client_is_rejected(self):
        payload = self.create_payload()
        payload["client"] = 999999

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("client", response.data)

        self.assertEqual(
            Equipment.objects.count(),
            1,
        )

    def test_missing_brand_is_rejected(self):
        payload = self.create_payload()
        payload.pop("brand")

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("brand", response.data)

    def test_invalid_equipment_type_is_rejected(self):
        payload = self.create_payload()
        payload["equipment_type"] = "TIPO_INEXISTENTE"

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "equipment_type",
            response.data,
        )

    def test_duplicate_imei_with_different_format_is_rejected(self):
        payload = self.create_payload()

        # Corresponde al mismo IMEI del equipo existente.
        payload["imei"] = "12345 67890-12345"

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("imei", response.data)

        self.assertEqual(
            Equipment.objects.count(),
            1,
        )

    def test_duplicate_serial_number_is_rejected(self):
        payload = self.create_payload()

        # Corresponde al mismo número de serie existente.
        payload["serial_number"] = " sn-abc-001 "

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "serial_number",
            response.data,
        )

        self.assertEqual(
            Equipment.objects.count(),
            1,
        )

    def test_update_normalizes_imei_and_serial_number(self):
        response = self.client.patch(
            self.detail_url(self.equipment),
            {
                "imei": "98765 43210-12345",
                "serial_number": " sn-xyz-002 ",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.equipment.refresh_from_db()

        self.assertEqual(
            self.equipment.imei,
            "987654321012345",
        )

        self.assertEqual(
            self.equipment.serial_number,
            "SN-XYZ-002",
        )

    def test_update_cannot_duplicate_another_equipment_imei(self):
        other_equipment = Equipment.objects.create(
            client=self.other_customer,
            equipment_type=Equipment.EquipmentType.NOTEBOOK,
            brand="Lenovo",
            model="Otro equipo ficticio",
            imei="987654321012345",
            created_by=self.admin,
        )

        response = self.client.patch(
            self.detail_url(self.equipment),
            {
                "imei": "98765 43210-12345",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("imei", response.data)

        self.equipment.refresh_from_db()

        self.assertEqual(
            self.equipment.imei,
            "123456789012345",
        )

        self.assertTrue(
            Equipment.objects.filter(
                pk=other_equipment.pk
            ).exists()
        )

    def test_update_cannot_duplicate_another_serial_number(self):
        Equipment.objects.create(
            client=self.other_customer,
            equipment_type=Equipment.EquipmentType.NOTEBOOK,
            brand="Lenovo",
            model="Otro equipo ficticio",
            serial_number="SN-XYZ-002",
            created_by=self.admin,
        )

        response = self.client.patch(
            self.detail_url(self.equipment),
            {
                "serial_number": " sn-xyz-002 ",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "serial_number",
            response.data,
        )

        self.equipment.refresh_from_db()

        self.assertEqual(
            self.equipment.serial_number,
            "SN-ABC-001",
        )

    def test_update_records_responsible_user(self):
        self.client.force_authenticate(
            user=self.technician
        )

        response = self.client.patch(
            self.detail_url(self.equipment),
            {
                "color": "Azul",
                "observations": "Observación actualizada.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.equipment.refresh_from_db()

        self.assertEqual(
            self.equipment.color,
            "Azul",
        )

        self.assertEqual(
            self.equipment.observations,
            "Observación actualizada.",
        )

        self.assertEqual(
            self.equipment.updated_by,
            self.technician,
        )

    def test_nonexistent_equipment_returns_404(self):
        response = self.client.get(
            reverse(
                "equipment-detail",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_equipment_without_orders_has_empty_history(self):
        response = self.client.get(
            self.history_url(self.equipment)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            0,
        )

    def test_history_contains_only_orders_for_selected_equipment(self):
        first_order = self.create_order(
            self.equipment,
            "Primera falla ficticia.",
        )

        second_order = self.create_order(
            self.equipment,
            "Segunda falla ficticia.",
        )

        other_equipment = Equipment.objects.create(
            client=self.other_customer,
            equipment_type=Equipment.EquipmentType.PC,
            brand="Marca ficticia",
            model="Otro equipo",
            created_by=self.admin,
        )

        other_order = self.create_order(
            other_equipment,
            "Falla de otro equipo.",
        )

        response = self.client.get(
            self.history_url(self.equipment)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        returned_ids = {
            item["id"]
            for item in response.data
        }

        self.assertEqual(
            returned_ids,
            {
                first_order.pk,
                second_order.pk,
            },
        )

        self.assertNotIn(
            other_order.pk,
            returned_ids,
        )

    def test_history_includes_technical_report_information(self):
        order = self.create_order(
            self.equipment,
            "Falla ficticia de encendido.",
        )

        OrderTechnicalReport.objects.create(
            order=order,
            diagnosis="Diagnóstico sintético.",
            repair_actions="Revisión de componentes.",
            repair_observations="Sin observaciones.",
            parts_description="Sin repuestos.",
            result=OrderTechnicalReport.Result.REPARADO,
            technician=self.technician,
            created_by=self.admin,
            updated_by=self.admin,
        )

        response = self.client.get(
            self.history_url(self.equipment)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        item = response.data[0]

        self.assertEqual(
            item["id"],
            order.pk,
        )

        self.assertEqual(
            item["tracking_code"],
            order.tracking_code,
        )

        self.assertEqual(
            item["diagnosis"],
            "Diagnóstico sintético.",
        )

        self.assertEqual(
            item["repair_actions"],
            "Revisión de componentes.",
        )

        self.assertEqual(
            item["technician_username"],
            self.technician.username,
        )

        self.assertEqual(
            item["order_url"],
            f"/api/orders/{order.pk}/",
        )

    def test_nonexistent_equipment_history_returns_404(self):
        response = self.client.get(
            reverse(
                "equipment-history",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )