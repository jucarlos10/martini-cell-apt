from rest_framework import serializers

from .loyalty import loyalty_summary
from .models import Client, ClientChangeHistory, ClientLoyaltyReview
from .validators import normalize_rut, validate_rut


class ClientSerializer(serializers.ModelSerializer):
    rut = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )
    updated_by_username = serializers.CharField(
        source="updated_by.username",
        read_only=True,
    )
    loyalty_order_count = serializers.SerializerMethodField()
    loyalty_pending_milestone = serializers.SerializerMethodField()
    loyalty_next_milestone = serializers.SerializerMethodField()
    loyalty_cycle_target = serializers.SerializerMethodField()
    loyalty_cycle_visits = serializers.SerializerMethodField()

    def get_loyalty_order_count(self, obj):
        return loyalty_summary(obj)["loyalty_order_count"]

    def get_loyalty_pending_milestone(self, obj):
        return loyalty_summary(obj)["loyalty_pending_milestone"]

    def get_loyalty_next_milestone(self, obj):
        return loyalty_summary(obj)["loyalty_next_milestone"]

    def get_loyalty_cycle_target(self, obj):
        return loyalty_summary(obj)["loyalty_cycle_target"]

    def get_loyalty_cycle_visits(self, obj):
        return loyalty_summary(obj)["loyalty_cycle_visits"]

    class Meta:
        model = Client
        fields = (
            "id",
            "rut",
            "name",
            "phone",
            "email",
            "is_active",
            "created_at",
            "updated_at",
            "created_by_username",
            "updated_by_username",
            "loyalty_order_count",
            "loyalty_pending_milestone",
            "loyalty_next_milestone",
            "loyalty_cycle_target",
            "loyalty_cycle_visits",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "created_by_username",
            "updated_by_username",
            "loyalty_order_count",
            "loyalty_pending_milestone",
            "loyalty_next_milestone",
            "loyalty_cycle_target",
            "loyalty_cycle_visits",
        )

    def validate_rut(self, value):
        rut = normalize_rut(value) or None

        if rut is None:
            return None

        validate_rut(rut)

        queryset = Client.objects.filter(rut=rut)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "Ya existe un cliente registrado con este RUT."
            )

        return rut


class ClientChangeHistorySerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(
        source="changed_by.username",
        read_only=True,
    )

    class Meta:
        model = ClientChangeHistory
        fields = (
            "id",
            "changed_at",
            "changed_by_username",
            "changes",
        )
        read_only_fields = fields


class ClientLoyaltyReviewSerializer(serializers.ModelSerializer):
    reviewed_by_username = serializers.CharField(
        source="reviewed_by.username", read_only=True
    )

    class Meta:
        model = ClientLoyaltyReview
        fields = (
            "milestone", "cycle_target", "benefit_applied",
            "reviewed_by_username", "reviewed_at"
        )
        read_only_fields = fields
