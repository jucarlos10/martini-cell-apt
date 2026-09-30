from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Client
from devices.models import Equipment

from .models import OrderWarranty, ServiceOrder
from .warranty_request_models import (
    WarrantyActionType,
    WarrantyRequest,
    WarrantyRequestHistory,
    WarrantyRequestProposal,
    WarrantyRequestResolution,
)


class WarrantyRequestResolutionTests(APITestCase):
    """
    HU-23: propuesta técnica, devolución, resolución final
    y trazabilidad de solicitudes de garantía.
    """

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_hu23",
            role=User.Role.ADMIN,
        )
        self.technician = User.objects.create_user(
            username="tech_hu23",
            role=User.Role.TECH,
        )
        self.helper = User.objects.create_user(
            username="helper_hu23",
            role=User.Role.HELPER,
        )

        self.customer = Client.objects.create(
            rut="12.345.678-5",
            name="Cliente HU-23",
            phone="912345678",
            created_by=self.admin,
        )

        self.equipment = Equipment.objects.create(
            client=self.customer,
            equipment_type=Equipment.EquipmentType.CELULAR,
            brand="Samsung",
            model="Equipo HU-23",
            created_by=self.admin,
        )

        self.order = ServiceOrder.objects.create(
            client=self.customer,
            equipment=self.equipment,
            reported_issue="Falla original de prueba.",
            created_by=self.admin,
        )

        today = timezone.localdate()

        self.warranty = OrderWarranty.objects.create(
            order=self.order,
            warranty_type=OrderWarranty.WarrantyType.SERVICE,
            is_applicable=True,
            starts_on=today - timedelta(days=10),
            ends_on=today + timedelta(days=30),
            conditions="Cobertura HU-23.",
            created_by=self.admin,
            updated_by=self.admin,
        )

        self.warranty_request = WarrantyRequest.objects.create(
            order=self.order,
            warranty=self.warranty,
            requested_on=today,
            problem_description="El cliente reporta nuevamente la falla.",
            created_by=self.admin,
        )

        WarrantyRequestHistory.objects.create(
            request=self.warranty_request,
            revision=1,
            action=WarrantyRequestHistory.Action.CREATED,
            from_status=None,
            to_status=WarrantyRequest.Status.PENDING,
            observation="Solicitud de garantía registrada.",
            changed_by=self.admin,
            changed_by_username=self.admin.username,
            changed_by_role=self.admin.role,
        )

    def proposal_url(self):
        return reverse(
            "warranty-request-proposal",
            kwargs={
                "pk": self.order.pk,
                "request_id": self.warranty_request.pk,
            },
        )

    def return_url(self):
        return reverse(
            "warranty-request-return",
            kwargs={
                "pk": self.order.pk,
                "request_id": self.warranty_request.pk,
            },
        )

    def resolve_url(self):
        return reverse(
            "warranty-request-resolve",
            kwargs={
                "pk": self.order.pk,
                "request_id": self.warranty_request.pk,
            },
        )

    def detail_url(self):
        return reverse(
            "warranty-request-detail",
            kwargs={
                "pk": self.order.pk,
                "request_id": self.warranty_request.pk,
            },
        )

    def history_url(self):
        return reverse(
            "warranty-request-history",
            kwargs={
                "pk": self.order.pk,
                "request_id": self.warranty_request.pk,
            },
        )

    def admin_note_url(self):
        return reverse(
            "warranty-request-admin-note",
            kwargs={
                "pk": self.order.pk,
                "request_id": self.warranty_request.pk,
            },
        )

    def proposal_payload(self, **changes):
        payload = {
            "technical_rationale": (
                "La falla coincide con el diagnóstico original."
            ),
            "action_type": WarrantyActionType.REPAIR,
            "action_description": (
                "Revisar el equipo y repetir la reparación cubierta."
            ),
        }
        payload.update(changes)
        return payload

    def accepted_resolution_payload(self, **changes):
        payload = {
            "decision": WarrantyRequestResolution.Decision.ACCEPTED,
            "rationale": (
                "La falla corresponde a la cobertura de garantía."
            ),
            "action_type": WarrantyActionType.REPAIR,
            "action_description": (
                "Se autoriza repetir la reparación sin costo."
            ),
        }
        payload.update(changes)
        return payload

    def rejected_resolution_payload(self, **changes):
        payload = {
            "decision": WarrantyRequestResolution.Decision.REJECTED,
            "rationale": (
                "La falla reportada no corresponde al trabajo cubierto."
            ),
        }
        payload.update(changes)
        return payload

    def send_proposal(self):
        self.client.force_authenticate(user=self.technician)
        return self.client.post(
            self.proposal_url(),
            self.proposal_payload(),
            format="json",
        )

    def test_tech_can_submit_proposal(self):
        response = self.send_proposal()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.warranty_request.refresh_from_db()
        self.assertEqual(
            self.warranty_request.status,
            WarrantyRequest.Status.AWAITING_APPROVAL,
        )

        proposal = WarrantyRequestProposal.objects.get()
        self.assertEqual(proposal.revision, 1)
        self.assertEqual(
            proposal.proposed_by,
            self.technician,
        )
        self.assertEqual(
            proposal.proposed_by_username,
            self.technician.username,
        )
        self.assertEqual(
            proposal.proposed_by_role,
            User.Role.TECH,
        )

        history = self.warranty_request.history.get(revision=2)
        self.assertEqual(
            history.action,
            WarrantyRequestHistory.Action.TECH_PROPOSAL,
        )
        self.assertEqual(
            history.from_status,
            WarrantyRequest.Status.PENDING,
        )
        self.assertEqual(
            history.to_status,
            WarrantyRequest.Status.AWAITING_APPROVAL,
        )
        self.assertEqual(
            history.changed_by,
            self.technician,
        )

    def test_admin_cannot_submit_technical_proposal(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.proposal_url(),
            self.proposal_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertFalse(WarrantyRequestProposal.objects.exists())

    def test_helper_cannot_submit_proposal(self):
        self.client.force_authenticate(user=self.helper)

        response = self.client.post(
            self.proposal_url(),
            self.proposal_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertFalse(WarrantyRequestProposal.objects.exists())

    def test_proposal_requires_rationale_and_action_description(self):
        self.client.force_authenticate(user=self.technician)

        response = self.client.post(
            self.proposal_url(),
            self.proposal_payload(
                technical_rationale="   ",
                action_description="   ",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(WarrantyRequestProposal.objects.exists())

        self.warranty_request.refresh_from_db()
        self.assertEqual(
            self.warranty_request.status,
            WarrantyRequest.Status.PENDING,
        )
        self.assertEqual(
            self.warranty_request.history.count(),
            1,
        )

    def test_admin_can_return_proposal_to_technician(self):
        proposal_response = self.send_proposal()
        self.assertEqual(proposal_response.status_code, 201)

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.return_url(),
            {
                "reason": (
                    "Falta detallar las pruebas realizadas al equipo."
                )
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.warranty_request.refresh_from_db()
        self.assertEqual(
            self.warranty_request.status,
            WarrantyRequest.Status.CHANGES_REQUESTED,
        )

        history = self.warranty_request.history.get(revision=3)
        self.assertEqual(
            history.action,
            WarrantyRequestHistory.Action.CHANGES_REQUESTED,
        )
        self.assertEqual(
            history.changed_by,
            self.admin,
        )
        self.assertIn(
            "Falta detallar",
            history.observation,
        )

    def test_return_requires_reason(self):
        proposal_response = self.send_proposal()
        self.assertEqual(proposal_response.status_code, 201)

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.return_url(),
            {"reason": "   "},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.warranty_request.refresh_from_db()
        self.assertEqual(
            self.warranty_request.status,
            WarrantyRequest.Status.AWAITING_APPROVAL,
        )
        self.assertEqual(
            self.warranty_request.history.count(),
            2,
        )

    def test_tech_can_resubmit_after_changes_requested(self):
        proposal_response = self.send_proposal()
        self.assertEqual(proposal_response.status_code, 201)

        self.client.force_authenticate(user=self.admin)
        return_response = self.client.post(
            self.return_url(),
            {"reason": "Complementar fundamento técnico."},
            format="json",
        )
        self.assertEqual(return_response.status_code, 200)

        self.client.force_authenticate(user=self.technician)
        second_response = self.client.post(
            self.proposal_url(),
            self.proposal_payload(
                technical_rationale=(
                    "Se realizaron pruebas adicionales y la falla "
                    "se reproduce bajo carga."
                )
            ),
            format="json",
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.warranty_request.refresh_from_db()
        self.assertEqual(
            self.warranty_request.status,
            WarrantyRequest.Status.AWAITING_APPROVAL,
        )

        proposals = list(
            self.warranty_request.proposals.order_by("revision")
        )
        self.assertEqual(len(proposals), 2)
        self.assertEqual(
            [proposal.revision for proposal in proposals],
            [1, 2],
        )

        self.assertEqual(
            self.warranty_request.history.count(),
            4,
        )

    def test_admin_can_accept_request_directly_from_pending(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.resolve_url(),
            self.accepted_resolution_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.warranty_request.refresh_from_db()
        self.assertEqual(
            self.warranty_request.status,
            WarrantyRequest.Status.RESOLVED,
        )

        resolution = WarrantyRequestResolution.objects.get()
        self.assertEqual(
            resolution.decision,
            WarrantyRequestResolution.Decision.ACCEPTED,
        )
        self.assertEqual(
            resolution.resolved_by,
            self.admin,
        )
        self.assertEqual(
            resolution.resolved_by_username,
            self.admin.username,
        )
        self.assertEqual(
            resolution.resolved_by_role,
            User.Role.ADMIN,
        )

        history = self.warranty_request.history.get(revision=2)
        self.assertEqual(
            history.action,
            WarrantyRequestHistory.Action.RESOLVED,
        )
        self.assertEqual(
            history.decision,
            WarrantyRequestResolution.Decision.ACCEPTED,
        )
        self.assertEqual(
            history.to_status,
            WarrantyRequest.Status.RESOLVED,
        )

    def test_admin_can_reject_request_directly(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.resolve_url(),
            self.rejected_resolution_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        resolution = WarrantyRequestResolution.objects.get()
        self.assertEqual(
            resolution.decision,
            WarrantyRequestResolution.Decision.REJECTED,
        )
        self.assertIsNone(resolution.action_type)
        self.assertEqual(
            resolution.action_description,
            "",
        )

        self.warranty_request.refresh_from_db()
        self.assertEqual(
            self.warranty_request.status,
            WarrantyRequest.Status.RESOLVED,
        )

    def test_accepted_resolution_requires_action(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.resolve_url(),
            {
                "decision": WarrantyRequestResolution.Decision.ACCEPTED,
                "rationale": "Corresponde aceptar la garantía.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(WarrantyRequestResolution.objects.exists())

        self.warranty_request.refresh_from_db()
        self.assertEqual(
            self.warranty_request.status,
            WarrantyRequest.Status.PENDING,
        )
        self.assertEqual(
            self.warranty_request.history.count(),
            1,
        )

    def test_tech_cannot_resolve_request(self):
        self.client.force_authenticate(user=self.technician)

        response = self.client.post(
            self.resolve_url(),
            self.accepted_resolution_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertFalse(WarrantyRequestResolution.objects.exists())

    def test_request_cannot_be_resolved_twice(self):
        self.client.force_authenticate(user=self.admin)

        first = self.client.post(
            self.resolve_url(),
            self.accepted_resolution_payload(),
            format="json",
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            self.resolve_url(),
            self.rejected_resolution_payload(),
            format="json",
        )

        self.assertEqual(
            second.status_code,
            status.HTTP_409_CONFLICT,
        )
        self.assertEqual(
            WarrantyRequestResolution.objects.count(),
            1,
        )
        self.assertEqual(
            self.warranty_request.history.count(),
            2,
        )

    def test_resolved_request_cannot_receive_new_proposal(self):
        self.client.force_authenticate(user=self.admin)

        resolved = self.client.post(
            self.resolve_url(),
            self.accepted_resolution_payload(),
            format="json",
        )
        self.assertEqual(resolved.status_code, 200)

        self.client.force_authenticate(user=self.technician)

        response = self.client.post(
            self.proposal_url(),
            self.proposal_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )
        self.assertFalse(WarrantyRequestProposal.objects.exists())

    def test_admin_note_does_not_reopen_or_modify_resolution(self):
        self.client.force_authenticate(user=self.admin)

        resolved = self.client.post(
            self.resolve_url(),
            self.accepted_resolution_payload(),
            format="json",
        )
        self.assertEqual(resolved.status_code, 200)

        original_resolution = WarrantyRequestResolution.objects.get()

        note_response = self.client.post(
            self.admin_note_url(),
            {
                "observation": (
                    "Corrección administrativa: se aclara el detalle "
                    "del registro sin modificar la decisión."
                )
            },
            format="json",
        )

        self.assertEqual(
            note_response.status_code,
            status.HTTP_200_OK,
        )

        self.warranty_request.refresh_from_db()
        original_resolution.refresh_from_db()

        self.assertEqual(
            self.warranty_request.status,
            WarrantyRequest.Status.RESOLVED,
        )
        self.assertEqual(
            original_resolution.decision,
            WarrantyRequestResolution.Decision.ACCEPTED,
        )

        history = self.warranty_request.history.get(revision=3)
        self.assertEqual(
            history.action,
            WarrantyRequestHistory.Action.ADMIN_NOTE,
        )
        self.assertEqual(
            history.from_status,
            WarrantyRequest.Status.RESOLVED,
        )
        self.assertEqual(
            history.to_status,
            WarrantyRequest.Status.RESOLVED,
        )

    def test_detail_shows_proposer_and_final_admin(self):
        proposal_response = self.send_proposal()
        self.assertEqual(proposal_response.status_code, 201)

        self.client.force_authenticate(user=self.admin)

        resolve_response = self.client.post(
            self.resolve_url(),
            self.accepted_resolution_payload(),
            format="json",
        )
        self.assertEqual(resolve_response.status_code, 200)

        detail = self.client.get(self.detail_url())

        self.assertEqual(detail.status_code, 200)
        self.assertEqual(
            detail.data["status"],
            WarrantyRequest.Status.RESOLVED,
        )
        self.assertEqual(
            detail.data["latest_proposal"]["proposed_by_username"],
            self.technician.username,
        )
        self.assertEqual(
            detail.data["resolution"]["resolved_by_username"],
            self.admin.username,
        )
        self.assertEqual(
            detail.data["resolution"]["decision"],
            WarrantyRequestResolution.Decision.ACCEPTED,
        )

    def test_history_preserves_complete_flow(self):
        proposal_response = self.send_proposal()
        self.assertEqual(proposal_response.status_code, 201)

        self.client.force_authenticate(user=self.admin)

        return_response = self.client.post(
            self.return_url(),
            {"reason": "Se requiere mayor detalle."},
            format="json",
        )
        self.assertEqual(return_response.status_code, 200)

        self.client.force_authenticate(user=self.technician)

        resubmit_response = self.client.post(
            self.proposal_url(),
            self.proposal_payload(
                technical_rationale="Fundamento técnico corregido."
            ),
            format="json",
        )
        self.assertEqual(resubmit_response.status_code, 201)

        self.client.force_authenticate(user=self.admin)

        resolve_response = self.client.post(
            self.resolve_url(),
            self.accepted_resolution_payload(),
            format="json",
        )
        self.assertEqual(resolve_response.status_code, 200)

        history_response = self.client.get(self.history_url())

        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(len(history_response.data), 5)

        self.assertEqual(
            [
                item["action"]
                for item in history_response.data
            ],
            [
                WarrantyRequestHistory.Action.CREATED,
                WarrantyRequestHistory.Action.TECH_PROPOSAL,
                WarrantyRequestHistory.Action.CHANGES_REQUESTED,
                WarrantyRequestHistory.Action.TECH_PROPOSAL,
                WarrantyRequestHistory.Action.RESOLVED,
            ],
        )

        self.assertEqual(
            history_response.data[-1]["decision"],
            WarrantyRequestResolution.Decision.ACCEPTED,
        )

    def test_wrong_order_returns_not_found(self):
        other_order = ServiceOrder.objects.create(
            client=self.customer,
            equipment=self.equipment,
            reported_issue="Otra orden.",
            created_by=self.admin,
        )

        self.client.force_authenticate(user=self.admin)

        url = reverse(
            "warranty-request-resolve",
            kwargs={
                "pk": other_order.pk,
                "request_id": self.warranty_request.pk,
            },
        )

        response = self.client.post(
            url,
            self.accepted_resolution_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertFalse(WarrantyRequestResolution.objects.exists())

    def test_anonymous_user_cannot_resolve(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.resolve_url(),
            self.accepted_resolution_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertFalse(WarrantyRequestResolution.objects.exists())
