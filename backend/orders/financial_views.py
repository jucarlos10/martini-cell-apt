
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .financial_serializers import OrderFinancialSerializer
from .financial_services import calculate_order_financials
from .models import OrderFinancial, ServiceOrder


class OrderFinancialView(APIView):
    """
    HU-14: consultar y actualizar las finanzas de una orden.

    ADMIN y TECH pueden consultar.
    Solo ADMIN puede registrar o modificar los valores.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if request.user.role not in {"ADMIN", "TECH"}:
            return Response(
                {
                    "detail": (
                        "No tienes permiso para consultar "
                        "la información financiera."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        order = get_object_or_404(
            ServiceOrder,
            pk=pk,
        )

        return Response(
            calculate_order_financials(order)
        )

    @transaction.atomic
    def patch(self, request, pk):
        if request.user.role != "ADMIN":
            return Response(
                {
                    "detail": (
                        "Solo un administrador puede modificar "
                        "la información financiera."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Bloqueamos la orden para evitar que dos solicitudes
        # creen simultáneamente su registro financiero.
        order = get_object_or_404(
            ServiceOrder.objects.select_for_update(),
            pk=pk,
        )

        financial = OrderFinancial.objects.filter(
            order=order
        ).first()

        serializer = OrderFinancialSerializer(
            financial,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)

        if financial is None:
            serializer.save(
                order=order,
                created_by=request.user,
                updated_by=request.user,
            )
            response_status = status.HTTP_201_CREATED

        else:
            serializer.save(
                updated_by=request.user,
            )
            response_status = status.HTTP_200_OK

        # Devolvemos los valores calculados por Django,
        # no cálculos enviados desde el navegador.
        return Response(
            calculate_order_financials(order),
            status=response_status,
        )