from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from customers.models import Client
from devices.models import Equipment
from orders.models import OrderTechnicalReport, ServiceOrder

from .models import User


class UserLifecycleTests(APITestCase):

    def setUp(self):
        self.password = "ClaveExclusivaDePruebas2026!"

        self.admin = User.objects.create_user(
            username="admin_ciclo",
            password=self.password,
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tecnico_ciclo",
            password=self.password,
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="ayudante_ciclo",
            password=self.password,
            role=User.Role.HELPER,
        )

        self.client.force_authenticate(user=self.admin)

    def user_url(self, user):
        return reverse(
            "user-detail",
            kwargs={"pk": user.pk},
        )

    def test_new_user_is_not_archived(self):
        self.assertFalse(self.technician.is_archived)

        response = self.client.get(self.user_url(self.technician))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIs(response.data["is_archived"], False)

    def test_admin_can_archive_user_and_account_becomes_inactive(self):
        response = self.client.patch(
            self.user_url(self.technician),
            {"is_archived": True},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.technician.refresh_from_db()

        self.assertTrue(self.technician.is_archived)
        self.assertFalse(self.technician.is_active)

    def test_archived_user_cannot_login(self):
        response = self.client.patch(
            self.user_url(self.technician),
            {"is_archived": True},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        anonymous_client = APIClient()

        login_response = anonymous_client.post(
            reverse("login"),
            {
                "username": self.technician.username,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(
            login_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_restoring_user_keeps_account_inactive(self):
        self.technician.is_archived = True
        self.technician.is_active = False
        self.technician.save(
            update_fields=["is_archived", "is_active"]
        )

        response = self.client.patch(
            self.user_url(self.technician),
            {"is_archived": False},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.technician.refresh_from_db()

        self.assertFalse(self.technician.is_archived)
        self.assertFalse(self.technician.is_active)

    def test_restored_user_can_be_activated_separately(self):
        self.technician.is_archived = True
        self.technician.is_active = False
        self.technician.save(
            update_fields=["is_archived", "is_active"]
        )

        restore_response = self.client.patch(
            self.user_url(self.technician),
            {"is_archived": False},
            format="json",
        )

        self.assertEqual(
            restore_response.status_code,
            status.HTTP_200_OK,
        )

        activate_response = self.client.patch(
            self.user_url(self.technician),
            {"is_active": True},
            format="json",
        )

        self.assertEqual(
            activate_response.status_code,
            status.HTTP_200_OK,
        )

        self.technician.refresh_from_db()

        self.assertFalse(self.technician.is_archived)
        self.assertTrue(self.technician.is_active)

    def test_archived_user_cannot_be_activated(self):
        self.technician.is_archived = True
        self.technician.is_active = False
        self.technician.save(
            update_fields=["is_archived", "is_active"]
        )

        response = self.client.patch(
            self.user_url(self.technician),
            {"is_active": True},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.technician.refresh_from_db()

        self.assertTrue(self.technician.is_archived)
        self.assertFalse(self.technician.is_active)

    def test_cannot_archive_and_activate_in_same_request(self):
        response = self.client.patch(
            self.user_url(self.technician),
            {
                "is_archived": True,
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.technician.refresh_from_db()

        self.assertFalse(self.technician.is_archived)
        self.assertTrue(self.technician.is_active)

    def test_cannot_restore_and_activate_in_same_request(self):
        self.technician.is_archived = True
        self.technician.is_active = False
        self.technician.save(
            update_fields=["is_archived", "is_active"]
        )

        response = self.client.patch(
            self.user_url(self.technician),
            {
                "is_archived": False,
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.technician.refresh_from_db()

        self.assertTrue(self.technician.is_archived)
        self.assertFalse(self.technician.is_active)

    def test_admin_cannot_archive_own_account(self):
        response = self.client.patch(
            self.user_url(self.admin),
            {"is_archived": True},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.admin.refresh_from_db()

        self.assertFalse(self.admin.is_archived)
        self.assertTrue(self.admin.is_active)

    def test_admin_can_delete_user_without_related_records(self):
        user_id = self.helper.pk

        response = self.client.delete(
            self.user_url(self.helper)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            User.objects.filter(pk=user_id).exists()
        )

    def test_anonymous_user_cannot_delete_account(self):
        self.client.force_authenticate(user=None)

        response = self.client.delete(
            self.user_url(self.helper)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertTrue(
            User.objects.filter(pk=self.helper.pk).exists()
        )

    def test_technician_cannot_delete_account(self):
        self.client.force_authenticate(user=self.technician)

        response = self.client.delete(
            self.user_url(self.helper)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertTrue(
            User.objects.filter(pk=self.helper.pk).exists()
        )

    def test_helper_cannot_delete_account(self):
        self.client.force_authenticate(user=self.helper)

        response = self.client.delete(
            self.user_url(self.technician)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertTrue(
            User.objects.filter(pk=self.technician.pk).exists()
        )

    def test_admin_cannot_delete_own_account(self):
        response = self.client.delete(
            self.user_url(self.admin)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertTrue(
            User.objects.filter(pk=self.admin.pk).exists()
        )

    def test_cannot_delete_last_active_admin(self):
        # Se fuerza la autenticación de un segundo administrador
        # inactivo para verificar directamente esta protección.
        second_admin = User.objects.create_user(
            username="admin_inactivo_ciclo",
            password=self.password,
            role=User.Role.ADMIN,
            is_active=False,
        )

        self.client.force_authenticate(user=second_admin)

        response = self.client.delete(
            self.user_url(self.admin)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertTrue(
            User.objects.filter(pk=self.admin.pk).exists()
        )

    def test_nullable_historical_relation_blocks_deletion(self):
        # created_by usa SET_NULL, pero igualmente debemos
        # conservar quién registró al cliente.
        customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente de prueba del ciclo de usuarios",
            phone="912345678",
            created_by=self.technician,
        )

        response = self.client.delete(
            self.user_url(self.technician)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertTrue(
            User.objects.filter(pk=self.technician.pk).exists()
        )

        customer.refresh_from_db()

        self.assertEqual(
            customer.created_by_id,
            self.technician.pk,
        )

    def test_protected_technical_report_blocks_deletion(self):
        customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente para informe de prueba",
            phone="912345678",
        )

        equipment = Equipment.objects.create(
            client=customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Marca de prueba",
            model="Modelo de prueba",
        )

        order = ServiceOrder.objects.create(
            client=customer,
            equipment=equipment,
            reported_issue="Falla de prueba",
        )

        report = OrderTechnicalReport.objects.create(
            order=order,
            diagnosis="Diagnóstico de prueba",
            repair_actions="Acciones de prueba",
            result=OrderTechnicalReport.Result.REPARADO,
            technician=self.technician,
            created_by=self.admin,
            updated_by=self.admin,
        )

        response = self.client.delete(
            self.user_url(self.technician)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertTrue(
            User.objects.filter(pk=self.technician.pk).exists()
        )

        report.refresh_from_db()

        self.assertEqual(
            report.technician_id,
            self.technician.pk,
        )

    def test_user_with_historical_records_can_be_archived(self):
        customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente con historial conservado",
            phone="912345678",
            created_by=self.technician,
        )

        response = self.client.patch(
            self.user_url(self.technician),
            {"is_archived": True},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.technician.refresh_from_db()
        customer.refresh_from_db()

        self.assertTrue(self.technician.is_archived)
        self.assertFalse(self.technician.is_active)

        self.assertEqual(
            customer.created_by_id,
            self.technician.pk,
        )