from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers

from .models import OrderWarranty
from .warranty_request_models import (
    WarrantyActionType,
    WarrantyRequest,
    WarrantyRequestHistory,
    WarrantyRequestProposal,
    WarrantyRequestResolution,
)


class WarrantyRequestWriteSerializer(serializers.ModelSerializer):
    """
    HU-22: valida los datos necesarios para registrar
    una solicitud de garantía.
    """

    warranty = serializers.PrimaryKeyRelatedField(
        queryset=OrderWarranty.objects.all(),
    )

    requested_on = serializers.DateField(
        required=False,
        default=timezone.localdate,
    )

    problem_description = serializers.CharField(
        trim_whitespace=True,
    )

    concurrent_open_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    evidence = serializers.ImageField(
        required=False,
        allow_null=True,
    )

    def validate_evidence(self, value):
        if value and value.size > settings.EVIDENCE_MAX_UPLOAD_SIZE:
            raise serializers.ValidationError(
                "La fotografía supera el máximo permitido de 20 MB."
            )
        return value

    class Meta:
        model = WarrantyRequest
        fields = (
            "warranty",
            "requested_on",
            "problem_description",
            "concurrent_open_reason",
            "evidence",
        )

    def validate(self, attrs):
        order = self.context.get("order")
        warranty = attrs.get("warranty")

        if order is None:
            raise serializers.ValidationError(
                "No se pudo determinar la orden de servicio."
            )

        if warranty.order_id != order.pk:
            raise serializers.ValidationError(
                {
                    "warranty": (
                        "La garantía seleccionada no pertenece "
                        "a esta orden."
                    )
                }
            )

        warranty_status = warranty.current_status

        if warranty_status == OrderWarranty.WarrantyStatus.NOT_APPLICABLE:
            raise serializers.ValidationError(
                {
                    "warranty": (
                        "No se puede registrar una solicitud porque "
                        "esta garantía está marcada como no aplicable."
                    )
                }
            )

        if warranty_status == OrderWarranty.WarrantyStatus.NOT_STARTED:
            raise serializers.ValidationError(
                {
                    "warranty": (
                        "No se puede registrar una solicitud porque "
                        "esta garantía todavía no ha comenzado."
                    )
                }
            )

        description = attrs.get("problem_description", "")
        if not description.strip():
            raise serializers.ValidationError(
                {
                    "problem_description": (
                        "Describe el problema reportado por el cliente."
                    )
                }
            )

        open_requests = WarrantyRequest.objects.filter(
            warranty=warranty,
            status__in=WarrantyRequest.OPEN_STATUSES,
        )

        if self.instance is not None:
            open_requests = open_requests.exclude(pk=self.instance.pk)

        if open_requests.exists():
            reason = attrs.get("concurrent_open_reason", "")

            if not reason.strip():
                raise serializers.ValidationError(
                    {
                        "concurrent_open_reason": (
                            "Esta garantía ya tiene una solicitud "
                            "abierta. Indica el motivo para registrar "
                            "otra solicitud."
                        )
                    }
                )

        return attrs


class WarrantyRequestProposalWriteSerializer(serializers.Serializer):
    """
    HU-23: datos que TECH debe registrar al enviar
    o reenviar una propuesta técnica.
    """

    technical_rationale = serializers.CharField(
        trim_whitespace=True,
    )

    action_type = serializers.ChoiceField(
        choices=WarrantyActionType.choices,
    )

    action_description = serializers.CharField(
        trim_whitespace=True,
    )

    def validate_technical_rationale(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "El fundamento técnico es obligatorio."
            )
        return value

    def validate_action_description(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Describe la acción propuesta."
            )
        return value


class WarrantyRequestProposalReadSerializer(serializers.ModelSerializer):
    action_type_display = serializers.CharField(
        source="get_action_type_display",
        read_only=True,
    )

    class Meta:
        model = WarrantyRequestProposal
        fields = (
            "id",
            "request",
            "revision",
            "technical_rationale",
            "action_type",
            "action_type_display",
            "action_description",
            "proposed_by",
            "proposed_by_username",
            "proposed_by_role",
            "proposed_at",
        )


class WarrantyRequestResolutionWriteSerializer(serializers.Serializer):
    """
    HU-23: decisión final que solo ADMIN puede registrar.
    """

    decision = serializers.ChoiceField(
        choices=WarrantyRequestResolution.Decision.choices,
    )

    rationale = serializers.CharField(
        trim_whitespace=True,
    )

    action_type = serializers.ChoiceField(
        choices=WarrantyActionType.choices,
        required=False,
        allow_null=True,
    )

    action_description = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    def validate_rationale(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "El fundamento de la decisión es obligatorio."
            )
        return value

    def validate(self, attrs):
        decision = attrs.get("decision")

        if decision == WarrantyRequestResolution.Decision.ACCEPTED:
            if not attrs.get("action_type"):
                raise serializers.ValidationError(
                    {
                        "action_type": (
                            "Indica la acción realizada o autorizada."
                        )
                    }
                )

            description = attrs.get("action_description", "")
            if not description.strip():
                raise serializers.ValidationError(
                    {
                        "action_description": (
                            "Describe la acción realizada o autorizada."
                        )
                    }
                )

        return attrs


