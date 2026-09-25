from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment

from .models import OrderStatusHistory, ServiceOrder


class ServiceOrderManagementTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_ordenes_tec01",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tecnico_ordenes_tec01",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="ayudante_ordenes_tec01",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente ficticio Alfa",
            phone="912345678",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.other_customer = Client.objects.create(
            rut="11.111.111-1",
            name="Cliente ficticio Beta",
            phone="923456789",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Marca de prueba",
            model="Modelo Alfa",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.other_equipment = Equipment.objects.create(
            client=self.other_customer,
            equipment_type=Equipment.EquipmentType.NOTEBOOK,
            brand="Marca de prueba",
            model="Modelo Beta",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.list_url = reverse("service-order-list-create")

        self.client.force_authenticate(
            user=self.admin
        )

    def order_payload(self):
        return {
            "client": self.customer.pk,
            "equipment": self.equipment.pk,
            "reported_issue": "Falla ficticia de encendido.",
            "initial_observations": (
                "Observaciones de prueba para TEC-01."
            ),
        }

    def detail_url(self, order):
        return reverse(
            "service-order-detail",
            kwargs={"pk": order.pk},
        )

    def status_url(self, order):
        return reverse(
            "order-status",
            kwargs={"pk": order.pk},
        )

    def history_url(self, order):
        return reverse(
            "order-status-history",
            kwargs={"pk": order.pk},
        )

    def create_order(self):
        response = self.client.post(
            self.list_url,
            self.order_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        return ServiceOrder.objects.get(
            pk=response.data["id"]
        )

    def test_anonymous_user_cannot_list_orders(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_anonymous_user_cannot_create_order(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.list_url,
            self.order_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertEqual(
            ServiceOrder.objects.count(),
            0,
        )

    def test_anonymous_user_cannot_read_order_detail(self):
        order = self.create_order()

        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.detail_url(order)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_anonymous_user_cannot_update_order(self):
        order = self.create_order()

        self.client.force_authenticate(user=None)

        response = self.client.patch(
            self.detail_url(order),
            {
                "reported_issue": "Cambio no autorizado.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.reported_issue,
            "Falla ficticia de encendido.",
        )

    def test_admin_can_create_order_with_initial_history(self):
        response = self.client.post(
            self.list_url,
            self.order_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        order = ServiceOrder.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            order.client,
            self.customer,
        )

        self.assertEqual(
            order.equipment,
            self.equipment,
        )

        self.assertEqual(
            order.reported_issue,
            "Falla ficticia de encendido.",
        )

        self.assertEqual(
            order.status,
            ServiceOrder.Status.RECEIVED,
        )

        self.assertEqual(
            order.created_by,
            self.admin,
        )

        self.assertIsNotNone(order.received_at)

        self.assertEqual(
            order.status_history.count(),
            1,
        )

        initial_event = order.status_history.get()

        self.assertIsNone(
            initial_event.from_status
        )

        self.assertEqual(
            initial_event.to_status,
            ServiceOrder.Status.RECEIVED,
        )

        self.assertEqual(
            initial_event.changed_by,
            self.admin,
        )

    def test_technician_can_create_order(self):
        self.client.force_authenticate(
            user=self.technician
        )

        response = self.client.post(
            self.list_url,
            self.order_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        order = ServiceOrder.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            order.created_by,
            self.technician,
        )

        self.assertEqual(
            order.status_history.get().changed_by,
            self.technician,
        )

    def test_each_order_receives_unique_tracking_code(self):
        first_order = self.create_order()
        second_order = self.create_order()

        self.assertRegex(
            first_order.tracking_code,
            r"^MC-[A-F0-9]{12}$",
        )

        self.assertRegex(
            second_order.tracking_code,
            r"^MC-[A-F0-9]{12}$",
        )

        self.assertNotEqual(
            first_order.tracking_code,
            second_order.tracking_code,
        )

    def test_client_cannot_force_tracking_code_or_initial_status(self):
        payload = self.order_payload()

        payload["tracking_code"] = "MC-CODIGOFALSO"
        payload["status"] = ServiceOrder.Status.CLOSED

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        order = ServiceOrder.objects.get(
            pk=response.data["id"]
        )

        self.assertNotEqual(
            order.tracking_code,
            "MC-CODIGOFALSO",
        )

        self.assertRegex(
            order.tracking_code,
            r"^MC-[A-F0-9]{12}$",
        )

        self.assertEqual(
            order.status,
            ServiceOrder.Status.RECEIVED,
        )

        self.assertEqual(
            order.status_history.count(),
            1,
        )

    def test_missing_client_is_rejected(self):
        payload = self.order_payload()
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

        self.assertEqual(
            ServiceOrder.objects.count(),
            0,
        )

    def test_missing_equipment_is_rejected(self):
        payload = self.order_payload()
        payload.pop("equipment")

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("equipment", response.data)

        self.assertEqual(
            ServiceOrder.objects.count(),
            0,
        )

    def test_missing_reported_issue_is_rejected(self):
        payload = self.order_payload()
        payload.pop("reported_issue")

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
            "reported_issue",
            response.data,
        )

        self.assertEqual(
            ServiceOrder.objects.count(),
            0,
        )

    def test_equipment_must_belong_to_selected_client(self):
        payload = self.order_payload()

        payload["equipment"] = self.other_equipment.pk

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
            "equipment",
            response.data,
        )

        self.assertEqual(
            ServiceOrder.objects.count(),
            0,
        )

        self.assertEqual(
            OrderStatusHistory.objects.count(),
            0,
        )

    def test_nonexistent_client_is_rejected(self):
        payload = self.order_payload()
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

    def test_nonexistent_equipment_is_rejected(self):
        payload = self.order_payload()
        payload["equipment"] = 999999

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
            "equipment",
            response.data,
        )

    def test_authenticated_user_can_list_orders(self):
        first_order = self.create_order()
        second_order = self.create_order()

        self.client.force_authenticate(
            user=self.technician
        )

        response = self.client.get(self.list_url)

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

    def test_helper_can_read_order_detail(self):
        order = self.create_order()

        self.client.force_authenticate(
            user=self.helper
        )

        response = self.client.get(
            self.detail_url(order)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["id"],
            order.pk,
        )

        self.assertEqual(
            response.data["tracking_code"],
            order.tracking_code,
        )

        self.assertEqual(
            response.data["client_name"],
            self.customer.name,
        )

        self.assertEqual(
            response.data["equipment_description"],
            "Marca de prueba Modelo Alfa",
        )

        self.assertEqual(
            response.data["status"],
            ServiceOrder.Status.RECEIVED,
        )

    def test_nonexistent_order_detail_returns_404(self):
        response = self.client.get(
            reverse(
                "service-order-detail",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_update_reported_issue_and_observations(self):
        order = self.create_order()

        response = self.client.patch(
            self.detail_url(order),
            {
                "reported_issue": "Falla ficticia actualizada.",
                "initial_observations": (
                    "Observación actualizada para TEC-01."
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.reported_issue,
            "Falla ficticia actualizada.",
        )

        self.assertEqual(
            order.initial_observations,
            "Observación actualizada para TEC-01.",
        )

    def test_general_update_cannot_change_tracking_code_or_status(self):
        order = self.create_order()

        original_tracking_code = order.tracking_code

        response = self.client.patch(
            self.detail_url(order),
            {
                "tracking_code": "MC-CODIGOFALSO",
                "status": ServiceOrder.Status.CLOSED,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.tracking_code,
            original_tracking_code,
        )

        self.assertEqual(
            order.status,
            ServiceOrder.Status.RECEIVED,
        )

        self.assertEqual(
            order.status_history.count(),
            1,
        )

    def test_update_rejects_equipment_from_another_client(self):
        order = self.create_order()

        response = self.client.patch(
            self.detail_url(order),
            {
                "equipment": self.other_equipment.pk,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "equipment",
            response.data,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.equipment,
            self.equipment,
        )

        self.assertEqual(
            order.client,
            self.customer,
        )

    def test_update_rejects_client_mismatch_with_equipment(self):
        order = self.create_order()

        response = self.client.patch(
            self.detail_url(order),
            {
                "client": self.other_customer.pk,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "equipment",
            response.data,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.client,
            self.customer,
        )

        self.assertEqual(
            order.equipment,
            self.equipment,
        )

    def test_anonymous_user_cannot_read_status_history(self):
        order = self.create_order()

        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.history_url(order)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_initial_status_history_is_available(self):
        order = self.create_order()

        response = self.client.get(
            self.history_url(order)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        initial_event = response.data[0]

        self.assertIsNone(
            initial_event["from_status"]
        )

        self.assertEqual(
            initial_event["to_status"],
            ServiceOrder.Status.RECEIVED,
        )

        self.assertEqual(
            initial_event["changed_by_username"],
            self.admin.username,
        )

    def test_status_change_is_reflected_in_history_endpoint(self):
        order = self.create_order()

        self.client.force_authenticate(
            user=self.technician
        )

        change_response = self.client.patch(
            self.status_url(order),
            {
                "status": ServiceOrder.Status.DIAGNOSIS,
                "note": "Inicio de diagnóstico de prueba.",
            },
            format="json",
        )

        self.assertEqual(
            change_response.status_code,
            status.HTTP_200_OK,
        )

        history_response = self.client.get(
            self.history_url(order)
        )

        self.assertEqual(
            history_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(history_response.data),
            2,
        )

        second_event = history_response.data[1]

        self.assertEqual(
            second_event["from_status"],
            ServiceOrder.Status.RECEIVED,
        )

        self.assertEqual(
            second_event["to_status"],
            ServiceOrder.Status.DIAGNOSIS,
        )

        self.assertEqual(
            second_event["note"],
            "Inicio de diagnóstico de prueba.",
        )

        self.assertEqual(
            second_event["changed_by_username"],
            self.technician.username,
        )

    def test_nonexistent_order_history_returns_404(self):
        response = self.client.get(
            reverse(
                "order-status-history",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )