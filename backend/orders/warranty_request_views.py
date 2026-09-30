from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
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
)
from .warranty_request_serializers import (
    WarrantyRequestHistorySerializer,
    WarrantyRequestReadSerializer,
    WarrantyRequestWriteSerializer,
)
from .warranty_views import require_warranty_permission


def serialize_model_validation_error(exc):
    if hasattr(exc, "message_dict"):
        raise ValidationError(exc.message_dict)

    raise ValidationError(exc.messages)


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
            )

        except DjangoValidationError as exc:
            serialize_model_validation_error(exc)

        warranty_request = (
            WarrantyRequest.objects
            .select_related(
                "order",
                "order__client",
                "warranty",
                "created_by",
            )
            .get(pk=warranty_request.pk)
        )

        return Response(
            WarrantyRequestReadSerializer(warranty_request).data,
            status=status.HTTP_201_CREATED,
        )


class WarrantyRequestDetailView(APIView):
    """
    HU-22: consulta interna de una solicitud de garantía.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk, request_id):
        denied = require_warranty_permission(request.user)
        if denied:
            return denied

        warranty_request = get_object_or_404(
            WarrantyRequest.objects.select_related(
                "order",
                "order__client",
                "warranty",
                "created_by",
            ),
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
    HU-22: consulta el historial interno de una solicitud.
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
