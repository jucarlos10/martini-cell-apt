from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    OrderViabilityAssessment,
    ServiceOrder,
)
from .viability_serializers import (
    OrderViabilityAssessmentSerializer,
)
from .viability_services import calculate_viability_index


class OrderViabilityView(APIView):
    """
    HU-16: consulta y registro de la evaluación
    utilizada por el índice de viabilidad.

    ADMIN y TECH pueden consultar y registrar
    la evaluación.

    El índice se calcula en el backend mediante
    reglas documentadas y datos existentes.
    """

    permission_classes = [IsAuthenticated]

    def has_permission_for_viability(self, user):
        return user.role in {
            "ADMIN",
            "TECH",
        }

    def get(self, request, pk):
        if not self.has_permission_for_viability(
            request.user
        ):
            return Response(
                {
                    "detail": (
                        "No tienes permiso para consultar "
                        "el índice de viabilidad."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        order = get_object_or_404(
            ServiceOrder,
            pk=pk,
        )

        result = calculate_viability_index(
            order
        )

        return Response(result)

    @transaction.atomic
    def patch(self, request, pk):
        if not self.has_permission_for_viability(
            request.user
        ):
            return Response(
                {
                    "detail": (
                        "No tienes permiso para registrar "
                        "la evaluación de viabilidad."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Bloqueamos la orden durante el registro para
        # evitar actualizaciones simultáneas.
        order = get_object_or_404(
            ServiceOrder.objects.select_for_update(),
            pk=pk,
        )

        assessment = (
            OrderViabilityAssessment.objects
            .select_for_update()
            .filter(order=order)
            .first()
        )

        is_creation = assessment is None

        serializer = OrderViabilityAssessmentSerializer(
            assessment,
            data=request.data,
            partial=not is_creation,
        )

        serializer.is_valid(
            raise_exception=True
        )

        if is_creation:
            serializer.save(
                order=order,
                created_by=request.user,
                updated_by=request.user,
            )

            response_status = (
                status.HTTP_201_CREATED
            )

        else:
            serializer.save(
                updated_by=request.user,
            )

            response_status = (
                status.HTTP_200_OK
            )

        # El resultado siempre vuelve a calcularse desde
        # el backend después de guardar la evaluación.
        result = calculate_viability_index(
            order
        )

        return Response(
            result,
            status=response_status,
        )