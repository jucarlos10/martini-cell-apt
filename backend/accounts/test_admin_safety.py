from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import User


class UserAdminSafetyTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_hu02",
            password="ClaveExclusivaDePruebas2026!",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tecnico_hu02",
            password="ClaveExclusivaDePruebas2026!",
            role=User.Role.TECH,
        )

        self.client.force_authenticate(user=self.admin)

    def user_url(self, user):
        return reverse(
            "user-detail",
            kwargs={"pk": user.pk},
        )

    def test_admin_cannot_deactivate_own_account(self):
        response = self.client.patch(
            self.user_url(self.admin),
            {"is_active": False},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_cannot_change_role_of_last_active_admin(self):
        response = self.client.patch(
            self.user_url(self.admin),
            {"role": User.Role.TECH},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, User.Role.ADMIN)

    def test_can_change_role_when_another_admin_remains(self):
        second_admin = User.objects.create_user(
            username="segundo_admin_hu02",
            password="ClaveExclusivaDePruebas2026!",
            role=User.Role.ADMIN,
        )

        response = self.client.patch(
            self.user_url(second_admin),
            {"role": User.Role.TECH},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        second_admin.refresh_from_db()
        self.assertEqual(second_admin.role, User.Role.TECH)

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertEqual(self.admin.role, User.Role.ADMIN)

    def test_deactivated_user_cannot_login(self):
        response = self.client.patch(
            self.user_url(self.technician),
            {"is_active": False},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.technician.refresh_from_db()
        self.assertFalse(self.technician.is_active)

        # La cuenta permanece registrada para conservar
        # su relación con el historial del sistema.
        self.assertTrue(
            User.objects.filter(pk=self.technician.pk).exists()
        )

        anonymous_client = APIClient()

        login_response = anonymous_client.post(
            reverse("login"),
            {
                "username": "tecnico_hu02",
                "password": "ClaveExclusivaDePruebas2026!",
            },
            format="json",
        )

        self.assertEqual(
            login_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_technician_cannot_modify_users(self):
        self.client.force_authenticate(user=self.technician)

        response = self.client.patch(
            self.user_url(self.admin),
            {"role": User.Role.TECH},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, User.Role.ADMIN)