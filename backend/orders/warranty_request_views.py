from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import OrderWarranty, ServiceOrder
from .warranty_request_models import (
    WarrantyRequest,
    WarrantyRequestHistory,
    WarrantyRequestProposal,
    WarrantyRequestResolution,
)
from .warranty_request_serializers import (
    WarrantyRequestAdminNoteSerializer,
    WarrantyRequestHistorySerializer,
    WarrantyRequestProposalReadSerializer,
    WarrantyRequestProposalWriteSerializer,
    WarrantyRequestReadSerializer,
    WarrantyRequestResolutionReadSerializer,
    WarrantyRequestResolutionWriteSerializer,
    WarrantyRequestReturnSerializer,
    WarrantyRequestWriteSerializer,
)
from .warranty_views import require_warranty_permission


def serialize_model_validation_error(exc):
    if hasattr(exc, "message_dict"):
        raise ValidationError(exc.message_dict)

    raise ValidationError(exc.messages)


def require_role(user, allowed_roles, message):
    if getattr(user, "role", None) not in set(allowed_roles):
        return Response(
            {"detail": message},
            status=status.HTTP_403_FORBIDDEN,
        )

    return None


def get_locked_warranty_request(*, order_id, request_id):
    return get_object_or_404(
        WarrantyRequest.objects.select_for_update(),
        pk=request_id,
        order_id=order_id,
    )


def next_history_revision(warranty_request):
    current = (
        warranty_request.history
        .aggregate(max_revision=Max("revision"))
        .get("max_revision")
        or 0
    )
    return current + 1


def next_proposal_revision(warranty_request):
    current = (
        warranty_request.proposals
        .aggregate(max_revision=Max("revision"))
        .get("max_revision")
        or 0
    )
    return current + 1


def create_history_event(
    *,
    warranty_request,
    action,
    from_status,
    to_status,
    user,
    observation="",
    decision=None,
):
    return WarrantyRequestHistory.objects.create(
        request=warranty_request,
        revision=next_history_revision(warranty_request),
        action=action,
        from_status=from_status,
        to_status=to_status,
        observation=observation,
        decision=decision,
        changed_by=user,
        changed_by_username=user.get_username(),
        changed_by_role=getattr(user, "role", "") or "",
    )


def serialize_warranty_request(warranty_request):
    warranty_request = (
        WarrantyRequest.objects
        .select_related(
            "order",
            "order__client",
            "warranty",
            "created_by",
        )
        .prefetch_related("proposals")
        .get(pk=warranty_request.pk)
    )
    return WarrantyRequestReadSerializer(warranty_request).data


class WarrantyRequestListCreateView(APIView):
    """
    HU-22.

    GET:
        Lista las solicitudes de garantía de una orden.

        Se puede filtrar por una garantía concreta con:
        ?warranty_id=<id>

    POST:
        Registra una nueva solicitud y crea su primer evento
        de historial.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        denied = require_warranty_permission(request.user)
        if denied:
            return denied

        order = get_object_or_404(ServiceOrder, pk=pk)

        requests = (
            WarrantyRequest.objects
            .filter(order=order)
            .select_related(
                "order",
                "order__client",
                "warranty",
                "created_by",
            )
            .prefetch_related("proposals")
            .order_by(
                "-requested_on",
                "-created_at",
                "-id",
            )
        )

        warranty_id = request.query_params.get("warranty_id")

        if warranty_id not in (None, ""):
            try:
                warranty_id = int(warranty_id)
            except (TypeError, ValueError):
                raise ValidationError(
                    {
                        "warranty_id": (
                            "El identificador de la garantía "
                            "debe ser un número entero."
                        )
                    }
                )

            warranty = get_object_or_404(
                OrderWarranty,
                pk=warranty_id,
                order=order,
            )

            requests = requests.filter(warranty=warranty)

        return Response(
            WarrantyRequestReadSerializer(
                requests,
                many=True,
            ).data
        )

    @transaction.atomic
    def post(self, request, pk):
        denied = require_warranty_permission(request.user)
        if denied:
            return denied

        order = get_object_or_404(
            ServiceOrder.objects.select_related("client"),
            pk=pk,
        )

        serializer = WarrantyRequestWriteSerializer(
            data=request.data,
            context={
                "order": order,
            },
        )
        serializer.is_valid(raise_exception=True)

        validated_data = dict(serializer.validated_data)

        try:
            warranty_request = WarrantyRequest(
                order=order,
                created_by=request.user,
                **validated_data,
            )
            warranty_request.save()

            WarrantyRequestHistory.objects.create(
                request=warranty_request,
                revision=1,
                action=WarrantyRequestHistory.Action.CREATED,
                from_status=None,
                to_status=WarrantyRequest.Status.PENDING,
                observation=(
                    warranty_request.concurrent_open_reason.strip()
                    or "Solicitud de garantía registrada."
                ),
                changed_by=request.user,
                changed_by_username=request.user.get_username(),
                changed_by_role=getattr(request.user, "role", "") or "",
            )

        except DjangoValidationError as exc:
            serialize_model_validation_error(exc)

        return Response(
            serialize_warranty_request(warranty_request),
            status=status.HTTP_201_CREATED,
        )


class WarrantyRequestDetailView(APIView):
    """
    HU-22/HU-23: consulta interna de una solicitud de garantía.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk, request_id):
        denied = require_warranty_permission(request.user)
        if denied:
            return denied

        warranty_request = get_object_or_404(
            WarrantyRequest.objects
            .select_related(
                "order",
                "order__client",
                "warranty",
                "created_by",
            )
            .prefetch_related("proposals"),
            pk=request_id,
            order_id=pk,
        )

        return Response(
            WarrantyRequestReadSerializer(
                warranty_request,
            ).data
        )


class WarrantyRequestHistoryView(APIView):
    """
    HU-22/HU-23: consulta el historial interno de una solicitud.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk, request_id):
        denied = require_warranty_permission(request.user)
        if denied:
            return denied

        warranty_request = get_object_or_404(
            WarrantyRequest,
            pk=request_id,
            order_id=pk,
        )

        history = (
            warranty_request.history
            .select_related("changed_by")
            .order_by("revision", "id")
        )

        return Response(
            WarrantyRequestHistorySerializer(
                history,
                many=True,
            ).data
        )


class WarrantyRequestsByWarrantyView(APIView):
    """
    HU-22: historial/listado de reclamos asociados
    a una garantía concreta.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk, warranty_id):
        denied = require_warranty_permission(request.user)
        if denied:
            return denied

        order = get_object_or_404(ServiceOrder, pk=pk)

        warranty = get_object_or_404(
            OrderWarranty,
            pk=warranty_id,
            order=order,
        )

        requests = (
            WarrantyRequest.objects
            .filter(
                order=order,
                warranty=warranty,
            )
            .select_related(
                "order",
                "order__client",
                "warranty",
                "created_by",
            )
            .prefetch_related("proposals")
            .order_by(
                "-requested_on",
                "-created_at",
                "-id",
            )
        )

        return Response(
            WarrantyRequestReadSerializer(
                requests,
                many=True,
            ).data
        )


