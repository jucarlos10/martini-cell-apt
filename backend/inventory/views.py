
from django.db import transaction
from django.db.models.deletion import ProtectedError, RestrictedError
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import (
    BasePermission,
    IsAuthenticated,
    SAFE_METHODS,
)
from rest_framework.response import Response

from accounts.permissions import IsAdminRole

from .models import Part, Supplier
from .serializers import PartSerializer, SupplierSerializer


class CanManageInventory(BasePermission):
    """
    Los usuarios autenticados pueden consultar el inventario.
    Solo ADMIN y TECH pueden crear o modificar registros.
    La eliminación se reserva exclusivamente para ADMIN.
    """

    message = "No tienes permiso para modificar el inventario."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        if request.method == "DELETE":
            return request.user.role == "ADMIN"

        return request.user.role in {"ADMIN", "TECH"}


class SupplierListCreateView(ListCreateAPIView):
    queryset = Supplier.objects.all().order_by("name", "id")
    serializer_class = SupplierSerializer
    permission_classes = [
        IsAuthenticated,
        CanManageInventory,
    ]


class SupplierDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [
        IsAuthenticated,
        CanManageInventory,
    ]

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAuthenticated(), IsAdminRole()]

        return super().get_permissions()

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        supplier = get_object_or_404(
            self.get_queryset().select_for_update(),
            pk=kwargs["pk"],
        )
        self.check_object_permissions(request, supplier)

        if supplier.parts.exists():
            return Response(
                {
                    "detail": (
                        "No se puede eliminar este proveedor porque "
                        "tiene repuestos asociados. Puedes desactivarlo "
                        "para conservar sus registros."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        if supplier.order_part_usages.exists():
            return Response(
                {
                    "detail": (
                        "No se puede eliminar este proveedor porque "
                        "aparece en el historial de repuestos utilizados "
                        "en órdenes de servicio."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            supplier.delete()
        except (ProtectedError, RestrictedError):
            return Response(
                {
                    "detail": (
                        "No se puede eliminar este proveedor porque "
                        "existen registros relacionados que deben "
                        "conservarse."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


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


class PartDetailView(RetrieveUpdateDestroyAPIView):
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

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAuthenticated(), IsAdminRole()]

        return super().get_permissions()

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        part = get_object_or_404(
            self.get_queryset().select_for_update(),
            pk=kwargs["pk"],
        )
        self.check_object_permissions(request, part)

        if part.order_usages.exists():
            return Response(
                {
                    "detail": (
                        "No se puede eliminar este repuesto porque "
                        "fue utilizado en una o más órdenes de servicio. "
                        "Puedes desactivarlo para conservar su historial."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            part.delete()
        except (ProtectedError, RestrictedError):
            return Response(
                {
                    "detail": (
                        "No se puede eliminar este repuesto porque "
                        "existen registros relacionados que deben "
                        "conservarse."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)