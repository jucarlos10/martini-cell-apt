import re

from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .models import ServiceOrder


class PublicTrackingThrottle(AnonRateThrottle):
    scope = "public_tracking"
    rate = "20/hour"


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

        serializer = PublicOrderStatusSerializer(order)

        return Response(serializer.data)