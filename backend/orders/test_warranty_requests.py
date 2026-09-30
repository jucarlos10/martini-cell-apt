import base64
import tempfile
from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment

from .models import OrderWarranty, ServiceOrder
from .warranty_request_models import (
    WarrantyRequest,
    WarrantyRequestHistory,
)


class WarrantyRequestTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_warranty_request",
            role=User.Role.ADMIN,
        )
        self.technician = User.objects.create_user(
            username="tech_warranty_request",
            role=User.Role.TECH,
        )
        self.helper = User.objects.create_user(
            username="helper_warranty_request",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente reclamo",
            phone="912345678",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model="Equipo garantía",
            created_by=self.admin,
        )

        self.order = ServiceOrder.objects.create(
            client=self.customer,
            equipment=self.equipment,
            reported_issue="Falla original.",
            created_by=self.admin,
        )

        self.other_order = ServiceOrder.objects.create(
            client=self.customer,
            equipment=self.equipment,
            reported_issue="Otra orden.",
            created_by=self.admin,
        )

        self.today = timezone.localdate()

        self.active_warranty = self.create_warranty(
            order=self.order,
            starts_on=self.today - timedelta(days=10),
            ends_on=self.today + timedelta(days=30),
        )

        self.list_url = reverse(
            "warranty-request-list-create",
            kwargs={"pk": self.order.pk},
        )

        self.client.force_authenticate(user=self.admin)

    def create_warranty(
        self,
        *,
        order,
        starts_on=None,
        ends_on=None,
        is_applicable=True,
    ):
        if is_applicable:
            starts_on = (
                starts_on
                if starts_on is not None
                else self.today - timedelta(days=1)
            )
            ends_on = (
                ends_on
                if ends_on is not None
                else self.today + timedelta(days=30)
            )
            conditions = "Cobertura de prueba."
        else:
            starts_on = None
            ends_on = None
            conditions = "No aplica."

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

    def request_payload(self, warranty=None, **changes):
        payload = {
            "warranty": (
                warranty.pk
                if warranty is not None
                else self.active_warranty.pk
            ),
            "requested_on": self.today.isoformat(),
            "problem_description": "El cliente reporta la misma falla.",
        }
        payload.update(changes)
        return payload

    def create_request(self, warranty=None, **changes):
        return self.client.post(
            self.list_url,
            self.request_payload(
                warranty=warranty,
                **changes,
            ),
            format="json",
        )

    def detail_url(self, request_id):
        return reverse(
            "warranty-request-detail",
            kwargs={
                "pk": self.order.pk,
                "request_id": request_id,
            },
        )

    def history_url(self, request_id):
        return reverse(
            "warranty-request-history",
            kwargs={
                "pk": self.order.pk,
                "request_id": request_id,
            },
        )

    def evidence_url(self, request_id, order=None):
        return reverse(
            "warranty-request-evidence",
            kwargs={
                "pk": (order or self.order).pk,
                "request_id": request_id,
            },
        )

    def by_warranty_url(self, warranty_id):
        return reverse(
            "warranty-requests-by-warranty",
            kwargs={
                "pk": self.order.pk,
                "warranty_id": warranty_id,
            },
        )

    def test_create_active_request_and_first_history(self):
        response = self.create_request()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(WarrantyRequest.objects.count(), 1)
        self.assertEqual(WarrantyRequestHistory.objects.count(), 1)

        warranty_request = WarrantyRequest.objects.get()

        self.assertEqual(
            warranty_request.order,
            self.order,
        )
        self.assertEqual(
            warranty_request.warranty,
            self.active_warranty,
        )
        self.assertEqual(
            warranty_request.status,
            WarrantyRequest.Status.PENDING,
        )
        self.assertEqual(
            warranty_request.created_by,
            self.admin,
        )
        self.assertEqual(
            warranty_request.created_by_username,
            self.admin.username,
        )
        self.assertEqual(
            warranty_request.client_name_snapshot,
            self.customer.name,
        )
        self.assertEqual(
            warranty_request.client_rut_snapshot,
            self.customer.rut,
        )

        history = WarrantyRequestHistory.objects.get()
        self.assertEqual(history.revision, 1)
        self.assertEqual(
            history.action,
            WarrantyRequestHistory.Action.CREATED,
        )
        self.assertIsNone(history.from_status)
        self.assertEqual(
            history.to_status,
            WarrantyRequest.Status.PENDING,
        )
        self.assertEqual(history.changed_by, self.admin)
        self.assertEqual(
            history.changed_by_username,
            self.admin.username,
        )

    def test_expired_warranty_allows_request_with_warning(self):
        expired = self.create_warranty(
            order=self.other_order,
            starts_on=self.today - timedelta(days=60),
            ends_on=self.today - timedelta(days=1),
        )

        # Se crea una URL de la otra orden para probar su garantía vencida.
        url = reverse(
            "warranty-request-list-create",
            kwargs={"pk": self.other_order.pk},
        )

        response = self.client.post(
            url,
            self.request_payload(warranty=expired),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["warranty_status"],
            OrderWarranty.WarrantyStatus.EXPIRED,
        )
        self.assertIsNotNone(
            response.data["coverage_warning"],
        )

    def test_not_applicable_warranty_is_rejected(self):
        warranty = self.create_warranty(
            order=self.other_order,
            is_applicable=False,
        )
        url = reverse(
            "warranty-request-list-create",
            kwargs={"pk": self.other_order.pk},
        )

        response = self.client.post(
            url,
            self.request_payload(warranty=warranty),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(WarrantyRequest.objects.exists())
        self.assertFalse(WarrantyRequestHistory.objects.exists())

    def test_not_started_warranty_is_rejected(self):
        warranty = self.create_warranty(
            order=self.other_order,
            starts_on=self.today + timedelta(days=1),
            ends_on=self.today + timedelta(days=30),
        )
        url = reverse(
            "warranty-request-list-create",
            kwargs={"pk": self.other_order.pk},
        )

        response = self.client.post(
            url,
            self.request_payload(warranty=warranty),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(WarrantyRequest.objects.exists())

    def test_blank_problem_description_is_rejected(self):
        response = self.create_request(
            problem_description="   ",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(WarrantyRequest.objects.exists())
        self.assertFalse(WarrantyRequestHistory.objects.exists())

    def test_warranty_from_another_order_is_rejected(self):
        foreign_warranty = self.create_warranty(
            order=self.other_order,
        )

        response = self.create_request(
            warranty=foreign_warranty,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(WarrantyRequest.objects.exists())

    def test_nonexistent_warranty_is_rejected(self):
        response = self.create_request(
            warranty=self.active_warranty,
        )
        self.assertEqual(response.status_code, 201)

        payload = self.request_payload()
        payload["warranty"] = 999999

        response = self.client.post(
            self.list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(WarrantyRequest.objects.count(), 1)

    def test_second_pending_request_requires_reason(self):
        first = self.create_request()

        self.assertEqual(first.status_code, 201)

        second = self.create_request()

        self.assertEqual(
            second.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "concurrent_open_reason",
            second.data,
        )
        self.assertEqual(WarrantyRequest.objects.count(), 1)
        self.assertEqual(WarrantyRequestHistory.objects.count(), 1)

    def test_second_pending_request_is_allowed_with_reason(self):
        first = self.create_request()
        self.assertEqual(first.status_code, 201)

        second = self.create_request(
            concurrent_open_reason=(
                "El cliente reporta un síntoma adicional "
                "y se decide abrir un reclamo separado."
            ),
        )

        self.assertEqual(
            second.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(WarrantyRequest.objects.count(), 2)
        self.assertEqual(WarrantyRequestHistory.objects.count(), 2)

        second_request = WarrantyRequest.objects.get(
            pk=second.data["id"],
        )
        self.assertTrue(
            second_request.concurrent_open_reason,
        )

        second_history = second_request.history.get()
        self.assertEqual(
            second_history.action,
            WarrantyRequestHistory.Action.CREATED,
        )
        self.assertIn(
            "síntoma adicional",
            second_history.observation,
        )

    def test_technician_can_create_request(self):
        self.client.force_authenticate(user=self.technician)

        response = self.create_request()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        warranty_request = WarrantyRequest.objects.get()
        self.assertEqual(
            warranty_request.created_by,
            self.technician,
        )

    def test_helper_cannot_create_or_list_requests(self):
        self.client.force_authenticate(user=self.helper)

        get_response = self.client.get(self.list_url)
        post_response = self.create_request()

        self.assertEqual(
            get_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            post_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertFalse(WarrantyRequest.objects.exists())

    def test_anonymous_user_cannot_access_requests(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_request_detail_and_history_are_available(self):
        created = self.create_request()
        request_id = created.data["id"]

        detail = self.client.get(
            self.detail_url(request_id),
        )
        history = self.client.get(
            self.history_url(request_id),
        )

        self.assertEqual(detail.status_code, 200)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(detail.data["id"], request_id)
        self.assertEqual(len(history.data), 1)
        self.assertEqual(
            history.data[0]["action"],
            WarrantyRequestHistory.Action.CREATED,
        )

    def test_private_evidence_is_available_only_to_authorized_order_users(self):
        created = self.create_request()
        request_id = created.data["id"]
        warranty_request = WarrantyRequest.objects.get(pk=request_id)
        url = self.evidence_url(request_id)

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            warranty_request.evidence.save(
                "prueba.jpg", ContentFile(b"private-photo-bytes"), save=True,
            )

            detail = self.client.get(self.detail_url(request_id))
            listing = self.client.get(self.list_url)
            self.assertTrue(detail.data["evidence"])
            self.assertEqual(detail.data["evidence_download_url"], url)
            self.assertEqual(listing.data[0]["evidence_download_url"], url)
            self.assertNotIn("warranty_requests/", str(detail.data))

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response["Content-Type"], "image/jpeg")
            self.assertEqual(response["Cache-Control"], "private, no-store")
            # El estado y el tipo prueban el acceso; consumir/cerrar el stream
            # en TestCase cierra su conexión PostgreSQL antes del rollback.

            self.client.force_authenticate(user=self.technician)
            self.assertEqual(self.client.get(url).status_code, 200)
            self.assertEqual(
                self.client.get(self.evidence_url(request_id, self.other_order)).status_code,
                status.HTTP_404_NOT_FOUND,
            )

            self.client.force_authenticate(user=self.helper)
            self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)

            self.client.force_authenticate(user=None)
            self.assertEqual(self.client.get(url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_evidence_returns_404_without_exposing_storage_path(self):
        created = self.create_request()
        self.assertFalse(created.data["evidence"])
        self.assertIsNone(created.data["evidence_download_url"])
        self.assertEqual(
            self.client.get(self.evidence_url(created.data["id"])).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    @override_settings(EVIDENCE_MAX_UPLOAD_SIZE=1)
    def test_oversized_evidence_is_rejected_before_saving_request(self):
        image = SimpleUploadedFile(
            "foto.png",
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4"
                "/5+hHgAHggJ/PYFv9QAAAABJRU5ErkJggg=="
            ),
            content_type="image/png",
        )
        response = self.client.post(
            self.list_url,
            self.request_payload(evidence=image),
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("evidence", response.data)
        self.assertFalse(WarrantyRequest.objects.exists())

    def test_requests_can_be_listed_by_warranty(self):
        first = self.create_request()
        self.assertEqual(first.status_code, 201)

        second = self.create_request(
            concurrent_open_reason="Segundo reclamo autorizado.",
        )
        self.assertEqual(second.status_code, 201)

        response = self.client.get(
            self.by_warranty_url(self.active_warranty.pk)
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(
            {
                item["warranty"]
                for item in response.data
            },
            {self.active_warranty.pk},
        )

    def test_order_list_can_be_filtered_by_warranty(self):
        response = self.create_request()
        self.assertEqual(response.status_code, 201)

        response = self.client.get(
            self.list_url,
            {
                "warranty_id": self.active_warranty.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["warranty"],
            self.active_warranty.pk,
        )

    def test_client_snapshot_does_not_change_after_client_edit(self):
        created = self.create_request()
        request_id = created.data["id"]

        self.customer.name = "Nombre modificado"
        self.customer.rut = "11.111.111-1"
        self.customer.save()

        warranty_request = WarrantyRequest.objects.get(
            pk=request_id,
        )

        self.assertEqual(
            warranty_request.client_name_snapshot,
            "Cliente reclamo",
        )
        self.assertEqual(
            warranty_request.client_rut_snapshot,
            "123456785",
        )

        detail = self.client.get(
            self.detail_url(request_id),
        )

        self.assertEqual(
            detail.data["client_name"],
            "Cliente reclamo",
        )
        self.assertEqual(
            detail.data["client_rut"],
            "123456785",
        )

    def test_creating_request_does_not_change_warranty_coverage(self):
        original_starts_on = self.active_warranty.starts_on
        original_ends_on = self.active_warranty.ends_on
        original_conditions = self.active_warranty.conditions

        response = self.create_request()
        self.assertEqual(response.status_code, 201)

        self.active_warranty.refresh_from_db()

        self.assertEqual(
            self.active_warranty.starts_on,
            original_starts_on,
        )
        self.assertEqual(
            self.active_warranty.ends_on,
            original_ends_on,
        )
        self.assertEqual(
            self.active_warranty.conditions,
            original_conditions,
        )
        self.assertEqual(
            self.active_warranty.current_status,
            OrderWarranty.WarrantyStatus.ACTIVE,
        )

    def test_warranty_with_requests_cannot_be_deleted(self):
        created = self.create_request()
        self.assertEqual(created.status_code, 201)

        warranty_delete_url = reverse(
            "order-warranty-detail",
            kwargs={
                "pk": self.order.pk,
                "warranty_id": self.active_warranty.pk,
            },
        )

        response = self.client.delete(warranty_delete_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )
        self.assertTrue(
            OrderWarranty.objects.filter(
                pk=self.active_warranty.pk,
            ).exists()
        )
        self.assertTrue(
            WarrantyRequest.objects.filter(
                pk=created.data["id"],
            ).exists()
        )
        self.assertIn(
            "solicitudes de garantía asociadas",
            response.data["detail"],
        )

    def test_public_tracking_does_not_expose_request_information(self):
        created = self.create_request()
        self.assertEqual(created.status_code, 201)

        self.client.force_authenticate(user=None)

        public_url = reverse(
            "public-order-status",
            kwargs={
                "tracking_code": self.order.tracking_code,
            },
        )

        response = self.client.get(public_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.data.keys()),
            {
                "tracking_code",
                "status",
                "status_display",
                "updated_at",
            },
        )
        self.assertNotIn("client_rut", response.data)
        self.assertNotIn("warranty_requests", response.data)
        self.assertNotIn("problem_description", response.data)
