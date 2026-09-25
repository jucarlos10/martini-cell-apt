
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import OrderWarranty, ServiceOrder
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
            .select_related("order_part__part", "order_part__supplier")
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


class OrderWarrantyHistoryView(APIView):
    """
    GET: consulta las revisiones de una garantía.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk, warranty_id):
        denied = require_warranty_permission(request.user)
        if denied:
            return denied

        warranty = get_object_or_404(
            OrderWarranty,
            pk=warranty_id,
            order_id=pk,
        )

        history = warranty.history.all().order_by("revision")

        return Response(
            OrderWarrantyHistorySerializer(
                history,
                many=True,
            ).data
        )