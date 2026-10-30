from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import User
from devices.models import Equipment
from orders.models import ServiceOrder

from .models import Client, ClientLoyaltyReview


class LoyaltyMilestoneTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_beneficios", role=User.Role.ADMIN
        )
        self.technician = User.objects.create_user(
            username="tech_beneficios", role=User.Role.TECH
        )
        self.customer = Client.objects.create(
            rut="123456785", name="Cliente ejemplo", phone="912345678"
        )
        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Marca",
            model="Modelo",
            created_by=self.admin,
        )
        self.alerts_url = reverse("client-loyalty-alerts")
        self.review_url = reverse(
            "client-loyalty-review", kwargs={"pk": self.customer.pk}
        )
        self.detail_url = reverse(
            "client-detail", kwargs={"pk": self.customer.pk}
        )
        self.client.force_authenticate(user=self.admin)

    def add_order(self):
        response = self.client.post(
            reverse("service-order-list-create"),
            {
                "client": self.customer.pk,
                "equipment": self.equipment.pk,
                "reported_issue": "Revisión solicitada por cliente.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return response.data

    def test_six_ingresos_trigger_one_private_pending_alert_and_admin_review(self):
        for _ in range(5):
            self.add_order()

        before = self.client.get(self.detail_url)
        self.assertEqual(before.data["loyalty_order_count"], 5)
        self.assertEqual(before.data["loyalty_cycle_visits"], 5)
        self.assertEqual(before.data["loyalty_cycle_target"], 6)
        self.assertIsNone(before.data["loyalty_pending_milestone"])
        self.assertEqual(self.client.get(self.alerts_url).data, [])

        sixth = self.add_order()
        detail = self.client.get(self.detail_url)
        self.assertEqual(detail.data["loyalty_order_count"], 6)
        self.assertEqual(detail.data["loyalty_pending_milestone"], 6)
        self.assertEqual(self.client.get(self.alerts_url).data[0]["id"], self.customer.pk)

        self.client.force_authenticate(user=None)
        public = self.client.get(
            reverse("public-order-status", kwargs={"tracking_code": sixth["tracking_code"]})
        )
        self.assertEqual(public.status_code, 200)
        self.assertNotIn("loyalty_order_count", public.data)
        self.assertNotIn("loyalty_pending_milestone", public.data)
        self.assertEqual(self.client.get(self.alerts_url).status_code, 401)

        self.client.force_authenticate(user=self.technician)
        self.assertEqual(self.client.get(self.alerts_url).status_code, 403)
        self.assertEqual(
            self.client.post(self.review_url, {"benefit_applied": "10 %"}).status_code, 403
        )

        self.client.force_authenticate(user=self.admin)
        self.assertEqual(self.client.post(self.review_url, {"benefit_applied": "  "}).status_code, 400)
        approved = self.client.post(
            self.review_url, {"benefit_applied": "Promoción aplicada en mostrador."}
        )
        self.assertEqual(approved.status_code, 201)
        self.assertEqual(approved.data["milestone"], 6)
        self.assertEqual(approved.data["cycle_target"], 6)
        self.assertEqual(approved.data["reviewed_by_username"], self.admin.username)
        self.assertEqual(self.client.get(self.alerts_url).data, [])
        self.assertEqual(self.client.get(self.detail_url).data["loyalty_next_milestone"], 11)
        self.assertEqual(self.client.get(self.detail_url).data["loyalty_cycle_visits"], 0)
        self.assertEqual(self.client.get(self.detail_url).data["loyalty_cycle_target"], 5)
        self.assertEqual(self.client.post(self.review_url, {"benefit_applied": "Otra"}).status_code, 409)
        self.assertEqual(ClientLoyaltyReview.objects.count(), 1)

        for _ in range(5):
            self.add_order()
        self.assertEqual(
            self.client.get(self.alerts_url).data[0]["loyalty_pending_milestone"], 11
        )
        second = self.client.post(
            self.review_url, {"benefit_applied": "Promoción aplicada por Marcos."}
        )
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.data["cycle_target"], 5)
        self.assertEqual(self.client.get(self.detail_url).data["loyalty_cycle_target"], 4)

        for _ in range(4):
            self.add_order()
        third = self.client.post(
            self.review_url, {"benefit_applied": "Beneficio de tercer ciclo."}
        )
        self.assertEqual(third.status_code, 201)
        self.assertEqual(third.data["milestone"], 15)
        self.assertEqual(third.data["cycle_target"], 4)

        for _ in range(4):
            self.add_order()
        fourth = self.client.post(
            self.review_url, {"benefit_applied": "Beneficio de cuarto ciclo."}
        )
        self.assertEqual(fourth.status_code, 201)
        self.assertEqual(fourth.data["milestone"], 19)
        self.assertEqual(fourth.data["cycle_target"], 4)
        self.assertEqual(self.client.get(self.detail_url).data["loyalty_cycle_target"], 4)
        self.assertEqual(self.client.get(self.review_url).data[0]["benefit_applied"],
                         "Beneficio de cuarto ciclo.")

    def test_rut_is_optional_and_adding_it_enables_pending_older_orders(self):
        self.customer.rut = None
        self.customer.save(update_fields=["rut"])
        for _ in range(6):
            self.add_order()

        missing = self.client.get(self.detail_url)
        self.assertEqual(missing.data["loyalty_order_count"], 6)
        self.assertIsNone(missing.data["loyalty_pending_milestone"])
        self.assertEqual(self.client.get(self.alerts_url).data, [])

        updated = self.client.patch(self.detail_url, {"rut": "12.345.678-5"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["loyalty_pending_milestone"], 6)
        self.assertEqual(len(self.client.get(self.alerts_url).data), 1)

    def test_extra_arrival_before_benefit_carries_over_after_application(self):
        for _ in range(7):
            self.add_order()
        before = self.client.get(self.detail_url).data
        self.assertEqual(before["loyalty_cycle_visits"], 7)
        self.assertEqual(before["loyalty_pending_milestone"], 6)

        applied = self.client.post(
            self.review_url, {"benefit_applied": "Beneficio aplicado en tienda."}
        )
        self.assertEqual(applied.status_code, 201)
        after = self.client.get(self.detail_url).data
        self.assertEqual(after["loyalty_cycle_visits"], 1)
        self.assertEqual(after["loyalty_cycle_target"], 5)

    def test_reassigned_order_recounts_customers_without_double_credit(self):
        for _ in range(6):
            self.add_order()
        other = Client.objects.create(
            rut="111111111", name="Otro cliente", phone="923456789"
        )
        other_device = Equipment.objects.create(
            client=other,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Marca",
            model="Otro",
            created_by=self.admin,
        )
        order = ServiceOrder.objects.filter(client=self.customer).first()
        changed = self.client.patch(
            reverse("service-order-detail", kwargs={"pk": order.pk}),
            {
                "client": other.pk,
                "equipment": other_device.pk,
                "change_reason": "Ficha original equivocada.",
            },
            format="json",
        )
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(self.client.get(self.detail_url).data["loyalty_order_count"], 5)
        self.assertEqual(self.client.get(self.alerts_url).data, [])
        other_detail = self.client.get(reverse("client-detail", kwargs={"pk": other.pk}))
        self.assertEqual(other_detail.data["loyalty_order_count"], 1)
