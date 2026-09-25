from rest_framework import serializers

from .models import OrderViabilityAssessment


class OrderViabilityAssessmentSerializer(
    serializers.ModelSerializer
):
    difficulty_display = serializers.CharField(
        source="get_difficulty_display",
        read_only=True,
    )

    warranty_risk_display = serializers.CharField(
        source="get_warranty_risk_display",
        read_only=True,
    )

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    updated_by_username = serializers.CharField(
        source="updated_by.username",
        read_only=True,
    )

    class Meta:
        model = OrderViabilityAssessment

        fields = (
            "id",
            "order",
            "difficulty",
            "difficulty_display",
            "warranty_risk",
            "warranty_risk_display",
            "notes",
            "created_by_username",
            "updated_by_username",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "order",
            "difficulty_display",
            "warranty_risk_display",
            "created_by_username",
            "updated_by_username",
            "created_at",
            "updated_at",
        )