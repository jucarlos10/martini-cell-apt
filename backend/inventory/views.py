
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import (
    BasePermission,
    IsAuthenticated,
    SAFE_METHODS,
)

from .models import Part, Supplier
from .serializers import PartSerializer, SupplierSerializer


class CanManageInventory(BasePermission):
    """
    Los usuarios autenticados pueden consultar el inventario.
    Solo ADMIN y TECH pueden crear o modificar registros.
    """

    message = "No tienes permiso para modificar el inventario."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        return request.user.role in {"ADMIN", "TECH"}


class SupplierListCreateView(ListCreateAPIView):
    queryset = Supplier.objects.all().order_by("name", "id")
    serializer_class = SupplierSerializer
    permission_classes = [
        IsAuthenticated,
        CanManageInventory,
    ]


class SupplierDetailView(RetrieveUpdateAPIView):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [
        IsAuthenticated,
        CanManageInventory,
    ]


class PartListCreateView(ListCreateAPIView):
    queryset = (
        Part.objects
        .select_related("supplier")
        .all()
        .order_by("name", "id")
    )
    serializer_class = PartSerializer
    permission_classes = [
        IsAuthenticated,
        CanManageInventory,
    ]


class PartDetailView(RetrieveUpdateAPIView):
    queryset = (
        Part.objects
        .select_related("supplier")
        .all()
    )
    serializer_class = PartSerializer
    permission_classes = [
        IsAuthenticated,
        CanManageInventory,
    ]