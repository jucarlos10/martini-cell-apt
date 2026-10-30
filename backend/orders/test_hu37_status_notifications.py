from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment

from .models import (
    OrderStatusHistory,
    OrderStatusNotification,
    ServiceOrder,
)


class OrderStatusNotificationTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_hu37",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tecnico_hu37",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="ayudante_hu37",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente HU37",
            phone="912345678",
            email="cliente.hu37@example.com",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model="Galaxy HU37",
            imei="123456789012345",
            color="Negro",
            observations="Dato interno del equipo HU37.",
            created_by=self.admin,
        )

        self.client.force_authenticate(user=self.admin)

    def create_order(self):
        response = self.client.post(
            reverse("service-order-list-create"),
            {
                "client": self.customer.pk,
                "equipment": self.equipment.pk,
                "reported_issue": "Equipo no enciende.",
                "initial_observations": (
                    "Observación interna que no debe notificarse."
                ),
                "received_accessories": "Cargador.",
                "deposit_amount": "25000.00",
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

    def status_url(self, order):
        return reverse(
            "order-status",
            kwargs={"pk": order.pk},
        )

    def history_url(self, order):
        return reverse(
            "order-status-history",
            kwargs={"pk": order.pk},
        )

    def set_preferred_channel(self, order, channel):
        order.preferred_notification_channel = channel
        order.save(
            update_fields=[
                "preferred_notification_channel",
                "updated_at",
            ]
        )

    def change_to_diagnosis(
        self,
        order,
        *,
        note="Inicio de diagnóstico interno.",
    ):
        return self.client.patch(
            self.status_url(order),
            {
                "status": ServiceOrder.Status.DIAGNOSIS,
                "note": note,
            },
            format="json",
        )

    def test_initial_received_history_does_not_create_notification(self):
        order = self.create_order()

        history = OrderStatusHistory.objects.get(
            order=order,
            from_status__isnull=True,
        )

        self.assertEqual(
            history.to_status,
            ServiceOrder.Status.RECEIVED,
        )
        self.assertEqual(
            OrderStatusNotification.objects.count(),
            0,
        )

    @patch(
        "orders.views.EmailMessage.send",
        return_value=1,
    )
    def test_email_status_change_creates_sent_notification(
        self,
        mocked_send,
    ):
        order = self.create_order()
        self.set_preferred_channel(
            order,
            ServiceOrder.NotificationChannel.EMAIL,
        )

        response = self.change_to_diagnosis(order)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            ServiceOrder.Status.DIAGNOSIS,
        )

        history = order.status_history.get(
            from_status=ServiceOrder.Status.RECEIVED,
            to_status=ServiceOrder.Status.DIAGNOSIS,
        )

        notification = OrderStatusNotification.objects.get(
            status_history=history,
        )

        self.assertEqual(
            notification.order,
            order,
        )
        self.assertEqual(
            notification.channel,
            ServiceOrder.NotificationChannel.EMAIL,
        )
        self.assertEqual(
            notification.status,
            OrderStatusNotification.Status.SENT,
        )
        self.assertEqual(
            notification.destination,
            self.customer.email,
        )
        self.assertEqual(
            notification.triggered_by,
            self.admin,
        )

        self.assertEqual(
            response.data["notification_result"]["status"],
            OrderStatusNotification.Status.SENT,
        )

        mocked_send.assert_called_once_with(
            using="default"
        )

    @patch(
        "orders.views.EmailMessage.send",
        side_effect=RuntimeError("SMTP no disponible"),
    )
    def test_email_failure_keeps_status_and_history(
        self,
        mocked_send,
    ):
        order = self.create_order()
        self.set_preferred_channel(
            order,
            ServiceOrder.NotificationChannel.EMAIL,
        )

        response = self.change_to_diagnosis(
            order,
            note="Cambio que debe persistir.",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            ServiceOrder.Status.DIAGNOSIS,
        )

        history = order.status_history.get(
            from_status=ServiceOrder.Status.RECEIVED,
            to_status=ServiceOrder.Status.DIAGNOSIS,
        )

        self.assertEqual(
            history.note,
            "Cambio que debe persistir.",
        )

        notification = OrderStatusNotification.objects.get(
            status_history=history,
        )

        self.assertEqual(
            notification.status,
            OrderStatusNotification.Status.FAILED,
        )
        self.assertIn(
            "SMTP no disponible",
            notification.detail,
        )

        mocked_send.assert_called_once_with(
            using="default"
        )

    def test_whatsapp_status_change_is_prepared(self):
        order = self.create_order()
        self.set_preferred_channel(
            order,
            ServiceOrder.NotificationChannel.WHATSAPP,
        )

        response = self.change_to_diagnosis(order)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        history = order.status_history.get(
            from_status=ServiceOrder.Status.RECEIVED,
            to_status=ServiceOrder.Status.DIAGNOSIS,
        )

        notification = OrderStatusNotification.objects.get(
            status_history=history,
        )

        self.assertEqual(
            notification.status,
            OrderStatusNotification.Status.PREPARED,
        )
        self.assertEqual(
            notification.destination,
            "56912345678",
        )
        self.assertIn(
            order.tracking_code,
            notification.prepared_message,
        )
        self.assertIn(
            "Diagnóstico",
            notification.prepared_message,
        )
        self.assertIn(
            "https://wa.me/56912345678",
            notification.action_url,
        )

        self.assertEqual(
            response.data["notification_result"]["status"],
            OrderStatusNotification.Status.PREPARED,
        )
        self.assertEqual(
            response.data["notification_result"]["action_url"],
            notification.action_url,
        )

    def test_email_without_destination_records_failed_notification(self):
        order = self.create_order()
        self.set_preferred_channel(
            order,
            ServiceOrder.NotificationChannel.EMAIL,
        )

        Client.objects.filter(
            pk=self.customer.pk
        ).update(email="")

        response = self.change_to_diagnosis(order)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        order.refresh_from_db()
        self.assertEqual(
            order.status,
            ServiceOrder.Status.DIAGNOSIS,
        )

        notification = OrderStatusNotification.objects.get(
            order=order,
        )

        self.assertEqual(
            notification.status,
            OrderStatusNotification.Status.FAILED,
        )
        self.assertEqual(
            notification.destination,
            "",
        )
        self.assertIn(
            "correo electrónico",
            notification.detail,
        )

    def test_whatsapp_without_destination_records_failed_notification(self):
        order = self.create_order()
        self.set_preferred_channel(
            order,
            ServiceOrder.NotificationChannel.WHATSAPP,
        )

        Client.objects.filter(
            pk=self.customer.pk
        ).update(phone="")

        response = self.change_to_diagnosis(order)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        order.refresh_from_db()
        self.assertEqual(
            order.status,
            ServiceOrder.Status.DIAGNOSIS,
        )

        notification = OrderStatusNotification.objects.get(
            order=order,
        )

        self.assertEqual(
            notification.status,
            OrderStatusNotification.Status.FAILED,
        )
        self.assertEqual(
            notification.destination,
            "",
        )
        self.assertIn(
            "teléfono",
            notification.detail,
        )

    def test_status_change_without_preferred_channel_keeps_change(self):
        order = self.create_order()

        self.assertEqual(
            order.preferred_notification_channel,
            "",
        )

        response = self.change_to_diagnosis(order)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["notification_result"]["status"],
            "FAILED",
        )
        self.assertIn(
            "canal preferido",
            response.data["notification_result"]["detail"],
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            ServiceOrder.Status.DIAGNOSIS,
        )
        self.assertEqual(
            order.status_history.count(),
            2,
        )
        self.assertEqual(
            OrderStatusNotification.objects.count(),
            0,
        )

    def test_invalid_transition_does_not_create_notification(self):
        order = self.create_order()
        self.set_preferred_channel(
            order,
            ServiceOrder.NotificationChannel.WHATSAPP,
        )

        response = self.client.patch(
            self.status_url(order),
            {
                "status": ServiceOrder.Status.READY,
                "note": "Intento inválido.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            ServiceOrder.Status.RECEIVED,
        )
        self.assertEqual(
            order.status_history.count(),
            1,
        )
        self.assertEqual(
            OrderStatusNotification.objects.count(),
            0,
        )

    def test_helper_cannot_change_status_or_trigger_notification(self):
        order = self.create_order()
        self.set_preferred_channel(
            order,
            ServiceOrder.NotificationChannel.WHATSAPP,
        )

        self.client.force_authenticate(user=self.helper)

        response = self.change_to_diagnosis(order)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            ServiceOrder.Status.RECEIVED,
        )
        self.assertEqual(
            OrderStatusNotification.objects.count(),
            0,
        )

    def test_technician_can_trigger_status_notification(self):
        order = self.create_order()
        self.set_preferred_channel(
            order,
            ServiceOrder.NotificationChannel.WHATSAPP,
        )

        self.client.force_authenticate(
            user=self.technician
        )

        response = self.change_to_diagnosis(order)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        notification = OrderStatusNotification.objects.get(
            order=order,
        )

        self.assertEqual(
            notification.triggered_by,
            self.technician,
        )

    def test_duplicate_notification_for_same_history_and_channel_is_rejected(self):
        order = self.create_order()

        history = OrderStatusHistory.objects.create(
            order=order,
            from_status=ServiceOrder.Status.RECEIVED,
            to_status=ServiceOrder.Status.DIAGNOSIS,
            changed_by=self.admin,
        )

        OrderStatusNotification.objects.create(
            order=order,
            status_history=history,
            channel=ServiceOrder.NotificationChannel.EMAIL,
            status=OrderStatusNotification.Status.SENT,
            destination=self.customer.email,
            triggered_by=self.admin,
        )

        with self.assertRaises(ValidationError):
            OrderStatusNotification.objects.create(
                order=order,
                status_history=history,
                channel=ServiceOrder.NotificationChannel.EMAIL,
                status=OrderStatusNotification.Status.SENT,
                destination=self.customer.email,
                triggered_by=self.admin,
            )

    def test_initial_history_cannot_origin_status_notification(self):
        order = self.create_order()

        initial_history = order.status_history.get(
            from_status__isnull=True,
        )

        with self.assertRaises(ValidationError):
            OrderStatusNotification.objects.create(
                order=order,
                status_history=initial_history,
                channel=ServiceOrder.NotificationChannel.EMAIL,
                status=OrderStatusNotification.Status.SENT,
                destination=self.customer.email,
                triggered_by=self.admin,
            )

    def test_status_history_exposes_notification_history(self):
        order = self.create_order()
        self.set_preferred_channel(
            order,
            ServiceOrder.NotificationChannel.WHATSAPP,
        )

        change_response = self.change_to_diagnosis(order)

        self.assertEqual(
            change_response.status_code,
            status.HTTP_200_OK,
        )

        response = self.client.get(
            self.history_url(order)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            len(response.data),
            2,
        )

        changed_entry = response.data[1]

        self.assertEqual(
            changed_entry["from_status"],
            ServiceOrder.Status.RECEIVED,
        )
        self.assertEqual(
            changed_entry["to_status"],
            ServiceOrder.Status.DIAGNOSIS,
        )
        self.assertEqual(
            len(changed_entry["notifications"]),
            1,
        )
        self.assertEqual(
            changed_entry["notifications"][0]["status"],
            OrderStatusNotification.Status.PREPARED,
        )
        self.assertEqual(
            changed_entry["notifications"][0]["channel"],
            ServiceOrder.NotificationChannel.WHATSAPP,
        )

    @patch("orders.views.EmailMessage")
    def test_email_content_uses_tracking_code_and_avoids_internal_note(
        self,
        mocked_email_message,
    ):
        mocked_email = mocked_email_message.return_value
        mocked_email.send.return_value = 1

        order = self.create_order()
        self.set_preferred_channel(
            order,
            ServiceOrder.NotificationChannel.EMAIL,
        )

        internal_note = (
            "NOTA INTERNA CONFIDENCIAL: costo técnico $999999."
        )

        response = self.change_to_diagnosis(
            order,
            note=internal_note,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        mocked_email_message.assert_called_once()

        kwargs = mocked_email_message.call_args.kwargs
        body = kwargs["body"]

        self.assertIn(
            order.tracking_code,
            body,
        )
        self.assertIn(
            "Diagnóstico",
            body,
        )
        self.assertNotIn(
            internal_note,
            body,
        )
        self.assertNotIn(
            "25000",
            body,
        )

        mocked_email.send.assert_called_once_with(
            using="default"
        )
