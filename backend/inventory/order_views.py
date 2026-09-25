
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import ServiceOrder

from .models import OrderPart, Part
from .serializers import OrderPartSerializer


class OrderPartsView(APIView):
    """
    Consulta y registro de repuestos utilizados en una orden.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = get_object_or_404(
            ServiceOrder,
            pk=order_id,
        )

        used_parts = (
            OrderPart.objects
            .filter(order=order)
            .select_related(
                "part",
                "supplier",
                "created_by",
            )
            .order_by("created_at", "id")
        )

        serializer = OrderPartSerializer(
            used_parts,
            many=True,
        )

        return Response(serializer.data)

    @transaction.atomic
    def post(self, request, order_id):
        # Solo administradores y técnicos pueden registrar uso.
        if request.user.role not in {"ADMIN", "TECH"}:
            return Response(
                {
                    "detail": (
                        "No tienes permiso para registrar "
                        "repuestos en una orden."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Bloqueamos la orden mientras se registra el repuesto.
        order = get_object_or_404(
            ServiceOrder.objects.select_for_update(),
            pk=order_id,
        )

        if order.status in {
            ServiceOrder.Status.DELIVERED,
            ServiceOrder.Status.CLOSED,
        }:
            return Response(
                {
                    "detail": (
                        "No se pueden agregar repuestos a una "
                        "orden entregada o cerrada."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OrderPartSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        part_id = serializer.validated_data["part"].id
        quantity = serializer.validated_data["quantity"]

        # El bloqueo evita que dos solicitudes descuenten
        # simultáneamente el mismo stock.
        part = get_object_or_404(
            Part.objects
            .select_for_update()
            .select_related("supplier"),
            pk=part_id,
        )

        if not part.is_active:
            return Response(
                {
                    "detail": "El repuesto está inactivo."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not part.supplier.is_active:
            return Response(
                {
                    "detail": "El proveedor está inactivo."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if part.stock < quantity:
            return Response(
                {
                    "detail": "Stock insuficiente.",
                    "available_stock": part.stock,
                    "requested_quantity": quantity,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Guardamos el proveedor y el costo del momento.
        used_part = serializer.save(
            order=order,
            part=part,
            supplier=part.supplier,
            unit_cost=part.unit_cost,
            created_by=request.user,
        )

        # Descontamos la cantidad utilizada del inventario.
        part.stock -= quantity
        part.save(
            update_fields=[
                "stock",
                "updated_at",
            ]
        )

        return Response(
            OrderPartSerializer(used_part).data,
            status=status.HTTP_201_CREATED,
        )