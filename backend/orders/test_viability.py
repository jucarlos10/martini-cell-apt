from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment

from .models import (
    OrderFinancial,
    OrderViabilityAssessment,
    ServiceOrder,
)


class OrderViabilityTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_viability",
            role=User.Role.ADMIN,
        )

        self.technician = User.objects.create_user(
            username="tech_viability",
            role=User.Role.TECH,
        )

        self.helper = User.objects.create_user(
            username="helper_viability",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente viabilidad",
            phone="912345678",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model="Equipo viabilidad",
            created_by=self.admin,
        )

        self.client.force_authenticate(
            user=self.admin
        )

        self.order = self.create_order()

        self.url = reverse(
            "order-viability",
            kwargs={"pk": self.order.pk},
        )

    def create_order(self):
        response = self.client.post(
            reverse("service-order-list-create"),
            {
                "client": self.customer.id,
                "equipment": self.equipment.id,
                "reported_issue": (
                    "Falla utilizada para probar viabilidad."
                ),
                "initial_observations": (
                    "Orden de prueba HU-16."
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

    def create_financial_record(self):
        return OrderFinancial.objects.create(
            order=self.order,
            price_charged=Decimal("100000.00"),
            labor_cost=Decimal("0.00"),
            other_direct_cost=Decimal("0.00"),
            created_by=self.admin,
            updated_by=self.admin,
        )

    def create_assessment(
        self,
        difficulty="LOW",
        warranty_risk="LOW",
    ):
        return self.client.patch(
            self.url,
            {
                "difficulty": difficulty,
                "warranty_risk": warranty_risk,
                "notes": "Evaluación de prueba HU-16.",
            },
            format="json",
        )

    def test_anonymous_user_cannot_access_viability(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_helper_cannot_access_viability(self):
        self.client.force_authenticate(
            user=self.helper
        )

        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_without_assessment_is_not_calculable(self):
        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            response.data["is_calculable"]
        )

        self.assertIsNone(
            response.data["score"]
        )

        self.assertEqual(
            response.data["level_display"],
            "Información insuficiente",
        )

        self.assertIn(
            "difficulty",
            response.data["missing_factors"],
        )

        self.assertIn(
            "warranty_risk",
            response.data["missing_factors"],
        )

    def test_creation_requires_manual_factors(self):
        response = self.client.patch(
            self.url,
            {
                "notes": "Faltan factores.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertFalse(
            OrderViabilityAssessment.objects.filter(
                order=self.order
            ).exists()
        )

    def test_invalid_difficulty_is_rejected(self):
        response = self.client.patch(
            self.url,
            {
                "difficulty": "EXTREME",
                "warranty_risk": "LOW",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertFalse(
            OrderViabilityAssessment.objects.filter(
                order=self.order
            ).exists()
        )

    def test_technician_can_create_assessment(self):
        self.client.force_authenticate(
            user=self.technician
        )

        response = self.create_assessment(
            difficulty="MEDIUM",
            warranty_risk="MEDIUM",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        assessment = (
            OrderViabilityAssessment.objects.get(
                order=self.order
            )
        )

        self.assertEqual(
            assessment.difficulty,
            OrderViabilityAssessment.Difficulty.MEDIUM,
        )

        self.assertEqual(
            assessment.warranty_risk,
            OrderViabilityAssessment.WarrantyRisk.MEDIUM,
        )

        self.assertEqual(
            assessment.created_by,
            self.technician,
        )

        self.assertEqual(
            assessment.updated_by,
            self.technician,
        )

    def test_missing_financial_data_prevents_final_score(self):
        response = self.create_assessment()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertFalse(
            response.data["is_calculable"]
        )

        self.assertIsNone(
            response.data["score"]
        )

        self.assertIn(
            "margin",
            response.data["missing_factors"],
        )

        margin_factor = next(
            factor
            for factor in response.data["factors"]
            if factor["key"] == "margin"
        )

        self.assertFalse(
            margin_factor["available"]
        )

    def test_complete_information_calculates_score(self):
        self.create_financial_record()

        response = self.create_assessment(
            difficulty="LOW",
            warranty_risk="LOW",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            response.data["is_calculable"]
        )

        self.assertEqual(
            response.data["score"],
            100,
        )

        self.assertEqual(
            response.data["max_score"],
            100,
        )

        self.assertEqual(
            response.data["level"],
            "HIGH",
        )

        self.assertEqual(
            response.data["level_display"],
            "Alta",
        )

        self.assertEqual(
            response.data["rule_version"],
            "HU16-v1",
        )

        factor_keys = {
            factor["key"]
            for factor in response.data["factors"]
        }

        self.assertEqual(
            factor_keys,
            {
                "difficulty",
                "parts",
                "margin",
                "time",
                "warranty_risk",
            },
        )

        self.assertIn(
            "no reemplaza",
            response.data["advisory"],
        )

    def test_update_changes_assessment_without_duplication(self):
        self.create_financial_record()

        first_response = self.create_assessment(
            difficulty="LOW",
            warranty_risk="LOW",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        second_response = self.client.patch(
            self.url,
            {
                "difficulty": "HIGH",
                "warranty_risk": "HIGH",
                "notes": "Evaluación actualizada.",
            },
            format="json",
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            OrderViabilityAssessment.objects.filter(
                order=self.order
            ).count(),
            1,
        )

        assessment = (
            OrderViabilityAssessment.objects.get(
                order=self.order
            )
        )

        self.assertEqual(
            assessment.difficulty,
            OrderViabilityAssessment.Difficulty.HIGH,
        )

        self.assertEqual(
            assessment.warranty_risk,
            OrderViabilityAssessment.WarrantyRisk.HIGH,
        )

        self.assertEqual(
            assessment.notes,
            "Evaluación actualizada.",
        )

        self.assertEqual(
            second_response.data["score"],
            73,
        )

        self.assertEqual(
            second_response.data["level"],
            "MEDIUM",
        )

    def test_get_explains_each_factor(self):
        self.create_financial_record()
        self.create_assessment()

        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data["factors"]),
            5,
        )

        for factor in response.data["factors"]:
            self.assertIn(
                "label",
                factor,
            )

            self.assertIn(
                "score",
                factor,
            )

            self.assertIn(
                "max_score",
                factor,
            )

            self.assertIn(
                "explanation",
                factor,
            )