
from django.db import transaction
from django.db.models.deletion import ProtectedError, RestrictedError
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdminRole
from orders.models import ServiceOrder
from orders.serializers import ServiceOrderHistorySerializer

from .models import Equipment
from .serializers import EquipmentSerializer


class EquipmentListCreateView(ListCreateAPIView):
    queryset = (
        Equipment.objects
        .select_related("client")
        .all()
        .order_by("-created_at")
    )
    serializer_class = EquipmentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )


class EquipmentDetailView(RetrieveUpdateDestroyAPIView):
    queryset = (
        Equipment.objects
        .select_related("client")
        .all()
    )
    serializer_class = EquipmentSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAdminRole()]

        return super().get_permissions()

    def perform_update(self, serializer):
        serializer.save(
            updated_by=self.request.user
        )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        equipment = get_object_or_404(
            self.get_queryset().select_for_update(),
            pk=kwargs["pk"],
        )
        self.check_object_permissions(request, equipment)

        if equipment.service_orders.exists():
            return Response(
                {
                    "detail": (
                        "No se puede eliminar este equipo porque "
                        "tiene órdenes de servicio asociadas. "
                        "Puedes desactivarlo para conservar "
                        "su historial técnico."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            equipment.delete()
        except (ProtectedError, RestrictedError):
            return Response(
                {
                    "detail": (
                        "No se puede eliminar este equipo porque "
                        "existen registros relacionados que deben "
                        "conservarse."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class EquipmentHistoryListView(ListAPIView):
    serializer_class = ServiceOrderHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        equipment = get_object_or_404(
            Equipment,
            pk=self.kwargs["pk"],
        )

        return (
            ServiceOrder.objects
            .filter(equipment=equipment)
            .select_related(
                "client",
                "equipment",
                "created_by",
                "technical_report__technician",
            )
            .order_by("received_at")
        )