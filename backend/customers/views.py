from django.db.models import Q
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated

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


class ClientDetailView(RetrieveUpdateAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]

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


class ClientChangeHistoryListView(ListAPIView):
    serializer_class = ClientChangeHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ClientChangeHistory.objects.filter(
            client_id=self.kwargs["pk"]
        ).order_by("-changed_at")