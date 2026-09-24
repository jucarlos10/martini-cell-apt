from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from .models import ServiceOrder
from .services import STATUS_CATEGORIES, calculate_order_times


class OrderTimeCalculationTests(SimpleTestCase):

    def setUp(self):
        self.start = datetime(
            2026, 9, 1, 9, 0,
            tzinfo=timezone.utc,
        )

    def make_event(self, event_id, previous, current, hours):
        return SimpleNamespace(
            id=event_id,
            from_status=previous,
            to_status=current,
            changed_at=self.start + timedelta(hours=hours),
        )

    def make_order(self, events, current_status):
        history = Mock()
        history.order_by.return_value = events

        return SimpleNamespace(
            id=1,
            tracking_code="MC-TEST",
            status=current_status,
            status_history=history,
        )

    def test_all_states_have_a_category(self):
        self.assertEqual(
            set(STATUS_CATEGORIES),
            set(ServiceOrder.Status.values),
        )

    def test_part_wait_is_not_technical_time(self):
        events = [
            self.make_event(
                1, None, "RECEIVED", 0
            ),
            self.make_event(
                2, "RECEIVED", "DIAGNOSIS", 1
            ),
            self.make_event(
                3, "DIAGNOSIS", "AUTHORIZATION", 2
            ),
            self.make_event(
                4, "AUTHORIZATION", "PART", 3
            ),
            # El repuesto llega después de tres días.
            self.make_event(
                5, "PART", "REPAIR", 75
            ),
            self.make_event(
                6, "REPAIR", "TESTING", 77
            ),
            self.make_event(
                7, "TESTING", "READY", 77.5
            ),
            self.make_event(
                8, "READY", "DELIVERED", 78
            ),
            self.make_event(
                9, "DELIVERED", "CLOSED", 79
            ),
        ]

        order = self.make_order(events, "CLOSED")

        result = calculate_order_times(
            order,
            as_of=self.start + timedelta(hours=200),
        )

        # Diagnóstico: 1 h
        # Reparación: 2 h
        # Pruebas: 0,5 h
        self.assertEqual(
            result["technical_seconds"],
            3.5 * 3600,
        )

        # Recepción: 1 h
        # Autorización: 1 h
        # Repuesto: 72 h
        # Retiro: 0,5 h
        self.assertEqual(
            result["waiting_seconds"],
            74.5 * 3600,
        )

        self.assertEqual(
            result["by_status"]["PART"],
            72 * 3600,
        )

        self.assertEqual(
            result["total_seconds"],
            78 * 3600,
        )

        # Entregado y cerrado no acumulan tiempo.
        self.assertEqual(
            result["by_status"]["DELIVERED"],
            0,
        )
        self.assertEqual(
            result["by_status"]["CLOSED"],
            0,
        )

    def test_current_stage_keeps_accumulating(self):
        events = [
            self.make_event(
                1, None, "RECEIVED", 0
            ),
            self.make_event(
                2, "RECEIVED", "DIAGNOSIS", 1
            ),
        ]

        order = self.make_order(events, "DIAGNOSIS")

        result = calculate_order_times(
            order,
            as_of=self.start + timedelta(hours=3.5),
        )

        self.assertEqual(
            result["waiting_seconds"],
            3600,
        )
        self.assertEqual(
            result["technical_seconds"],
            2.5 * 3600,
        )
        self.assertTrue(
            result["segments"][-1]["is_running"],
        )

    def test_repeated_repair_and_testing_are_accumulated(self):
        events = [
            self.make_event(
                1, None, "RECEIVED", 0
            ),
            self.make_event(
                2, "RECEIVED", "DIAGNOSIS", 1
            ),
            self.make_event(
                3, "DIAGNOSIS", "AUTHORIZATION", 2
            ),
            self.make_event(
                4, "AUTHORIZATION", "REPAIR", 3
            ),
            self.make_event(
                5, "REPAIR", "TESTING", 4
            ),
            self.make_event(
                6, "TESTING", "REPAIR", 5
            ),
            self.make_event(
                7, "REPAIR", "TESTING", 6
            ),
            self.make_event(
                8, "TESTING", "READY", 7
            ),
            self.make_event(
                9, "READY", "DELIVERED", 8
            ),
        ]

        order = self.make_order(events, "DELIVERED")

        result = calculate_order_times(
            order,
            as_of=self.start + timedelta(hours=20),
        )

        self.assertEqual(
            result["by_status"]["REPAIR"],
            2 * 3600,
        )
        self.assertEqual(
            result["by_status"]["TESTING"],
            2 * 3600,
        )
        self.assertEqual(
            result["technical_seconds"],
            5 * 3600,
        )
        self.assertEqual(
            result["waiting_seconds"],
            3 * 3600,
        )

    def test_equal_timestamps_do_not_create_negative_time(self):
        events = [
            self.make_event(
                1, None, "RECEIVED", 0
            ),
            self.make_event(
                2, "RECEIVED", "DIAGNOSIS", 0
            ),
            self.make_event(
                3, "DIAGNOSIS", "AUTHORIZATION", 1
            ),
        ]

        order = self.make_order(events, "AUTHORIZATION")

        result = calculate_order_times(
            order,
            as_of=self.start + timedelta(hours=2),
        )

        self.assertEqual(
            result["by_status"]["RECEIVED"],
            0,
        )
        self.assertEqual(
            result["technical_seconds"],
            3600,
        )
        self.assertEqual(
            result["waiting_seconds"],
            3600,
        )

    def test_missing_history_is_rejected(self):
        order = self.make_order([], "RECEIVED")

        with self.assertRaisesRegex(
            ValueError,
            "no tiene historial",
        ):
            calculate_order_times(order, as_of=self.start)

    def test_missing_initial_record_is_rejected(self):
        events = [
            self.make_event(
                1, "RECEIVED", "DIAGNOSIS", 1
            ),
        ]

        order = self.make_order(events, "DIAGNOSIS")

        with self.assertRaisesRegex(
            ValueError,
            "registro inicial",
        ):
            calculate_order_times(order, as_of=self.start)

    def test_broken_transition_chain_is_rejected(self):
        events = [
            self.make_event(
                1, None, "RECEIVED", 0
            ),
            self.make_event(
                2, "AUTHORIZATION", "DIAGNOSIS", 1
            ),
        ]

        order = self.make_order(events, "DIAGNOSIS")

        with self.assertRaisesRegex(
            ValueError,
            "no coincide con el estado anterior",
        ):
            calculate_order_times(
                order,
                as_of=self.start + timedelta(hours=2),
            )

    def test_reversed_dates_are_rejected(self):
        events = [
            self.make_event(
                1, None, "RECEIVED", 2
            ),
            self.make_event(
                2, "RECEIVED", "DIAGNOSIS", 1
            ),
        ]

        order = self.make_order(events, "DIAGNOSIS")

        with self.assertRaisesRegex(
            ValueError,
            "fechas inconsistentes",
        ):
            calculate_order_times(
                order,
                as_of=self.start + timedelta(hours=3),
            )

    def test_current_status_must_match_history(self):
        events = [
            self.make_event(
                1, None, "RECEIVED", 0
            ),
        ]

        order = self.make_order(events, "REPAIR")

        with self.assertRaisesRegex(
            ValueError,
            "estado actual no coincide",
        ):
            calculate_order_times(
                order,
                as_of=self.start + timedelta(hours=1),
            )