"""Recorrido real de API con datos ficticios, sin enviar correos externos."""

from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment

from .models import ServiceOrder


class OrderTraceabilityJourneyTests(APITestCase):
    def test_order_lifecycle_keeps_internal_history_and_safe_public_tracking(self):
        admin = User.objects.create_user(
            username="administrador_recorrido",
            role=User.Role.ADMIN,
        )
        technician = User.objects.create_user(
            username="tecnico_recorrido",
            role=User.Role.TECH,
        )
        customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente de ensayo",
            phone="912345678",
            email="ensayo@example.com",
            created_by=admin,
        )
        equipment = Equipment.objects.create(
            client=customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Equipo",
            model="de ensayo",
            created_by=admin,
        )

        self.client.force_authenticate(user=admin)
        created = self.client.post(
            reverse("service-order-list-create"),
            {
                "client": customer.pk,
                "equipment": equipment.pk,
                "reported_issue": "Falla interna de ensayo",
                "initial_observations": "Observación privada de ensayo",
                "preferred_notification_channel": "EMAIL",
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        order_id = created.data["id"]
        code = created.data["tracking_code"]
        status_url = reverse("order-status", kwargs={"pk": order_id})
        history_url = reverse("order-status-history", kwargs={"pk": order_id})
        public_url = reverse(
            "public-order-status", kwargs={"tracking_code": code}
        )
        public_client = APIClient()

        initial = public_client.get(public_url)
        self.assertEqual(initial.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [entry["status"] for entry in initial.data["history"]],
            [ServiceOrder.Status.RECEIVED],
        )

        self.client.force_authenticate(user=technician)
        stages = [
            ServiceOrder.Status.DIAGNOSIS,
            ServiceOrder.Status.AUTHORIZATION,
            ServiceOrder.Status.REPAIR,
            ServiceOrder.Status.TESTING,
            ServiceOrder.Status.READY,
            ServiceOrder.Status.DELIVERED,
            ServiceOrder.Status.CLOSED,
        ]

        with patch("orders.views.send_email", return_value={"id": "ensayo-001"}) as send:
            for next_status in stages:
                with self.subTest(stage=next_status):
                    response = self.client.patch(
                        status_url,
                        {
                            "status": next_status,
                            "note": "Nota interna de ensayo",
                        },
                        format="json",
                    )
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                    self.assertEqual(response.data["status"], next_status)
                    self.assertEqual(
                        response.data["notification_result"]["status"],
                        "SENT",
                    )
            self.assertEqual(send.call_count, len(stages))

        internal = self.client.get(history_url)
        self.assertEqual(internal.status_code, status.HTTP_200_OK)
        expected = [ServiceOrder.Status.RECEIVED, *stages]
        self.assertEqual(
            [entry["to_status"] for entry in internal.data], expected
        )
        self.assertEqual(
            [entry["from_status"] for entry in internal.data],
            [None, *expected[:-1]],
        )
        self.assertEqual(internal.data[0]["changed_by_username"], admin.username)
        for entry in internal.data[1:]:
            self.assertEqual(entry["changed_by_username"], technician.username)
            self.assertEqual(entry["note"], "Nota interna de ensayo")
            self.assertEqual(entry["notifications"][0]["status"], "SENT")

        public = public_client.get(public_url)
        self.assertEqual(public.status_code, status.HTTP_200_OK)
        self.assertEqual(public.data["status"], ServiceOrder.Status.CLOSED)
        self.assertEqual(
            [entry["status"] for entry in public.data["history"]], expected
        )
        self.assertEqual(
            set(public.data),
            {"tracking_code", "status", "status_display", "updated_at", "history"},
        )
        for entry in public.data["history"]:
            self.assertEqual(
                set(entry), {"status", "status_display", "changed_at"}
            )
        self.assertNotIn("Nota interna de ensayo", str(public.data))
        self.assertNotIn(customer.email, str(public.data))

        rejected = self.client.patch(
            status_url,
            {"status": ServiceOrder.Status.DIAGNOSIS},
            format="json",
        )
        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            ServiceOrder.objects.get(pk=order_id).status_history.count(),
            len(expected),
        )
