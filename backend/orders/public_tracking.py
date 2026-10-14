import re

from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .models import OrderStatusHistory, ServiceOrder


class PublicTrackingThrottle(AnonRateThrottle):
    scope = "public_tracking"
    rate = "20/hour"


class PublicStatusHistorySerializer(serializers.ModelSerializer):
    status = serializers.CharField(
        source="to_status",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_to_status_display",
        read_only=True,
    )

    class Meta:
        model = OrderStatusHistory
        fields = (
            "status",
            "status_display",
            "changed_at",
        )
        read_only_fields = fields


class PublicOrderStatusSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = ServiceOrder
        fields = (
            "tracking_code",
            "status",
            "status_display",
            "updated_at",
        )
        read_only_fields = fields


class PublicOrderStatusView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [PublicTrackingThrottle]

    def get(self, request, tracking_code):
        error_message = "No se encontró una orden con ese código."

        if not re.fullmatch(r"MC-[0-9A-F]{12}", tracking_code):
            raise NotFound(error_message)

        order = ServiceOrder.objects.filter(
            tracking_code=tracking_code,
        ).first()

        if order is None:
            raise NotFound(error_message)

        history = (
            OrderStatusHistory.objects
            .filter(order=order)
            .order_by("changed_at", "id")
        )

        order_serializer = PublicOrderStatusSerializer(order)
        history_serializer = PublicStatusHistorySerializer(
            history,
            many=True,
        )

        response_data = dict(order_serializer.data)
        response_data["history"] = history_serializer.data

        return Response(response_data)