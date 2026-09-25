from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import OrderWarranty
from .warranty_serializers import OrderWarrantyReadSerializer
from .warranty_views import require_warranty_permission


class OrderWarrantySummarySerializer(OrderWarrantyReadSerializer):
    """
    Reutiliza los datos de HU-15 y agrega el código de la orden
    para mostrarlo en el listado general de garantías.
    """

    tracking_code = serializers.CharField(
        source="order.tracking_code",
        read_only=True,
    )

    class Meta(OrderWarrantyReadSerializer.Meta):
        fields = OrderWarrantyReadSerializer.Meta.fields + (
            "tracking_code",
        )


class OrderWarrantySummaryListView(APIView):
    """
    Consulta de todas las garantías registradas.
    Solo disponible para ADMIN y TECH.
    No crea ni modifica registros.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = require_warranty_permission(request.user)

        if denied is not None:
            return denied

        warranties = (
            OrderWarranty.objects
            .select_related(
                "order",
                "order_part__part",
                "order_part__supplier",
            )
            .order_by("-updated_at", "-id")
        )

        serializer = OrderWarrantySummarySerializer(
            warranties,
            many=True,
        )

        return Response(serializer.data)