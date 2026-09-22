from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from .models import Equipment
from .serializers import EquipmentSerializer


class EquipmentListCreateView(ListCreateAPIView):
    queryset = Equipment.objects.select_related("client").all().order_by("-created_at")
    serializer_class = EquipmentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )


class EquipmentDetailView(RetrieveUpdateAPIView):
    queryset = Equipment.objects.select_related("client").all()
    serializer_class = EquipmentSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(
            updated_by=self.request.user
        )