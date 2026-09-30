import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from .models import OrderWarranty, ServiceOrder


def warranty_request_evidence_upload_path(instance, filename):
    """
    Guarda las evidencias de solicitudes de garantía separadas
    por orden y solicitud.
    """
    extension = Path(filename).suffix.lower()
    request_id = instance.pk or uuid.uuid4().hex

    return (
        f"warranty_requests/"
        f"{instance.order_id}/"
        f"{request_id}/"
        f"{uuid.uuid4().hex}{extension}"
    )


class WarrantyActionType(models.TextChoices):
    REPAIR = "REPAIR", "Reparación"
    PART_REPLACEMENT = "PART_REPLACEMENT", "Cambio de repuesto"
    OTHER = "OTHER", "Otra"


class WarrantyRequest(models.Model):
    """
    HU-22/HU-23: Solicitud o reclamo realizado sobre una garantía existente.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        AWAITING_APPROVAL = "AWAITING_APPROVAL", "Pendiente de aprobación"
        CHANGES_REQUESTED = "CHANGES_REQUESTED", "Correcciones solicitadas"
        RESOLVED = "RESOLVED", "Resuelta"

    OPEN_STATUSES = (
        Status.PENDING,
        Status.AWAITING_APPROVAL,
        Status.CHANGES_REQUESTED,
    )

    order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.PROTECT,
        related_name="warranty_requests",
    )
    warranty = models.ForeignKey(
        OrderWarranty,
        on_delete=models.PROTECT,
        related_name="requests",
    )
    requested_on = models.DateField(default=timezone.localdate)
    problem_description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    concurrent_open_reason = models.TextField(blank=True)
    client_name_snapshot = models.CharField(max_length=150, editable=False)
    client_rut_snapshot = models.CharField(max_length=20, editable=False)
    evidence = models.ImageField(
        upload_to=warranty_request_evidence_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["jpg", "jpeg", "png", "webp"]
            )
        ],
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warranty_requests_created",
    )
    created_by_username = models.CharField(
        max_length=150,
        blank=True,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-requested_on", "-created_at", "-id"]

    def clean(self):
        super().clean()

        if (
            self.order_id
            and self.warranty_id
            and self.warranty.order_id != self.order_id
        ):
            raise ValidationError(
                {"warranty": "La garantía seleccionada no pertenece a esta orden."}
            )

        if self.warranty_id:
            warranty_status = self.warranty.current_status

            if warranty_status == OrderWarranty.WarrantyStatus.NOT_APPLICABLE:
                raise ValidationError(
                    {
                        "warranty": (
                            "No se puede registrar una solicitud porque "
                            "esta garantía está marcada como no aplicable."
                        )
                    }
                )

            if warranty_status == OrderWarranty.WarrantyStatus.NOT_STARTED:
                raise ValidationError(
                    {
                        "warranty": (
                            "No se puede registrar una solicitud porque "
                            "esta garantía todavía no ha comenzado."
                        )
                    }
                )

        if not self.problem_description.strip():
            raise ValidationError(
                {
                    "problem_description": (
                        "Describe el problema reportado por el cliente."
                    )
                }
            )

        if self._state.adding and self.warranty_id:
            open_requests = WarrantyRequest.objects.filter(
                warranty_id=self.warranty_id,
                status__in=self.OPEN_STATUSES,
            )

            if (
                open_requests.exists()
                and not self.concurrent_open_reason.strip()
            ):
                raise ValidationError(
                    {
                        "concurrent_open_reason": (
                            "Esta garantía ya tiene una solicitud abierta. "
                            "Indica el motivo para registrar otra solicitud."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        if self.order_id:
            if not self.client_name_snapshot:
                self.client_name_snapshot = self.order.client.name

            if not self.client_rut_snapshot:
                self.client_rut_snapshot = self.order.client.rut

        if self.created_by_id and not self.created_by_username:
            self.created_by_username = self.created_by.get_username()

        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def warranty_status_at_query(self):
        return self.warranty.current_status

    @property
    def has_expired_warranty(self):
        return (
            self.warranty.current_status
            == OrderWarranty.WarrantyStatus.EXPIRED
        )

    @property
    def is_open(self):
        return self.status in self.OPEN_STATUSES

    @property
    def is_resolved(self):
        return self.status == self.Status.RESOLVED

    def __str__(self):
        return (
            f"Solicitud garantía #{self.pk} - "
            f"{self.order.tracking_code}"
        )


class WarrantyRequestProposal(models.Model):
    """
    HU-23: propuesta técnica enviada por TECH.
    Cada reenvío crea una nueva revisión.
    """

    request = models.ForeignKey(
        WarrantyRequest,
        on_delete=models.PROTECT,
        related_name="proposals",
    )
    revision = models.PositiveIntegerField()
    technical_rationale = models.TextField()
    action_type = models.CharField(
        max_length=30,
        choices=WarrantyActionType.choices,
    )
    action_description = models.TextField()
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warranty_request_proposals",
    )
    proposed_by_username = models.CharField(
        max_length=150,
        blank=True,
        editable=False,
    )
    proposed_by_role = models.CharField(
        max_length=20,
        blank=True,
        editable=False,
    )
    proposed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["revision", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["request", "revision"],
                name="unique_warranty_request_proposal_revision",
            )
        ]

    def clean(self):
        super().clean()

        if not self.technical_rationale.strip():
            raise ValidationError(
                {"technical_rationale": "El fundamento técnico es obligatorio."}
            )

        if not self.action_description.strip():
            raise ValidationError(
                {"action_description": "Describe la acción propuesta."}
            )

    def save(self, *args, **kwargs):
        if self.proposed_by_id:
            if not self.proposed_by_username:
                self.proposed_by_username = self.proposed_by.get_username()

            if not self.proposed_by_role:
                self.proposed_by_role = (
                    getattr(self.proposed_by, "role", "") or ""
                )

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Solicitud #{self.request_id} - "
            f"propuesta {self.revision}"
        )


class WarrantyRequestResolution(models.Model):
    """
    HU-23: decisión administrativa final.
    """

    class Decision(models.TextChoices):
        ACCEPTED = "ACCEPTED", "Aceptada"
        REJECTED = "REJECTED", "Rechazada"

    request = models.OneToOneField(
        WarrantyRequest,
        on_delete=models.PROTECT,
        related_name="resolution",
    )
    decision = models.CharField(
        max_length=10,
        choices=Decision.choices,
    )
    rationale = models.TextField()
    action_type = models.CharField(
        max_length=30,
        choices=WarrantyActionType.choices,
        null=True,
        blank=True,
    )
    action_description = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warranty_request_resolutions",
    )
    resolved_by_username = models.CharField(
        max_length=150,
        blank=True,
        editable=False,
    )
    resolved_by_role = models.CharField(
        max_length=20,
        blank=True,
        editable=False,
    )
    resolved_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()

        if not self.rationale.strip():
            raise ValidationError(
                {"rationale": "El fundamento de la decisión es obligatorio."}
            )

        if self.decision == self.Decision.ACCEPTED:
            if not self.action_type:
                raise ValidationError(
                    {"action_type": "Indica la acción autorizada."}
                )

            if not self.action_description.strip():
                raise ValidationError(
                    {
                        "action_description": (
                            "Describe la acción realizada o autorizada."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        if self.resolved_by_id:
            if not self.resolved_by_username:
                self.resolved_by_username = self.resolved_by.get_username()

            if not self.resolved_by_role:
                self.resolved_by_role = (
                    getattr(self.resolved_by, "role", "") or ""
                )

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Solicitud #{self.request_id} - "
            f"{self.get_decision_display()}"
        )


class WarrantyRequestHistory(models.Model):
    """
    HU-22/HU-23: historial interno de cada solicitud de garantía.
    """

    class Action(models.TextChoices):
        CREATED = "CREATED", "Creación"
        UPDATED = "UPDATED", "Actualización"
        STATUS_CHANGED = "STATUS_CHANGED", "Cambio de estado"
        TECH_PROPOSAL = "TECH_PROPOSAL", "Propuesta técnica enviada"
        CHANGES_REQUESTED = (
            "CHANGES_REQUESTED",
            "Correcciones solicitadas",
        )
        RESOLVED = "RESOLVED", "Resolución administrativa"
        ADMIN_NOTE = "ADMIN_NOTE", "Observación administrativa"

    request = models.ForeignKey(
        WarrantyRequest,
        on_delete=models.PROTECT,
        related_name="history",
    )
    revision = models.PositiveIntegerField()
    action = models.CharField(
        max_length=30,
        choices=Action.choices,
    )
    from_status = models.CharField(
        max_length=20,
        choices=WarrantyRequest.Status.choices,
        null=True,
        blank=True,
    )
    to_status = models.CharField(
        max_length=20,
        choices=WarrantyRequest.Status.choices,
    )
    observation = models.TextField(blank=True)
    decision = models.CharField(
        max_length=10,
        choices=WarrantyRequestResolution.Decision.choices,
        null=True,
        blank=True,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warranty_request_changes",
    )
    changed_by_username = models.CharField(
        max_length=150,
        blank=True,
    )
    changed_by_role = models.CharField(
        max_length=20,
        blank=True,
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["revision", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["request", "revision"],
                name="unique_warranty_request_revision",
            )
        ]

    def save(self, *args, **kwargs):
        if self.changed_by_id:
            if not self.changed_by_username:
                self.changed_by_username = self.changed_by.get_username()

            if not self.changed_by_role:
                self.changed_by_role = (
                    getattr(self.changed_by, "role", "") or ""
                )

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Solicitud #{self.request_id} - "
            f"revisión {self.revision}"
        )