class WarrantyRequestResolutionReadSerializer(serializers.ModelSerializer):
    decision_display = serializers.CharField(
        source="get_decision_display",
        read_only=True,
    )

    action_type_display = serializers.SerializerMethodField()

    class Meta:
        model = WarrantyRequestResolution
        fields = (
            "id",
            "request",
            "decision",
            "decision_display",
            "rationale",
            "action_type",
            "action_type_display",
            "action_description",
            "resolved_by",
            "resolved_by_username",
            "resolved_by_role",
            "resolved_at",
        )

    def get_action_type_display(self, obj):
        if not obj.action_type:
            return None
        return obj.get_action_type_display()


class WarrantyRequestReturnSerializer(serializers.Serializer):
    """
    HU-23: motivo obligatorio cuando ADMIN devuelve
    una propuesta al técnico.
    """

    reason = serializers.CharField(
        trim_whitespace=True,
    )

    def validate_reason(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Indica el motivo de la devolución al técnico."
            )
        return value


class WarrantyRequestAdminNoteSerializer(serializers.Serializer):
    """
    HU-23: observación administrativa posterior.

    No modifica una resolución final ni reabre la solicitud.
    """

    observation = serializers.CharField(
        trim_whitespace=True,
    )

    def validate_observation(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "La observación administrativa es obligatoria."
            )
        return value


class WarrantyRequestReadSerializer(serializers.ModelSerializer):
    """
    Presenta la solicitud para perfiles internos autorizados.

    El nombre y RUT corresponden a la copia histórica tomada
    desde la orden al momento de crear la solicitud.
    """

    warranty_status = serializers.CharField(
        source="warranty_status_at_query",
        read_only=True,
    )

    warranty_type = serializers.CharField(
        source="warranty.warranty_type",
        read_only=True,
    )

    warranty_type_display = serializers.CharField(
        source="warranty.get_warranty_type_display",
        read_only=True,
    )

    coverage_warning = serializers.SerializerMethodField()

    evidence = serializers.SerializerMethodField()
    evidence_download_url = serializers.SerializerMethodField()

    client_name = serializers.CharField(
        source="client_name_snapshot",
        read_only=True,
    )

    client_rut = serializers.CharField(
        source="client_rut_snapshot",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    has_other_open_request = serializers.SerializerMethodField()

    proposals = WarrantyRequestProposalReadSerializer(
        many=True,
        read_only=True,
    )

    resolution = serializers.SerializerMethodField()

    latest_proposal = serializers.SerializerMethodField()

    class Meta:
        model = WarrantyRequest
        fields = (
            "id",
            "order",
            "warranty",
            "warranty_type",
            "warranty_type_display",
            "warranty_status",
            "coverage_warning",
            "requested_on",
            "problem_description",
            "status",
            "status_display",
            "concurrent_open_reason",
            "client_name",
            "client_rut",
            "evidence",
            "evidence_download_url",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
            "has_other_open_request",
            "proposals",
            "latest_proposal",
            "resolution",
        )

    def get_coverage_warning(self, obj):
        if obj.has_expired_warranty:
            return (
                "La cobertura asociada a esta solicitud "
                "se encuentra vencida."
            )

        return None

    def get_evidence(self, obj):
        return bool(obj.evidence)

    def get_evidence_download_url(self, obj):
        if not obj.evidence:
            return None
        return reverse(
            "warranty-request-evidence",
            kwargs={"pk": obj.order_id, "request_id": obj.pk},
        )

    def get_has_other_open_request(self, obj):
        return (
            WarrantyRequest.objects
            .filter(
                warranty_id=obj.warranty_id,
                status__in=WarrantyRequest.OPEN_STATUSES,
            )
            .exclude(pk=obj.pk)
            .exists()
        )

    def get_latest_proposal(self, obj):
        proposal = obj.proposals.order_by("-revision", "-id").first()
        if proposal is None:
            return None

        return WarrantyRequestProposalReadSerializer(proposal).data

    def get_resolution(self, obj):
        try:
            resolution = obj.resolution
        except WarrantyRequestResolution.DoesNotExist:
            return None

        return WarrantyRequestResolutionReadSerializer(resolution).data


class WarrantyRequestHistorySerializer(serializers.ModelSerializer):
    """
    Presenta el historial interno de una solicitud de garantía.
    """

    action_display = serializers.CharField(
        source="get_action_display",
        read_only=True,
    )

    from_status_display = serializers.SerializerMethodField()
    to_status_display = serializers.SerializerMethodField()
    decision_display = serializers.SerializerMethodField()

    class Meta:
        model = WarrantyRequestHistory
        fields = (
            "id",
            "request",
            "revision",
            "action",
            "action_display",
            "from_status",
            "from_status_display",
            "to_status",
            "to_status_display",
            "observation",
            "decision",
            "decision_display",
            "changed_by",
            "changed_by_username",
            "changed_by_role",
            "changed_at",
        )

    def get_from_status_display(self, obj):
        if not obj.from_status:
            return None

        return dict(WarrantyRequest.Status.choices).get(
            obj.from_status,
            obj.from_status,
        )

    def get_to_status_display(self, obj):
        return dict(WarrantyRequest.Status.choices).get(
            obj.to_status,
            obj.to_status,
        )

    def get_decision_display(self, obj):
        if not obj.decision:
            return None

        return dict(
            WarrantyRequestResolution.Decision.choices
        ).get(
            obj.decision,
            obj.decision,
        )
