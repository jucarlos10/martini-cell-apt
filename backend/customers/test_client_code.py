from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from .models import Client


class ClientCodeTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_client_code",
            role=User.Role.ADMIN,
        )
        self.client.force_authenticate(user=self.admin)
        self.list_url = reverse("client-list-create")

    def create_customer(self, name="Cliente código"):
        return Client.objects.create(
            identification_type=Client.IdentificationType.NONE,
            name=name,
            phone="912345678",
            created_by=self.admin,
            updated_by=self.admin,
        )

    def test_new_client_receives_sequential_internal_code(self):
        customer = self.create_customer()

        self.assertEqual(
            customer.client_code,
            f"CLI-{customer.pk:06d}",
        )

    def test_api_exposes_client_code(self):
        customer = self.create_customer()

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data[0]["client_code"],
            customer.client_code,
        )

    def test_search_by_client_code(self):
        customer = self.create_customer()

        response = self.client.get(
            self.list_url,
            {"search": customer.client_code},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            customer.id,
        )

    def test_existing_search_by_name_still_works(self):
        customer = self.create_customer(
            name="María Búsqueda Código",
        )

        response = self.client.get(
            self.list_url,
            {"search": "María"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            customer.id,
        )

    def test_client_code_cannot_be_changed_through_api(self):
        customer = self.create_customer()
        original_code = customer.client_code

        response = self.client.patch(
            reverse(
                "client-detail",
                kwargs={"pk": customer.pk},
            ),
            {
                "client_code": "CLI-999999",
                "name": "Nombre actualizado",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        customer.refresh_from_db()

        self.assertEqual(
            customer.client_code,
            original_code,
        )
        self.assertEqual(
            customer.name,
            "Nombre actualizado",
        )

    def test_model_preserves_client_code_on_save(self):
        customer = self.create_customer()
        original_code = customer.client_code

        customer.client_code = "CLI-999999"
        customer.name = "Nombre preservado"
        customer.save()
        customer.refresh_from_db()

        self.assertEqual(
            customer.client_code,
            original_code,
        )
        self.assertEqual(
            customer.name,
            "Nombre preservado",
        )
