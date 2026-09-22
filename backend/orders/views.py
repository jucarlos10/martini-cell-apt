from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated

from .models import ServiceOrder
from .serializers import ServiceOrderSerializer


class ServiceOrderListCreateView(ListCreateAPIView):
    queryset = (
        ServiceOrder.objects
        .select_related("client", "equipment", "created_by")
        .all()
        .order_by("-received_at")
    )
    serializer_class = ServiceOrderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user
        )


class ServiceOrderDetailView(RetrieveUpdateAPIView):
    queryset = (
        ServiceOrder.objects
        .select_related("client", "equipment", "created_by")
        .all()
    )
    serializer_class = ServiceOrderSerializer
    permission_classes = [IsAuthenticated]