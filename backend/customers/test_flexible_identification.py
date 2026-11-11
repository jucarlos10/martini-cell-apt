from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from .models import Client


class FlexibleClientIdentificationTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_identificacion_cliente",
            role=User.Role.ADMIN,
        )
        self.client.force_authenticate(user=self.admin)
        self.list_url = reverse("client-list-create")

    def test_client_can_be_created_without_document(self):
        response = self.client.post(
            self.list_url,
            {
                "identification_type": Client.IdentificationType.NONE,
                "name": "Cliente sin documento",
                "phone": "912345678",
                "email": "",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        created = Client.objects.get(pk=response.data["id"])

        self.assertEqual(
            created.identification_type,
            Client.IdentificationType.NONE,
        )
        self.assertIsNone(created.rut)
        self.assertEqual(created.document_number, "")
        self.assertEqual(
            response.data["identification_display"],
            "Sin documento",
        )

    def test_client_can_be_created_with_passport_and_email_only(self):
        response = self.client.post(
            self.list_url,
            {
                "identification_type": (
                    Client.IdentificationType.PASSPORT
                ),
                "document_number": "ve123abc",
                "name": "Cliente con pasaporte",
                "phone": "",
                "email": "pasaporte@example.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        created = Client.objects.get(pk=response.data["id"])

        self.assertIsNone(created.rut)
        self.assertEqual(
            created.document_number,
            "VE123ABC",
        )
        self.assertEqual(
            response.data["identification_display"],
            "Pasaporte: VE123ABC",
        )

    def test_client_can_be_created_with_foreign_document(self):
        response = self.client.post(
            self.list_url,
            {
                "identification_type": (
                    Client.IdentificationType.FOREIGN_DOCUMENT
                ),
                "document_number": "v-12345678",
                "name": "Cliente extranjero",
                "phone": "956789123",
                "email": "",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["document_number"],
            "V-12345678",
        )
        self.assertEqual(
            response.data["identification_display"],
            "Documento extranjero: V-12345678",
        )

    def test_rut_type_still_requires_and_validates_rut(self):
        response = self.client.post(
            self.list_url,
            {
                "identification_type": Client.IdentificationType.RUT,
                "name": "Cliente sin RUT",
                "phone": "912345678",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("rut", response.data)

    def test_passport_requires_document_number(self):
        response = self.client.post(
            self.list_url,
            {
                "identification_type": (
                    Client.IdentificationType.PASSPORT
                ),
                "name": "Cliente sin pasaporte",
                "phone": "912345678",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("document_number", response.data)

    def test_client_requires_at_least_one_contact_method(self):
        response = self.client.post(
            self.list_url,
            {
                "identification_type": Client.IdentificationType.NONE,
                "name": "Cliente incomunicable",
                "phone": "",
                "email": "",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("contact", response.data)

    def test_duplicate_passport_is_rejected_case_insensitively(self):
        Client.objects.create(
            identification_type=Client.IdentificationType.PASSPORT,
            document_number="VE123ABC",
            name="Primer cliente",
            phone="912345678",
            created_by=self.admin,
            updated_by=self.admin,
        )

        response = self.client.post(
            self.list_url,
            {
                "identification_type": (
                    Client.IdentificationType.PASSPORT
                ),
                "document_number": "ve123abc",
                "name": "Segundo cliente",
                "phone": "923456789",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("document_number", response.data)

    def test_search_by_foreign_document(self):
        customer = Client.objects.create(
            identification_type=(
                Client.IdentificationType.FOREIGN_DOCUMENT
            ),
            document_number="V-99887766",
            name="Cliente búsqueda",
            phone="912345678",
            created_by=self.admin,
            updated_by=self.admin,
        )

        response = self.client.get(
            self.list_url,
            {"search": "99887766"},
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
