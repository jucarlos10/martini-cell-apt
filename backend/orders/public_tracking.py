import re
from hashlib import sha256

from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle
from rest_framework.views import APIView

from .models import OrderStatusHistory, ServiceOrder


class PublicTrackingThrottle(AnonRateThrottle):
    scope = "public_tracking"
    rate = "20/hour"


class PublicChatReadThrottle(SimpleRateThrottle):
    scope = "public_chat_read"
    # La pantalla consulta cada cinco segundos mientras el chat está abierto.
    rate = "3600/hour"

    def get_cache_key(self, request, view):
        if request.method != "GET":
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class PublicChatWriteThrottle(SimpleRateThrottle):
    scope = "public_chat_write"
    rate = "20/hour"

    def get_cache_key(self, request, view):
        if request.method != "POST":
            return None
        # Una conversación comparte el límite aunque lleguen envíos desde
        # diferentes IP. No guardar el código de seguimiento en la clave.
        code = (view.kwargs.get("tracking_code") or "").strip().upper()
        return self.cache_format % {
            "scope": self.scope,
            "ident": sha256(code.encode("utf-8")).hexdigest(),
        }


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
