import mimetypes

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .models import OrderEvidence, ServiceOrder
from .serializers import (
    OrderEvidenceSerializer,
    ServiceOrderSerializer,
)


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


class OrderEvidenceListCreateView(ListCreateAPIView):
    serializer_class = OrderEvidenceSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_order(self):
        return get_object_or_404(
            ServiceOrder,
            pk=self.kwargs["pk"],
        )

    def get_queryset(self):
        order = self.get_order()

        return (
            OrderEvidence.objects
            .filter(order=order)
            .select_related("uploaded_by", "order")
            .order_by("created_at")
        )

    def perform_create(self, serializer):
        serializer.save(
            order=self.get_order(),
            uploaded_by=self.request.user,
        )


class OrderEvidenceDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, evidence_id):
        evidence = get_object_or_404(
            OrderEvidence,
            pk=evidence_id,
            order_id=pk,
        )

        evidence.image.open("rb")

        content_type, _ = mimetypes.guess_type(
            evidence.image.name
        )

        response = FileResponse(
            evidence.image,
            content_type=content_type or "application/octet-stream",
        )

        response["Content-Disposition"] = (
            f'inline; filename="evidence-{evidence.id}"'
        )

        return response