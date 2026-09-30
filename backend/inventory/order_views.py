from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import OrderWarranty, ServiceOrder

from .models import (
    OrderPart,
    OrderPartCorrectionHistory,
    Part,
)
from .serializers import (
    OrderPartCorrectionHistorySerializer,
    OrderPartCorrectionSerializer,
    OrderPartSerializer,
)


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
            context={"request": request},
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


class OrderPartCorrectionView(APIView):
    """
    HU-24: corrige cantidad o nota de un uso de repuesto.

    Repuesto, proveedor y costo unitario no se modifican
    directamente. Para esos casos corresponde anular el uso
    y registrar uno nuevo mediante el flujo de HU-25.
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, order_id, order_part_id):
        if request.user.role not in {"ADMIN", "TECH"}:
            return Response(
                {
                    "detail": (
                        "No tienes permiso para corregir "
                        "repuestos de una orden."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Bloqueamos la orden para evitar cambios concurrentes
        # mientras se valida y aplica la corrección.
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
                        "No se pueden corregir repuestos de una "
                        "orden entregada o cerrada."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # El filtro por order asegura que un uso perteneciente a
        # otra orden se rechace como inexistente para esta orden.
        #
        # Importante: no hacemos select_related("created_by") aquí.
        # created_by es nullable y PostgreSQL no permite FOR UPDATE
        # sobre el lado nullable de un OUTER JOIN.
        used_part = get_object_or_404(
            OrderPart.objects
            .select_for_update()
            .select_related(
                "part",
                "supplier",
            ),
            pk=order_part_id,
            order=order,
        )

        serializer = OrderPartCorrectionSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        field_name = serializer.validated_data["field_name"]
        new_value = serializer.validated_data["normalized_value"]
        reason = serializer.validated_data["reason"]

        if field_name == OrderPartCorrectionHistory.Field.QUANTITY:
            return self._correct_quantity(
                request=request,
                used_part=used_part,
                new_quantity=new_value,
                reason=reason,
            )

        return self._correct_note(
            request=request,
            used_part=used_part,
            new_note=new_value,
            reason=reason,
        )

    def _correct_quantity(
        self,
        request,
        used_part,
        new_quantity,
        reason,
    ):
        old_quantity = used_part.quantity

        if new_quantity == old_quantity:
            return Response(
                {
                    "detail": (
                        "La nueva cantidad debe ser distinta "
                        "de la cantidad actual."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Si el uso ya originó una garantía de repuesto,
        # la cantidad queda congelada para no alterar el consumo
        # asociado a esa garantía.
        if OrderWarranty.objects.filter(
            order_part=used_part,
        ).exists():
            return Response(
                {
                    "detail": (
                        "No se puede corregir la cantidad porque "
                        "este uso tiene una garantía de repuesto "
                        "asociada. Solo puedes corregir la nota."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        part = get_object_or_404(
            Part.objects.select_for_update(),
            pk=used_part.part_id,
        )

        difference = new_quantity - old_quantity

        if difference > 0:
            # Aumentar el consumo descuenta solo la diferencia.
            if part.stock < difference:
                return Response(
                    {
                        "detail": "Stock insuficiente.",
                        "available_stock": part.stock,
                        "additional_required": difference,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            part.stock -= difference
        else:
            # Disminuir el consumo devuelve la diferencia al stock.
            part.stock += abs(difference)

        used_part.quantity = new_quantity
        used_part.save(update_fields=["quantity"])

        part.save(
            update_fields=[
                "stock",
                "updated_at",
            ]
        )

        correction = OrderPartCorrectionHistory.objects.create(
            order_part=used_part,
            field_name=OrderPartCorrectionHistory.Field.QUANTITY,
            old_value=str(old_quantity),
            new_value=str(new_quantity),
            reason=reason,
            changed_by=request.user,
            changed_by_username=request.user.get_username(),
            changed_by_role=request.user.role,
        )

        return Response(
            self._response_payload(
                used_part=used_part,
                correction=correction,
            ),
            status=status.HTTP_200_OK,
        )

    def _correct_note(
        self,
        request,
        used_part,
        new_note,
        reason,
    ):
        old_note = used_part.note

        if new_note == old_note:
            return Response(
                {
                    "detail": (
                        "La nueva nota debe ser distinta "
                        "de la nota actual."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        used_part.note = new_note
        used_part.save(update_fields=["note"])

        correction = OrderPartCorrectionHistory.objects.create(
            order_part=used_part,
            field_name=OrderPartCorrectionHistory.Field.NOTE,
            old_value=old_note,
            new_value=new_note,
            reason=reason,
            changed_by=request.user,
            changed_by_username=request.user.get_username(),
            changed_by_role=request.user.role,
        )

        return Response(
            self._response_payload(
                used_part=used_part,
                correction=correction,
            ),
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _response_payload(used_part, correction):
        return {
            "used_part": OrderPartSerializer(used_part).data,
            "correction": (
                OrderPartCorrectionHistorySerializer(
                    correction
                ).data
            ),
        }


class OrderPartCorrectionHistoryView(APIView):
    """
    HU-24: historial de correcciones de un uso de repuesto.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id, order_part_id):
        if request.user.role not in {"ADMIN", "TECH"}:
            return Response(
                {
                    "detail": (
                        "No tienes permiso para consultar "
                        "correcciones de repuestos."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        order = get_object_or_404(
            ServiceOrder,
            pk=order_id,
        )

        used_part = get_object_or_404(
            OrderPart,
            pk=order_part_id,
            order=order,
        )

        history = (
            OrderPartCorrectionHistory.objects
            .filter(order_part=used_part)
            .select_related("changed_by")
            .order_by("changed_at", "id")
        )

        return Response(
            OrderPartCorrectionHistorySerializer(
                history,
                many=True,
            ).data
        )
