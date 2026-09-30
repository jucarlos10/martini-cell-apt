from django.utils import timezone
from rest_framework import serializers

from .models import OrderWarranty
from .warranty_request_models import (
    WarrantyRequest,
    WarrantyRequestHistory,
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
            status=WarrantyRequest.Status.PENDING,
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
                            "pendiente. Indica el motivo para registrar "
                            "otra solicitud."
                        )
                    }
                )

        return attrs


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
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
            "has_other_open_request",
        )

    def get_coverage_warning(self, obj):
        if obj.has_expired_warranty:
            return (
                "La cobertura asociada a esta solicitud "
                "se encuentra vencida."
            )

        return None

    def get_has_other_open_request(self, obj):
        return (
            WarrantyRequest.objects
            .filter(
                warranty_id=obj.warranty_id,
                status=WarrantyRequest.Status.PENDING,
            )
            .exclude(pk=obj.pk)
            .exists()
        )


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
            "changed_by",
            "changed_by_username",
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
