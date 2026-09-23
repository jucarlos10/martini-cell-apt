from django.shortcuts import get_object_or_404
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated

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


class EquipmentDetailView(RetrieveUpdateAPIView):
    queryset = (
        Equipment.objects
        .select_related("client")
        .all()
    )
    serializer_class = EquipmentSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(
            updated_by=self.request.user
        )


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
            )
            .order_by("received_at")
        )