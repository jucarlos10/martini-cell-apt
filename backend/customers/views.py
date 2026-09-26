
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError, RestrictedError
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdminRole

from .models import Client, ClientChangeHistory
from .serializers import ClientChangeHistorySerializer, ClientSerializer
from .validators import normalize_rut


class ClientListCreateView(ListCreateAPIView):
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Client.objects.all().order_by("name")
        search = self.request.query_params.get("search", "").strip()

        if not search:
            return queryset

        normalized_rut = normalize_rut(search)

        filters = (
            Q(name__icontains=search)
            | Q(phone__icontains=search)
            | Q(email__icontains=search)
        )

        if normalized_rut:
            filters |= Q(rut__icontains=normalized_rut)

        return queryset.filter(filters)

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )


class ClientDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAdminRole()]

        return super().get_permissions()

    def perform_update(self, serializer):
        client = self.get_object()

        fields_to_track = (
            "rut",
            "name",
            "phone",
            "email",
            "is_active",
        )

        old_values = {
            field: getattr(client, field)
            for field in fields_to_track
        }

        updated_client = serializer.save(
            updated_by=self.request.user
        )

        changes = {}

        for field in fields_to_track:
            old_value = old_values[field]
            new_value = getattr(updated_client, field)

            if old_value != new_value:
                changes[field] = {
                    "from": old_value,
                    "to": new_value,
                }

        if changes:
            ClientChangeHistory.objects.create(
                client=updated_client,
                changed_by=self.request.user,
                changes=changes,
            )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        client = get_object_or_404(
            self.get_queryset().select_for_update(),
            pk=kwargs["pk"],
        )
        self.check_object_permissions(request, client)

        if client.equipment.exists():
            return Response(
                {
                    "detail": (
                        "No se puede eliminar este cliente porque "
                        "tiene equipos asociados. Puedes desactivarlo "
                        "para conservar sus registros."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        if client.service_orders.exists():
            return Response(
                {
                    "detail": (
                        "No se puede eliminar este cliente porque "
                        "tiene órdenes de servicio asociadas."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        if client.change_history.exists():
            return Response(
                {
                    "detail": (
                        "No se puede eliminar este cliente porque "
                        "tiene un historial de modificaciones. "
                        "Puedes desactivarlo para conservar "
                        "la trazabilidad."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            client.delete()
        except (ProtectedError, RestrictedError):
            return Response(
                {
                    "detail": (
                        "No se puede eliminar este cliente porque "
                        "existen registros relacionados que deben "
                        "conservarse."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class ClientChangeHistoryListView(ListAPIView):
    serializer_class = ClientChangeHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ClientChangeHistory.objects.filter(
            client_id=self.kwargs["pk"]
        ).order_by("-changed_at")