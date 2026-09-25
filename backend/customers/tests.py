from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from .models import Client, ClientChangeHistory


class ClientManagementTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_clientes_tec01",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tecnico_clientes_tec01",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="ayudante_clientes_tec01",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente de prueba Alfa",
            phone="912345678",
            email="alfa@example.com",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.list_url = reverse("client-list-create")

        self.client.force_authenticate(
            user=self.admin
        )

    def detail_url(self, customer):
        return reverse(
            "client-detail",
            kwargs={"pk": customer.pk},
        )

    def history_url(self, customer):
        return reverse(
            "client-change-history",
            kwargs={"pk": customer.pk},
        )

    def create_payload(self):
        return {
            "rut": "11.111.111-1",
            "name": "Cliente de prueba Beta",
            "phone": "923456789",
            "email": "beta@example.com",
        }

    def test_anonymous_user_cannot_list_clients(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_anonymous_user_cannot_create_client(self):
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
            Client.objects.count(),
            1,
        )

    def test_authenticated_user_can_list_clients(self):
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
            self.customer.id,
        )

    def test_technician_can_create_client_and_normalize_rut(self):
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

        created_customer = Client.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            created_customer.rut,
            "111111111",
        )

        self.assertEqual(
            response.data["rut"],
            "111111111",
        )

        self.assertEqual(
            created_customer.created_by,
            self.technician,
        )

        self.assertEqual(
            created_customer.updated_by,
            self.technician,
        )

    def test_missing_required_name_is_rejected(self):
        payload = self.create_payload()
        payload.pop("name")

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
            "name",
            response.data,
        )

        self.assertEqual(
            Client.objects.count(),
            1,
        )

    def test_invalid_rut_verifier_is_rejected(self):
        payload = self.create_payload()

        payload["rut"] = "12.345.678-9"

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
            "rut",
            response.data,
        )

        self.assertEqual(
            Client.objects.count(),
            1,
        )

    def test_rut_with_invalid_body_is_rejected(self):
        payload = self.create_payload()

        payload["rut"] = "12A3456785"

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
            "rut",
            response.data,
        )

    def test_duplicate_rut_with_different_format_is_rejected(self):
        payload = self.create_payload()

        # El cliente existente tiene RUT 12.345.678-5.
        # El formato siguiente representa el mismo RUT.
        payload["rut"] = "123456785"

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
            "rut",
            response.data,
        )

        self.assertEqual(
            Client.objects.count(),
            1,
        )

    def test_lowercase_k_is_normalized(self):
        payload = self.create_payload()

        # RUT sintético con dígito verificador K.
        payload["rut"] = "11.111.112-k"

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        created_customer = Client.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            created_customer.rut,
            "11111112K",
        )

    def test_search_by_name_is_case_insensitive(self):
        response = self.client.get(
            self.list_url,
            {"search": "ALFA"},
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
            self.customer.id,
        )

    def test_search_by_phone_email_and_formatted_rut(self):
        searches = (
            "912345678",
            "alfa@example.com",
            "12.345.678-5",
        )

        for search in searches:
            with self.subTest(search=search):
                response = self.client.get(
                    self.list_url,
                    {"search": search},
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
                    self.customer.id,
                )

    def test_search_without_matches_returns_empty_list(self):
        response = self.client.get(
            self.list_url,
            {"search": "Sin coincidencias TEC01"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            0,
        )

    def test_authenticated_user_can_retrieve_client(self):
        self.client.force_authenticate(
            user=self.helper
        )

        response = self.client.get(
            self.detail_url(self.customer)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["id"],
            self.customer.id,
        )

        self.assertEqual(
            response.data["name"],
            self.customer.name,
        )

    def test_nonexistent_client_returns_404(self):
        response = self.client.get(
            reverse(
                "client-detail",
                kwargs={"pk": 999999},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_anonymous_user_cannot_read_client_detail(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.detail_url(self.customer)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_update_registers_changes_and_responsible_user(self):
        self.client.force_authenticate(
            user=self.technician
        )

        response = self.client.patch(
            self.detail_url(self.customer),
            {
                "name": "Cliente Alfa actualizado",
                "phone": "934567890",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.customer.refresh_from_db()

        self.assertEqual(
            self.customer.name,
            "Cliente Alfa actualizado",
        )

        self.assertEqual(
            self.customer.phone,
            "934567890",
        )

        self.assertEqual(
            self.customer.updated_by,
            self.technician,
        )

        self.assertEqual(
            ClientChangeHistory.objects.filter(
                client=self.customer
            ).count(),
            1,
        )

        history = ClientChangeHistory.objects.get(
            client=self.customer
        )

        self.assertEqual(
            history.changed_by,
            self.technician,
        )

        self.assertEqual(
            history.changes["name"],
            {
                "from": "Cliente de prueba Alfa",
                "to": "Cliente Alfa actualizado",
            },
        )

        self.assertEqual(
            history.changes["phone"],
            {
                "from": "912345678",
                "to": "934567890",
            },
        )

        self.assertNotIn(
            "email",
            history.changes,
        )

    def test_update_without_changes_does_not_create_history(self):
        response = self.client.patch(
            self.detail_url(self.customer),
            {
                "name": self.customer.name,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            ClientChangeHistory.objects.filter(
                client=self.customer
            ).exists()
        )

    def test_rut_update_is_normalized_and_audited(self):
        response = self.client.patch(
            self.detail_url(self.customer),
            {
                "rut": "11.111.111-1",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.customer.refresh_from_db()

        self.assertEqual(
            self.customer.rut,
            "111111111",
        )

        history = ClientChangeHistory.objects.get(
            client=self.customer
        )

        self.assertEqual(
            history.changes["rut"],
            {
                "from": "123456785",
                "to": "111111111",
            },
        )

    def test_update_cannot_duplicate_another_client_rut(self):
        Client.objects.create(
            rut="11.111.111-1",
            name="Cliente de prueba Beta",
            phone="923456789",
            created_by=self.admin,
            updated_by=self.admin,
        )

        response = self.client.patch(
            self.detail_url(self.customer),
            {
                "rut": "11.111.111-1",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "rut",
            response.data,
        )

        self.customer.refresh_from_db()

        self.assertEqual(
            self.customer.rut,
            "123456785",
        )

        self.assertFalse(
            ClientChangeHistory.objects.filter(
                client=self.customer
            ).exists()
        )

    def test_authenticated_user_can_read_change_history(self):
        self.client.patch(
            self.detail_url(self.customer),
            {
                "name": "Nombre actualizado",
            },
            format="json",
        )

        self.client.force_authenticate(
            user=self.technician
        )

        response = self.client.get(
            self.history_url(self.customer)
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
            response.data[0]["changed_by_username"],
            self.admin.username,
        )

        self.assertEqual(
            response.data[0]["changes"]["name"]["to"],
            "Nombre actualizado",
        )

    def test_anonymous_user_cannot_read_change_history(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.history_url(self.customer)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_anonymous_user_cannot_update_client(self):
        self.client.force_authenticate(user=None)

        response = self.client.patch(
            self.detail_url(self.customer),
            {
                "name": "Cambio no autorizado",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.customer.refresh_from_db()

        self.assertEqual(
            self.customer.name,
            "Cliente de prueba Alfa",
        )