class WarrantyRequestProposalView(APIView):
    """
    HU-23: TECH envía o reenvía una propuesta técnica.

    Transiciones permitidas:
    PENDING -> AWAITING_APPROVAL
    CHANGES_REQUESTED -> AWAITING_APPROVAL
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk, request_id):
        denied = require_role(
            request.user,
            {"TECH"},
            "Solo un técnico puede enviar una propuesta de resolución.",
        )
        if denied:
            return denied

        warranty_request = get_locked_warranty_request(
            order_id=pk,
            request_id=request_id,
        )

        if warranty_request.status == WarrantyRequest.Status.RESOLVED:
            return Response(
                {
                    "detail": (
                        "La solicitud ya está resuelta y no puede "
                        "recibir nuevas propuestas."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        allowed_statuses = {
            WarrantyRequest.Status.PENDING,
            WarrantyRequest.Status.CHANGES_REQUESTED,
        }

        if warranty_request.status not in allowed_statuses:
            return Response(
                {
                    "detail": (
                        "La solicitud no está disponible para enviar "
                        "una propuesta técnica en su estado actual."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        serializer = WarrantyRequestProposalWriteSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        previous_status = warranty_request.status
        validated_data = dict(serializer.validated_data)

        try:
            proposal = WarrantyRequestProposal(
                request=warranty_request,
                revision=next_proposal_revision(warranty_request),
                proposed_by=request.user,
                **validated_data,
            )
            proposal.save()

            warranty_request.status = (
                WarrantyRequest.Status.AWAITING_APPROVAL
            )
            warranty_request.save(update_fields=["status", "updated_at"])

            create_history_event(
                warranty_request=warranty_request,
                action=WarrantyRequestHistory.Action.TECH_PROPOSAL,
                from_status=previous_status,
                to_status=WarrantyRequest.Status.AWAITING_APPROVAL,
                user=request.user,
                observation=(
                    f"Propuesta técnica #{proposal.revision}: "
                    f"{proposal.technical_rationale}"
                ),
            )

        except DjangoValidationError as exc:
            serialize_model_validation_error(exc)

        return Response(
            {
                "request": serialize_warranty_request(warranty_request),
                "proposal": WarrantyRequestProposalReadSerializer(
                    proposal
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class WarrantyRequestReturnView(APIView):
    """
    HU-23: ADMIN devuelve una propuesta al técnico.

    AWAITING_APPROVAL -> CHANGES_REQUESTED
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk, request_id):
        denied = require_role(
            request.user,
            {"ADMIN"},
            "Solo un administrador puede devolver una propuesta.",
        )
        if denied:
            return denied

        warranty_request = get_locked_warranty_request(
            order_id=pk,
            request_id=request_id,
        )

        if warranty_request.status == WarrantyRequest.Status.RESOLVED:
            return Response(
                {
                    "detail": (
                        "La solicitud ya está resuelta y no puede "
                        "volver al técnico."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        if (
            warranty_request.status
            != WarrantyRequest.Status.AWAITING_APPROVAL
        ):
            return Response(
                {
                    "detail": (
                        "Solo se puede devolver una solicitud que esté "
                        "pendiente de aprobación."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        serializer = WarrantyRequestReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data["reason"]
        previous_status = warranty_request.status

        try:
            warranty_request.status = (
                WarrantyRequest.Status.CHANGES_REQUESTED
            )
            warranty_request.save(update_fields=["status", "updated_at"])

            create_history_event(
                warranty_request=warranty_request,
                action=WarrantyRequestHistory.Action.CHANGES_REQUESTED,
                from_status=previous_status,
                to_status=WarrantyRequest.Status.CHANGES_REQUESTED,
                user=request.user,
                observation=reason,
            )

        except DjangoValidationError as exc:
            serialize_model_validation_error(exc)

        return Response(
            serialize_warranty_request(warranty_request),
            status=status.HTTP_200_OK,
        )


class WarrantyRequestResolveView(APIView):
    """
    HU-23: resolución administrativa final.

    Solo ADMIN puede aceptar o rechazar.
    ADMIN puede resolver directamente desde PENDING o
    CHANGES_REQUESTED, o resolver una propuesta en AWAITING_APPROVAL.
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk, request_id):
        denied = require_role(
            request.user,
            {"ADMIN"},
            "Solo un administrador puede resolver una solicitud.",
        )
        if denied:
            return denied

        warranty_request = get_locked_warranty_request(
            order_id=pk,
            request_id=request_id,
        )

        if warranty_request.status == WarrantyRequest.Status.RESOLVED:
            return Response(
                {
                    "detail": (
                        "La solicitud ya fue resuelta. "
                        "La resolución final no puede modificarse."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        if WarrantyRequestResolution.objects.filter(
            request=warranty_request
        ).exists():
            return Response(
                {
                    "detail": (
                        "La solicitud ya posee una resolución final."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        allowed_statuses = {
            WarrantyRequest.Status.PENDING,
            WarrantyRequest.Status.AWAITING_APPROVAL,
            WarrantyRequest.Status.CHANGES_REQUESTED,
        }

        if warranty_request.status not in allowed_statuses:
            return Response(
                {
                    "detail": (
                        "La solicitud no puede resolverse "
                        "en su estado actual."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        serializer = WarrantyRequestResolutionWriteSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        previous_status = warranty_request.status
        validated_data = dict(serializer.validated_data)

        try:
            resolution = WarrantyRequestResolution(
                request=warranty_request,
                resolved_by=request.user,
                **validated_data,
            )
            resolution.save()

            warranty_request.status = WarrantyRequest.Status.RESOLVED
            warranty_request.save(update_fields=["status", "updated_at"])

            create_history_event(
                warranty_request=warranty_request,
                action=WarrantyRequestHistory.Action.RESOLVED,
                from_status=previous_status,
                to_status=WarrantyRequest.Status.RESOLVED,
                user=request.user,
                observation=resolution.rationale,
                decision=resolution.decision,
            )

        except DjangoValidationError as exc:
            serialize_model_validation_error(exc)

        return Response(
            {
                "request": serialize_warranty_request(warranty_request),
                "resolution": WarrantyRequestResolutionReadSerializer(
                    resolution
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class WarrantyRequestAdminNoteView(APIView):
    """
    HU-23: ADMIN agrega una corrección/observación administrativa
    a una solicitud ya resuelta.

    No modifica la decisión final ni reabre la solicitud.
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk, request_id):
        denied = require_role(
            request.user,
            {"ADMIN"},
            (
                "Solo un administrador puede registrar "
                "observaciones administrativas."
            ),
        )
        if denied:
            return denied

        warranty_request = get_locked_warranty_request(
            order_id=pk,
            request_id=request_id,
        )

        if warranty_request.status != WarrantyRequest.Status.RESOLVED:
            return Response(
                {
                    "detail": (
                        "Las observaciones administrativas de corrección "
                        "solo pueden agregarse a solicitudes resueltas."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        serializer = WarrantyRequestAdminNoteSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        observation = serializer.validated_data["observation"]

        create_history_event(
            warranty_request=warranty_request,
            action=WarrantyRequestHistory.Action.ADMIN_NOTE,
            from_status=WarrantyRequest.Status.RESOLVED,
            to_status=WarrantyRequest.Status.RESOLVED,
            user=request.user,
            observation=observation,
        )

        return Response(
            serialize_warranty_request(warranty_request),
            status=status.HTTP_200_OK,
        )
