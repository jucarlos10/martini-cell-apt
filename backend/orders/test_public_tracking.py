from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache.backends.locmem import LocMemCache
from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class PublicOrderTrackingTests(SimpleTestCase):

    def setUp(self):
        self.client = APIClient()
        self.code = "MC-4410686A550E"

        self.url = reverse(
            "public-order-status",
            kwargs={"tracking_code": self.code},
        )

        # Simula una orden con información interna.
        # La API pública no debe exponer esos datos.
        self.order = SimpleNamespace(
            tracking_code=self.code,
            status="DIAGNOSIS",
            updated_at=datetime(
                2026, 9, 24, 5, 10, tzinfo=timezone.utc
            ),
            get_status_display=lambda: "Diagnóstico",
            reported_issue="Información privada del problema",
            initial_observations="Observaciones internas",
            client_name="Cliente de prueba",
        )

        # Historial público seguro.
        # Solo contiene estado, nombre visible y fecha.
        self.history = [
            SimpleNamespace(
                to_status="RECEIVED",
                get_to_status_display=lambda: "Ingresado",
                changed_at=datetime(
                    2026, 9, 24, 4, 30, tzinfo=timezone.utc
                ),
            ),
            SimpleNamespace(
                to_status="DIAGNOSIS",
                get_to_status_display=lambda: "Diagnóstico",
                changed_at=datetime(
                    2026, 9, 24, 5, 10, tzinfo=timezone.utc
                ),
            ),
        ]

    def configure_history_mock(self, mock_history_filter):
        mock_history_filter.return_value.order_by.return_value = (
            self.history
        )

    @patch(
        "orders.public_tracking.OrderStatusHistory.objects.filter"
    )
    @patch(
        "orders.public_tracking.ServiceOrder.objects.filter"
    )
    def test_valid_code_works_without_login(
        self,
        mock_order_filter,
        mock_history_filter,
    ):
        mock_order_filter.return_value.first.return_value = self.order
        self.configure_history_mock(mock_history_filter)

        # No enviamos usuario, contraseña ni token.
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["tracking_code"],
            self.code,
        )

        self.assertEqual(
            response.data["status"],
            "DIAGNOSIS",
        )

        self.assertEqual(
            len(response.data["history"]),
            2,
        )

        mock_order_filter.assert_called_once_with(
            tracking_code=self.code
        )

        mock_history_filter.assert_called_once_with(
            order=self.order
        )

        mock_history_filter.return_value.order_by.assert_called_once_with(
            "changed_at",
            "id",
        )

    @patch(
        "orders.public_tracking.OrderStatusHistory.objects.filter"
    )
    @patch(
        "orders.public_tracking.ServiceOrder.objects.filter"
    )
    def test_public_response_contains_only_allowed_fields(
        self,
        mock_order_filter,
        mock_history_filter,
    ):
        mock_order_filter.return_value.first.return_value = self.order
        self.configure_history_mock(mock_history_filter)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            set(response.data.keys()),
            {
                "tracking_code",
                "status",
                "status_display",
                "updated_at",
                "history",
            },
        )

    @patch(
        "orders.public_tracking.OrderStatusHistory.objects.filter"
    )
    @patch(
        "orders.public_tracking.ServiceOrder.objects.filter"
    )
    def test_public_history_contains_only_allowed_fields(
        self,
        mock_order_filter,
        mock_history_filter,
    ):
        mock_order_filter.return_value.first.return_value = self.order
        self.configure_history_mock(mock_history_filter)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            set(response.data["history"][0].keys()),
            {
                "status",
                "status_display",
                "changed_at",
            },
        )

    @patch(
        "orders.public_tracking.OrderStatusHistory.objects.filter"
    )
    @patch(
        "orders.public_tracking.ServiceOrder.objects.filter"
    )
    def test_public_history_returns_expected_states(
        self,
        mock_order_filter,
        mock_history_filter,
    ):
        mock_order_filter.return_value.first.return_value = self.order
        self.configure_history_mock(mock_history_filter)

        response = self.client.get(self.url)

        self.assertEqual(
            response.data["history"][0]["status"],
            "RECEIVED",
        )

        self.assertEqual(
            response.data["history"][0]["status_display"],
            "Ingresado",
        )

        self.assertEqual(
            response.data["history"][1]["status"],
            "DIAGNOSIS",
        )

        self.assertEqual(
            response.data["history"][1]["status_display"],
            "Diagnóstico",
        )

    @patch(
        "orders.public_tracking.OrderStatusHistory.objects.filter"
    )
    @patch(
        "orders.public_tracking.ServiceOrder.objects.filter"
    )
    def test_nonexistent_code_returns_404(
        self,
        mock_order_filter,
        mock_history_filter,
    ):
        mock_order_filter.return_value.first.return_value = None

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(
            response.data["detail"],
            "No se encontró una orden con ese código.",
        )

        mock_history_filter.assert_not_called()

    @patch(
        "orders.public_tracking.OrderStatusHistory.objects.filter"
    )
    @patch(
        "orders.public_tracking.ServiceOrder.objects.filter"
    )
    def test_invalid_format_returns_404_without_database_query(
        self,
        mock_order_filter,
        mock_history_filter,
    ):
        invalid_url = reverse(
            "public-order-status",
            kwargs={"tracking_code": "CODIGO-INCORRECTO"},
        )

        response = self.client.get(invalid_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        mock_order_filter.assert_not_called()
        mock_history_filter.assert_not_called()

    @patch(
        "orders.public_tracking.OrderStatusHistory.objects.filter"
    )
    @patch(
        "orders.public_tracking.ServiceOrder.objects.filter"
    )
    def test_invalid_and_nonexistent_codes_have_same_message(
        self,
        mock_order_filter,
        mock_history_filter,
    ):
        mock_order_filter.return_value.first.return_value = None

        invalid_url = reverse(
            "public-order-status",
            kwargs={"tracking_code": "CODIGO-INCORRECTO"},
        )

        invalid_response = self.client.get(invalid_url)
        nonexistent_response = self.client.get(self.url)

        self.assertEqual(
            invalid_response.status_code,
            nonexistent_response.status_code,
        )

        self.assertEqual(
            invalid_response.data,
            nonexistent_response.data,
        )

        mock_history_filter.assert_not_called()

    def test_post_method_is_not_allowed(self):
        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @patch(
        "orders.public_tracking.OrderStatusHistory.objects.filter"
    )
    @patch(
        "orders.public_tracking.ServiceOrder.objects.filter"
    )
    def test_rate_limit_blocks_21st_request(
        self,
        mock_order_filter,
        mock_history_filter,
    ):
        mock_order_filter.return_value.first.return_value = self.order
        self.configure_history_mock(mock_history_filter)

        # Caché independiente para que otras pruebas no
        # alteren el contador de solicitudes.
        isolated_cache = LocMemCache(
            "hu12-throttle-test",
            {},
        )

        with patch(
            "orders.public_tracking.PublicTrackingThrottle.cache",
            isolated_cache,
        ):
            # Las primeras 20 solicitudes deben funcionar.
            for _ in range(20):
                response = self.client.get(self.url)

                self.assertEqual(
                    response.status_code,
                    status.HTTP_200_OK,
                )

            # La solicitud número 21 debe ser bloqueada.
            blocked_response = self.client.get(self.url)

        self.assertEqual(
            blocked_response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

        # La solicitud bloqueada no debe consultar la orden
        # ni el historial.
        self.assertEqual(
            mock_order_filter.call_count,
            20,
        )

        self.assertEqual(
            mock_history_filter.call_count,
            20,
        )