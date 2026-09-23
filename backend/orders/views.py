import mimetypes

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    OrderEvidence,
    OrderTechnicalReport,
    ServiceOrder,
)
from .serializers import (
    OrderEvidenceSerializer,
    OrderTechnicalReportHistorySerializer,
    OrderTechnicalReportSerializer,
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


class OrderTechnicalReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get_order(self, pk):
        return get_object_or_404(
            ServiceOrder,
            pk=pk,
        )

    def can_modify(self, user):
        return user.role in {
            "ADMIN",
            "TECH",
        }

    def get(self, request, pk):
        order = self.get_order(pk)

        report = get_object_or_404(
            OrderTechnicalReport.objects.select_related(
                "order",
                "technician",
                "created_by",
                "updated_by",
            ),
            order=order,
        )

        serializer = OrderTechnicalReportSerializer(
            report
        )

        return Response(serializer.data)

    def post(self, request, pk):
        if not self.can_modify(request.user):
            return Response(
                {
                    "detail": (
                        "No tienes permiso para registrar "
                        "un informe técnico."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        order = self.get_order(pk)

        if OrderTechnicalReport.objects.filter(
            order=order
        ).exists():
            return Response(
                {
                    "detail": (
                        "La orden ya posee un informe técnico."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OrderTechnicalReportSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        report = serializer.save(
            order=order,
            created_by=request.user,
            updated_by=request.user,
        )

        response_serializer = (
            OrderTechnicalReportSerializer(report)
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request, pk):
        if not self.can_modify(request.user):
            return Response(
                {
                    "detail": (
                        "No tienes permiso para modificar "
                        "un informe técnico."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        order = self.get_order(pk)

        report = get_object_or_404(
            OrderTechnicalReport,
            order=order,
        )

        serializer = OrderTechnicalReportSerializer(
            report,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True
        )

        report = serializer.save(
            updated_by=request.user
        )

        response_serializer = (
            OrderTechnicalReportSerializer(report)
        )

        return Response(
            response_serializer.data
        )


class OrderTechnicalReportHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(
            ServiceOrder,
            pk=pk,
        )

        report = get_object_or_404(
            OrderTechnicalReport,
            order=order,
        )

        history = (
            report.history
            .select_related(
                "technician",
                "changed_by",
            )
            .order_by("revision")
        )

        serializer = (
            OrderTechnicalReportHistorySerializer(
                history,
                many=True,
            )
        )

        return Response(serializer.data)