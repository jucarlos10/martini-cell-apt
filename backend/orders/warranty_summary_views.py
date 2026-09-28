import re

from django.db.models import Q
from django.utils import timezone

from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from customers.validators import normalize_rut

from .models import OrderWarranty
from .warranty_serializers import OrderWarrantyReadSerializer
from .warranty_views import require_warranty_permission


class OrderWarrantySummarySerializer(OrderWarrantyReadSerializer):
    """
    Reutiliza los datos de HU-15 y agrega el código de la orden
    para mostrarlo en el listado general de garantías.

    Los datos personales del cliente se utilizan únicamente para
    realizar búsquedas y no forman parte de la respuesta.
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
    HU-33: consulta y filtrado de garantías registradas.

    Parámetros opcionales:
    - q: código de orden, nombre del cliente o RUT.
    - status: ACTIVE, EXPIRED, NOT_STARTED o NOT_APPLICABLE.
    - type: SERVICE o PART.

    Solo disponible para ADMIN y TECH.
    No crea ni modifica registros.
    """

    permission_classes = [IsAuthenticated]

    VALID_STATUSES = {
        OrderWarranty.WarrantyStatus.ACTIVE,
        OrderWarranty.WarrantyStatus.EXPIRED,
        OrderWarranty.WarrantyStatus.NOT_STARTED,
        OrderWarranty.WarrantyStatus.NOT_APPLICABLE,
    }

    VALID_TYPES = {
        OrderWarranty.WarrantyType.SERVICE,
        OrderWarranty.WarrantyType.PART,
    }

    def get(self, request):
        denied = require_warranty_permission(request.user)

        if denied is not None:
            return denied

        warranties = (
            OrderWarranty.objects
            .select_related(
                "order",
                "order__client",
                "order_part__part",
                "order_part__supplier",
            )
            .order_by("-updated_at", "-id")
        )

        search_term = request.query_params.get("q", "").strip()
        warranty_status = (
            request.query_params.get("status", "")
            .strip()
            .upper()
        )
        warranty_type = (
            request.query_params.get("type", "")
            .strip()
            .upper()
        )

        if search_term:
            search_query = (
                Q(order__tracking_code__icontains=search_term)
                | Q(order__client__name__icontains=search_term)
            )

            # Solo se interpreta como posible RUT cuando el texto
            # contiene caracteres propios de un RUT chileno.
            if re.fullmatch(
                r"[0-9kK.\-\s]+",
                search_term,
            ):
                normalized_search_rut = normalize_rut(search_term)

                if normalized_search_rut:
                    search_query |= Q(
                        order__client__rut__icontains=(
                            normalized_search_rut
                        )
                    )

            warranties = warranties.filter(search_query)

        if warranty_type:
            if warranty_type not in self.VALID_TYPES:
                return Response(
                    {
                        "detail": (
                            "Tipo de garantía no válido. "
                            "Utiliza SERVICE o PART."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            warranties = warranties.filter(
                warranty_type=warranty_type
            )

        if warranty_status:
            if warranty_status not in self.VALID_STATUSES:
                return Response(
                    {
                        "detail": (
                            "Estado de garantía no válido."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            today = timezone.localdate()

            if (
                warranty_status
                == OrderWarranty.WarrantyStatus.NOT_APPLICABLE
            ):
                warranties = warranties.filter(
                    is_applicable=False
                )

            elif (
                warranty_status
                == OrderWarranty.WarrantyStatus.NOT_STARTED
            ):
                warranties = warranties.filter(
                    is_applicable=True,
                    starts_on__gt=today,
                )

            elif (
                warranty_status
                == OrderWarranty.WarrantyStatus.ACTIVE
            ):
                warranties = warranties.filter(
                    is_applicable=True,
                    starts_on__lte=today,
                    ends_on__gte=today,
                )

            elif (
                warranty_status
                == OrderWarranty.WarrantyStatus.EXPIRED
            ):
                warranties = warranties.filter(
                    is_applicable=True,
                    ends_on__lt=today,
                )

        serializer = OrderWarrantySummarySerializer(
            warranties,
            many=True,
        )

        return Response(serializer.data)