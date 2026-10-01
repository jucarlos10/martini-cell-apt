from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    OrderWarranty,
    OrderWarrantyHistory,
    ServiceOrder,
)
from .warranty_serializers import (
    OrderWarrantyHistorySerializer,
    OrderWarrantyReadSerializer,
    OrderWarrantyWriteSerializer,
)
from .warranty_services import save_warranty_with_history


def require_warranty_permission(user):
    """
    ADMIN y TECH pueden consultar y gestionar garantías.
    """

    if getattr(user, "role", None) not in {"ADMIN", "TECH"}:
        return Response(
            {"detail": "No tienes permiso para gestionar garantías."},
            status=status.HTTP_403_FORBIDDEN,
        )

    return None


def save_and_serialize_warranty(
    *,
    order,
    user,
    serializer,
    warranty=None,
):
    """
    Guarda la garantía y su historial; convierte los errores
    de validación de Django en respuestas HTTP 400.
    """

    validated_data = dict(serializer.validated_data)
    change_note = validated_data.pop("change_note", "")

    try:
        saved_warranty = save_warranty_with_history(
            order=order,
            user=user,
            validated_data=validated_data,
            warranty=warranty,
            change_note=change_note,
        )
    except DjangoValidationError as exc:
        if hasattr(exc, "message_dict"):
            raise ValidationError(exc.message_dict)

        raise ValidationError(exc.messages)

    return OrderWarrantyReadSerializer(saved_warranty).data


class OrderWarrantyListCreateView(APIView):
    """
    GET: lista las garantías de una orden.
    POST: registra una garantía y su primera revisión.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        denied = require_warranty_permission(request.user)
        if denied:
            return denied

        order = get_object_or_404(ServiceOrder, pk=pk)

        warranties = (
            OrderWarranty.objects
            .filter(order=order)
            .select_related(
                "order_part__part",
                "order_part__supplier",
            )
        )

        return Response(
            OrderWarrantyReadSerializer(
                warranties,
                many=True,
            ).data
        )

    def post(self, request, pk):
        denied = require_warranty_permission(request.user)
        if denied:
            return denied

        order = get_object_or_404(ServiceOrder, pk=pk)

        serializer = OrderWarrantyWriteSerializer(
            data=request.data,
            context={"order": order},
        )
        serializer.is_valid(raise_exception=True)

        result = save_and_serialize_warranty(
            order=order,
            user=request.user,
            serializer=serializer,
        )

        return Response(
            result,
            status=status.HTTP_201_CREATED,
        )


class OrderWarrantyDetailView(APIView):
    """
    GET: consulta una garantía.
    PATCH: actualiza la garantía y crea una nueva revisión.
    DELETE: elimina una garantía ingresada por error,
    conservando evidencia histórica de la eliminación.

    Si la garantía ya tiene solicitudes/reclamos asociados,
    no puede eliminarse porque esos registros forman parte
    de la trazabilidad histórica de la atención.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk, warranty_id):
        denied = require_warranty_permission(request.user)
        if denied:
            return denied

        warranty = get_object_or_404(
            OrderWarranty.objects.select_related(
                "order_part__part",
                "order_part__supplier",
            ),
            pk=warranty_id,
            order_id=pk,
        )

        return Response(
            OrderWarrantyReadSerializer(warranty).data
        )

    def patch(self, request, pk, warranty_id):
        denied = require_warranty_permission(request.user)
        if denied:
            return denied

        order = get_object_or_404(ServiceOrder, pk=pk)

        warranty = get_object_or_404(
            OrderWarranty,
            pk=warranty_id,
            order=order,
        )

        serializer = OrderWarrantyWriteSerializer(
            warranty,
            data=request.data,
            partial=True,
            context={"order": order},
        )
        serializer.is_valid(raise_exception=True)

        result = save_and_serialize_warranty(
            order=order,
            user=request.user,
            serializer=serializer,
            warranty=warranty,
        )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def delete(self, request, pk, warranty_id):
        denied = require_warranty_permission(request.user)
        if denied:
            return denied

        warranty = get_object_or_404(
            OrderWarranty.objects.select_for_update(),
            pk=warranty_id,
            order_id=pk,
        )

        # HU-22: una garantía que ya posee solicitudes/reclamos
        # no puede eliminarse. De hacerlo se perdería la relación
        # necesaria para consultar la trazabilidad del reclamo.
        if warranty.requests.exists():
            return Response(
                {
                    "detail": (
                        "No se puede eliminar esta garantía porque "
                        "tiene solicitudes de garantía asociadas."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        last_revision = (
            OrderWarrantyHistory.objects
            .filter(warranty=warranty)
            .order_by("-revision")
            .values_list("revision", flat=True)
            .first()
        ) or 0

        OrderWarrantyHistory.objects.create(
            warranty=warranty,
            warranty_id_snapshot=warranty.pk,
            revision=last_revision + 1,
            action=OrderWarrantyHistory.Action.DELETED,
            order=warranty.order,
            warranty_type=warranty.warranty_type,
            order_part=warranty.order_part,
            is_applicable=warranty.is_applicable,
            starts_on=warranty.starts_on,
            ends_on=warranty.ends_on,
            conditions=warranty.conditions,
            change_note="Garantía eliminada por error.",
            changed_by=request.user,
            changed_by_username=request.user.get_username(),
        )

        warranty.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )


class OrderWarrantyHistoryView(APIView):
    """
    GET: consulta las revisiones de una garantía.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk, warranty_id):
        denied = require_warranty_permission(request.user)
        if denied:
            return denied

        history = OrderWarrantyHistory.objects.filter(
            order_id=pk,
            warranty_id_snapshot=warranty_id,
        ).order_by("revision")
        if not history.exists():
            # Conserva la respuesta previa para garantías existentes sin
            # historial, si hubiera registros heredados sin revisiones.
            get_object_or_404(OrderWarranty, pk=warranty_id, order_id=pk)

        return Response(
            OrderWarrantyHistorySerializer(
                history,
                many=True,
            ).data
        )
