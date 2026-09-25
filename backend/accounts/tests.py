from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User


class AuthenticationAndUserTests(APITestCase):

    def setUp(self):
        self.password = "ClaveExclusivaDePruebas2026!"

        self.admin = User.objects.create_user(
            username="admin_tec01",
            password=self.password,
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tecnico_tec01",
            password=self.password,
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="ayudante_tec01",
            password=self.password,
            role=User.Role.HELPER,
        )

        self.login_url = reverse("login")
        self.refresh_url = reverse("token_refresh")
        self.me_url = reverse("me")
        self.users_url = reverse("user-list-create")

    def login_as(self, user):
        response = self.client.post(
            self.login_url,
            {
                "username": user.username,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        access_token = response.data["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        return response.data

    def test_valid_login_returns_access_and_refresh_tokens(self):
        response = self.client.post(
            self.login_url,
            {
                "username": self.technician.username,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        self.assertTrue(response.data["access"])
        self.assertTrue(response.data["refresh"])

    def test_wrong_password_is_rejected(self):
        response = self.client.post(
            self.login_url,
            {
                "username": self.technician.username,
                "password": "ClaveIncorrecta2026!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)

    def test_inactive_user_cannot_login(self):
        self.technician.is_active = False
        self.technician.save(update_fields=["is_active"])

        response = self.client.post(
            self.login_url,
            {
                "username": self.technician.username,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_me_requires_authentication(self):
        response = self.client.get(self.me_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_me_returns_authenticated_user_without_password(self):
        self.login_as(self.technician)

        response = self.client.get(self.me_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["id"],
            self.technician.id,
        )

        self.assertEqual(
            response.data["username"],
            self.technician.username,
        )

        self.assertEqual(
            response.data["role"],
            User.Role.TECH,
        )

        self.assertNotIn("password", response.data)

    def test_invalid_access_token_is_rejected(self):
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer token_invalido"
        )

        response = self.client.get(self.me_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_refresh_token_cannot_replace_access_token(self):
        tokens = self.login_as(self.technician)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {tokens['refresh']}"
        )

        response = self.client.get(self.me_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_valid_refresh_token_generates_new_access_token(self):
        tokens = self.login_as(self.technician)

        response = self.client.post(
            self.refresh_url,
            {
                "refresh": tokens["refresh"],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn("access", response.data)
        self.assertTrue(response.data["access"])

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {response.data['access']}"
            )
        )

        me_response = self.client.get(self.me_url)

        self.assertEqual(
            me_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            me_response.data["id"],
            self.technician.id,
        )

    def test_invalid_refresh_token_is_rejected(self):
        response = self.client.post(
            self.refresh_url,
            {
                "refresh": "refresh_invalido",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertNotIn("access", response.data)

    def test_anonymous_user_cannot_list_users(self):
        response = self.client.get(self.users_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_admin_can_list_users(self):
        self.login_as(self.admin)

        response = self.client.get(self.users_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 3)

        usernames = {
            item["username"]
            for item in response.data
        }

        self.assertEqual(
            usernames,
            {
                self.admin.username,
                self.technician.username,
                self.helper.username,
            },
        )

    def test_technician_cannot_list_users(self):
        self.login_as(self.technician)

        response = self.client.get(self.users_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_helper_cannot_create_users(self):
        self.login_as(self.helper)

        response = self.client.post(
            self.users_url,
            {
                "username": "usuario_no_autorizado",
                "password": "ClaveNuevaDePruebas2026!",
                "role": User.Role.TECH,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertFalse(
            User.objects.filter(
                username="usuario_no_autorizado"
            ).exists()
        )

    def test_admin_can_create_user_with_hashed_password(self):
        self.login_as(self.admin)

        new_password = "ClaveNuevaDePruebas2026!"

        response = self.client.post(
            self.users_url,
            {
                "username": "nuevo_tecnico_tec01",
                "email": "tecnico@example.com",
                "password": new_password,
                "role": User.Role.TECH,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        created_user = User.objects.get(
            username="nuevo_tecnico_tec01"
        )

        self.assertEqual(
            created_user.role,
            User.Role.TECH,
        )

        self.assertTrue(
            created_user.check_password(new_password)
        )

        self.assertNotEqual(
            created_user.password,
            new_password,
        )

        self.assertNotIn(
            "password",
            response.data,
        )

    def test_admin_can_update_another_user(self):
        self.login_as(self.admin)

        response = self.client.patch(
            reverse(
                "user-detail",
                kwargs={"pk": self.technician.pk},
            ),
            {
                "role": User.Role.HELPER,
                "email": "actualizado@example.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.technician.refresh_from_db()

        self.assertEqual(
            self.technician.role,
            User.Role.HELPER,
        )

        self.assertEqual(
            self.technician.email,
            "actualizado@example.com",
        )