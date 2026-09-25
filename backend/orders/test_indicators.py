from datetime import datetime, timezone
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment

from .models import OrderStatusHistory, ServiceOrder


class OperationalIndicatorsTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_indicators",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tech_indicators",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="helper_indicators",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente indicadores",
            phone="912345678",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model="Equipo indicadores",
            created_by=self.admin,
        )

        self.url = reverse(
            "operational-indicators"
        )

        self.client.force_authenticate(
            user=self.admin
        )

    def create_order(self):
        response = self.client.post(
            reverse("service-order-list-create"),
            {
                "client": self.customer.id,
                "equipment": self.equipment.id,
                "reported_issue": (
                    "Falla para prueba de indicadores."
                ),
                "initial_observations": (
                    "Orden creada para HU-16."
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

    def set_received_at(self, order, value):
        ServiceOrder.objects.filter(
            pk=order.pk
        ).update(
            received_at=value
        )

        order.refresh_from_db()

    def change_status(self, order, new_status):
        response = self.client.patch(
            reverse(
                "order-status",
                kwargs={"pk": order.pk},
            ),
            {
                "status": new_status,
                "note": "Transición para prueba HU-16.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        order.refresh_from_db()

    def test_anonymous_user_cannot_access_indicators(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.url,
            {
                "start": "2026-09-01",
                "end": "2026-09-30",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_helper_cannot_access_indicators(self):
        self.client.force_authenticate(
            user=self.helper
        )

        response = self.client.get(
            self.url,
            {
                "start": "2026-09-01",
                "end": "2026-09-30",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_technician_can_access_indicators(self):
        self.client.force_authenticate(
            user=self.technician
        )

        response = self.client.get(
            self.url,
            {
                "start": "2026-09-01",
                "end": "2026-09-30",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_dates_are_required(self):
        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_invalid_date_format_is_rejected(self):
        response = self.client.get(
            self.url,
            {
                "start": "01-09-2026",
                "end": "30-09-2026",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_start_date_cannot_be_after_end_date(self):
        response = self.client.get(
            self.url,
            {
                "start": "2026-09-30",
                "end": "2026-09-01",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    @patch(
        "orders.indicator_services.calculate_order_times"
    )
    def test_period_filters_orders_and_counts_statuses(
        self,
        mocked_times,
    ):
        mocked_times.return_value = {
            "technical_seconds": 3600,
            "waiting_seconds": 1800,
            "total_seconds": 5400,
        }

        september_received = self.create_order()

        self.set_received_at(
            september_received,
            datetime(
                2026,
                9,
                5,
                10,
                0,
                tzinfo=timezone.utc,
            ),
        )

        september_closed = self.create_order()

        self.set_received_at(
            september_closed,
            datetime(
                2026,
                9,
                10,
                10,
                0,
                tzinfo=timezone.utc,
            ),
        )

        ServiceOrder.objects.filter(
            pk=september_closed.pk
        ).update(
            status=ServiceOrder.Status.CLOSED
        )

        august_order = self.create_order()

        self.set_received_at(
            august_order,
            datetime(
                2026,
                8,
                31,
                10,
                0,
                tzinfo=timezone.utc,
            ),
        )

        response = self.client.get(
            self.url,
            {
                "start": "2026-09-01",
                "end": "2026-09-30",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["period"],
            {
                "start": "2026-09-01",
                "end": "2026-09-30",
            },
        )

        self.assertEqual(
            response.data["orders_received"],
            2,
        )

        self.assertEqual(
            response.data["orders_finalized"],
            1,
        )

        status_counts = {
            item["status"]: item["count"]
            for item in response.data["orders_by_status"]
        }

        self.assertEqual(
            status_counts[
                ServiceOrder.Status.RECEIVED
            ],
            1,
        )

        self.assertEqual(
            status_counts[
                ServiceOrder.Status.CLOSED
            ],
            1,
        )

        self.assertEqual(
            mocked_times.call_count,
            2,
        )

    @patch(
        "orders.indicator_services.calculate_order_times"
    )
    def test_invalid_history_is_excluded_from_time_averages(
        self,
        mocked_times,
    ):
        first_order = self.create_order()
        second_order = self.create_order()

        self.set_received_at(
            first_order,
            datetime(
                2026,
                9,
                5,
                9,
                0,
                tzinfo=timezone.utc,
            ),
        )

        self.set_received_at(
            second_order,
            datetime(
                2026,
                9,
                6,
                9,
                0,
                tzinfo=timezone.utc,
            ),
        )

        mocked_times.side_effect = [
            {
                "technical_seconds": 3600,
                "waiting_seconds": 7200,
                "total_seconds": 10800,
            },
            ValueError(
                "Historial inconsistente."
            ),
        ]

        response = self.client.get(
            self.url,
            {
                "start": "2026-09-01",
                "end": "2026-09-30",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["orders_with_time_data"],
            1,
        )

        self.assertEqual(
            response.data["orders_without_time_data"],
            1,
        )

        self.assertEqual(
            response.data["average_technical_seconds"],
            3600,
        )

        self.assertEqual(
            response.data["average_waiting_seconds"],
            7200,
        )

        self.assertEqual(
            response.data["average_total_seconds"],
            10800,
        )

        self.assertEqual(
            response.data["average_technical_display"],
            "1 h",
        )

        self.assertEqual(
            response.data["average_waiting_display"],
            "2 h",
        )

        self.assertEqual(
            response.data["average_total_display"],
            "3 h",
        )

    def test_real_order_history_calculates_operational_times(self):
        order = self.create_order()

        start_at = datetime(
            2026,
            9,
            10,
            9,
            0,
            tzinfo=timezone.utc,
        )

        self.set_received_at(
            order,
            start_at,
        )

        self.change_status(
            order,
            ServiceOrder.Status.DIAGNOSIS,
        )

        self.change_status(
            order,
            ServiceOrder.Status.AUTHORIZATION,
        )

        self.change_status(
            order,
            ServiceOrder.Status.REPAIR,
        )

        self.change_status(
            order,
            ServiceOrder.Status.TESTING,
        )

        self.change_status(
            order,
            ServiceOrder.Status.READY,
        )

        self.change_status(
            order,
            ServiceOrder.Status.DELIVERED,
        )

        history = list(
            OrderStatusHistory.objects
            .filter(order=order)
            .order_by("changed_at", "id")
        )

        hours = [
            0,
            1,
            3,
            4,
            7,
            8,
            9,
        ]

        for event, hour in zip(
            history,
            hours,
        ):
            OrderStatusHistory.objects.filter(
                pk=event.pk
            ).update(
                changed_at=datetime(
                    2026,
                    9,
                    10,
                    9 + hour,
                    0,
                    tzinfo=timezone.utc,
                )
            )

        response = self.client.get(
            self.url,
            {
                "start": "2026-09-10",
                "end": "2026-09-10",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["orders_received"],
            1,
        )

        self.assertEqual(
            response.data["orders_finalized"],
            1,
        )

        self.assertEqual(
            response.data["average_technical_seconds"],
            21600,
        )

        self.assertEqual(
            response.data["average_waiting_seconds"],
            10800,
        )

        self.assertEqual(
            response.data["average_total_seconds"],
            32400,
        )

        self.assertEqual(
            response.data["average_technical_display"],
            "6 h",
        )

        self.assertEqual(
            response.data["average_waiting_display"],
            "3 h",
        )

        self.assertEqual(
            response.data["average_total_display"],
            "9 h",
        )