import mimetypes

from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
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
    OrderStatusHistory,
    OrderTechnicalReport,
    ServiceOrder,
)
from .serializers import (
    OrderEvidenceSerializer,
    OrderTechnicalReportHistorySerializer,
    OrderTechnicalReportSerializer,
    ServiceOrderSerializer,
)


# Transiciones permitidas para la primera versión de HU-10.
# Conservamos los diez estados existentes en el frontend.
STATUS_TRANSITIONS = {
    ServiceOrder.Status.RECEIVED: (
        ServiceOrder.Status.DIAGNOSIS,
    ),
    ServiceOrder.Status.DIAGNOSIS: (
        ServiceOrder.Status.AUTHORIZATION,
        ServiceOrder.Status.REJECTED,
    ),
    ServiceOrder.Status.AUTHORIZATION: (
        ServiceOrder.Status.PART,
        ServiceOrder.Status.REPAIR,
        ServiceOrder.Status.REJECTED,
    ),
    ServiceOrder.Status.PART: (
        ServiceOrder.Status.REPAIR,
        ServiceOrder.Status.REJECTED,
    ),
    ServiceOrder.Status.REPAIR: (
        ServiceOrder.Status.PART,
        ServiceOrder.Status.TESTING,
    ),
    ServiceOrder.Status.TESTING: (
        ServiceOrder.Status.REPAIR,
        ServiceOrder.Status.READY,
    ),
    ServiceOrder.Status.READY: (
        ServiceOrder.Status.DELIVERED,
    ),
    ServiceOrder.Status.REJECTED: (
        ServiceOrder.Status.READY,
    ),
    ServiceOrder.Status.DELIVERED: (
        ServiceOrder.Status.CLOSED,
    ),
    ServiceOrder.Status.CLOSED: (),
}


class OrderStatusChangeSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=ServiceOrder.Status.choices,
    )

    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
    )


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    from_status_display = serializers.CharField(
        source="get_from_status_display",
        read_only=True,
    )

    to_status_display = serializers.CharField(
        source="get_to_status_display",
        read_only=True,
    )

    changed_by_username = serializers.SerializerMethodField()

    class Meta:
        model = OrderStatusHistory
        fields = (
            "id",
            "from_status",
            "from_status_display",
            "to_status",
            "to_status_display",
            "note",
            "changed_by",
            "changed_by_username",
            "changed_at",
        )

        read_only_fields = fields

    def get_changed_by_username(self, obj):
        if not obj.changed_by_id:
            return None

        return obj.changed_by.username


def get_order_status_data(order):
    allowed = STATUS_TRANSITIONS.get(
        order.status,
        (),
    )

    return {
        "order_id": order.id,
        "tracking_code": order.tracking_code,
        "status": order.status,
        "status_display": order.get_status_display(),
        "allowed_transitions": [
            {
                "status": next_status,
                "status_display": ServiceOrder.Status(
                    next_status
                ).label,
            }
            for next_status in allowed
        ],
    }


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


class OrderStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(
            ServiceOrder,
            pk=pk,
        )

        return Response(
            get_order_status_data(order)
        )

    @transaction.atomic
    def patch(self, request, pk):
        if request.user.role not in {"ADMIN", "TECH"}:
            return Response(
                {
                    "detail": (
                        "No tienes permiso para cambiar "
                        "el estado de una orden."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OrderStatusChangeSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        new_status = serializer.validated_data["status"]
        note = serializer.validated_data.get(
            "note",
            "",
        )

        # Bloqueamos la orden durante la transición para evitar
        # que dos solicitudes cambien su estado simultáneamente.
        order = get_object_or_404(
            ServiceOrder.objects.select_for_update(),
            pk=pk,
        )

        previous_status = order.status

        allowed = STATUS_TRANSITIONS.get(
            previous_status,
            (),
        )

        if new_status not in allowed:
            return Response(
                {
                    "detail": (
                        "No está permitido cambiar el estado "
                        f"de {order.get_status_display()} "
                        f"a {ServiceOrder.Status(new_status).label}."
                    ),
                    "current_status": previous_status,
                    "allowed_transitions": list(allowed),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = new_status
        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        OrderStatusHistory.objects.create(
            order=order,
            from_status=previous_status,
            to_status=new_status,
            note=note,
            changed_by=request.user,
        )

        return Response(
            get_order_status_data(order)
        )


class OrderStatusHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(
            ServiceOrder,
            pk=pk,
        )

        history = (
            OrderStatusHistory.objects
            .filter(order=order)
            .select_related("changed_by")
            .order_by("changed_at", "id")
        )

        serializer = OrderStatusHistorySerializer(
            history,
            many=True,
        )

        return Response(serializer.data)


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

    @transaction.atomic
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

        order = get_object_or_404(
            ServiceOrder.objects.select_for_update(),
            pk=pk,
        )

        if order.status in {
            ServiceOrder.Status.DELIVERED,
            ServiceOrder.Status.CLOSED,
        }:
            return Response(
                {
                    "detail": (
                        "No se puede registrar un informe técnico "
                        "en una orden entregada o cerrada."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

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

    @transaction.atomic
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

        order = get_object_or_404(
            ServiceOrder.objects.select_for_update(),
            pk=pk,
        )

        if order.status in {
            ServiceOrder.Status.DELIVERED,
            ServiceOrder.Status.CLOSED,
        }:
            return Response(
                {
                    "detail": (
                        "No se puede modificar un informe técnico "
                        "en una orden entregada o cerrada."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

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