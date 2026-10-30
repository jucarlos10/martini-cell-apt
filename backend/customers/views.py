from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError, RestrictedError
from django.shortcuts import get_object_or_404

from rest_framework import serializers, status
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import (
    CanManageOperationalRecord,
    IsAdminRole,
    IsAdminOrTechRole,
)

from .loyalty import loyalty_summary, with_loyalty_counts
from .models import Client, ClientChangeHistory, ClientLoyaltyReview
from .serializers import (
    ClientChangeHistorySerializer, ClientLoyaltyReviewSerializer,
    ClientSerializer,
)
from .validators import normalize_rut


class ClientListCreateView(ListCreateAPIView):
    serializer_class = ClientSerializer
    permission_classes = [
        IsAuthenticated,
        CanManageOperationalRecord,
    ]

    def get_queryset(self):
        queryset = with_loyalty_counts().order_by("name")
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
    queryset = with_loyalty_counts()
    serializer_class = ClientSerializer
    permission_classes = [
        IsAuthenticated,
        CanManageOperationalRecord,
    ]

    @transaction.atomic
    def perform_update(self, serializer):
        # Bloquear la fila y usar su estado actual para que el cambio
        # y el historial se confirmen juntos, incluso ante ediciones
        # simultáneas del mismo cliente.
        client = Client.objects.select_for_update().get(
            pk=serializer.instance.pk,
        )
        serializer.instance = client

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
            Client.objects.select_for_update(),
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
    permission_classes = [
        IsAuthenticated,
        IsAdminOrTechRole,
    ]

    def get_queryset(self):
        return ClientChangeHistory.objects.filter(
            client_id=self.kwargs["pk"]
        ).order_by("-changed_at")


class ClientLoyaltyAlertsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        clients = with_loyalty_counts(
            Client.objects.filter(rut__isnull=False, is_active=True)
        ).filter(loyalty_order_count__gte=6).order_by("name")

        return Response(
            ClientSerializer(
                [client for client in clients if loyalty_summary(client)[
                    "loyalty_pending_milestone"
                ]], many=True
            ).data
        )


class LoyaltyBenefitSerializer(serializers.Serializer):
    benefit_applied = serializers.CharField(
        max_length=1000, trim_whitespace=True
    )


class ClientLoyaltyReviewView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        reviews = client.loyalty_reviews.select_related("reviewed_by")
        return Response(ClientLoyaltyReviewSerializer(reviews, many=True).data)

    @transaction.atomic
    def post(self, request, pk):
        form = LoyaltyBenefitSerializer(data=request.data)
        form.is_valid(raise_exception=True)

        client = get_object_or_404(Client.objects.select_for_update(), pk=pk)
        summary = loyalty_summary(client)
        pending = summary["loyalty_pending_milestone"]
        if pending is None:
            return Response(
                {"detail": "No hay un hito pendiente para este cliente."},
                status=status.HTTP_409_CONFLICT,
            )

        review = ClientLoyaltyReview.objects.create(
            client=client,
            milestone=pending,
            cycle_target=summary["loyalty_cycle_target"],
            benefit_applied=form.validated_data["benefit_applied"],
            reviewed_by=request.user,
        )
        return Response(
            ClientLoyaltyReviewSerializer(review).data,
            status=status.HTTP_201_CREATED,
        )
