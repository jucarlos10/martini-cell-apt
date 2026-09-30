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


class WarrantyRequest(models.Model):
    """
    HU-22: Solicitud o reclamo realizado sobre una garantía existente.

    Una garantía puede tener varias solicitudes a lo largo del tiempo.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"

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

    requested_on = models.DateField(
        default=timezone.localdate,
    )

    problem_description = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Se exige cuando ya existe otra solicitud pendiente
    # para la misma garantía y ADMIN/TECH decide abrir otra.
    concurrent_open_reason = models.TextField(
        blank=True,
    )

    # Datos históricos del cliente al momento de abrir la solicitud.
    # Se obtienen automáticamente desde la orden y no se sobrescriben
    # en modificaciones posteriores.
    client_name_snapshot = models.CharField(
        max_length=150,
        editable=False,
    )

    client_rut_snapshot = models.CharField(
        max_length=20,
        editable=False,
    )

    evidence = models.ImageField(
        upload_to=warranty_request_evidence_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "jpg",
                    "jpeg",
                    "png",
                    "webp",
                ]
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

    # Conserva quién ingresó la solicitud aunque posteriormente
    # la cuenta del usuario sea eliminada.
    created_by_username = models.CharField(
        max_length=150,
        blank=True,
        editable=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-requested_on",
            "-created_at",
            "-id",
        ]

    def clean(self):
        super().clean()

        if (
            self.order_id
            and self.warranty_id
            and self.warranty.order_id != self.order_id
        ):
            raise ValidationError(
                {
                    "warranty": (
                        "La garantía seleccionada no pertenece "
                        "a esta orden."
                    )
                }
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

        if self.warranty_id:
            pending_requests = WarrantyRequest.objects.filter(
                warranty_id=self.warranty_id,
                status=self.Status.PENDING,
            )

            if self.pk:
                pending_requests = pending_requests.exclude(pk=self.pk)

            if (
                pending_requests.exists()
                and not self.concurrent_open_reason.strip()
            ):
                raise ValidationError(
                    {
                        "concurrent_open_reason": (
                            "Esta garantía ya tiene una solicitud pendiente. "
                            "Indica el motivo para registrar otra solicitud."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        # El snapshot se captura solo al crearse. Así HU-23 podrá cambiar
        # el estado de la solicitud sin reemplazar los datos históricos
        # del cliente por información editada posteriormente.
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
        """
        Estado actual de la cobertura.

        Las garantías vencidas sí pueden recibir solicitudes;
        la interfaz deberá mostrar la advertencia correspondiente.
        """
        return self.warranty.current_status

    @property
    def has_expired_warranty(self):
        return (
            self.warranty.current_status
            == OrderWarranty.WarrantyStatus.EXPIRED
        )

    def __str__(self):
        return (
            f"Solicitud garantía #{self.pk} - "
            f"{self.order.tracking_code}"
        )


class WarrantyRequestHistory(models.Model):
    """
    HU-22: Historial interno de cada solicitud de garantía.

    HU-23 ampliará este historial al resolver solicitudes.
    """

    class Action(models.TextChoices):
        CREATED = "CREATED", "Creación"
        UPDATED = "UPDATED", "Actualización"
        STATUS_CHANGED = "STATUS_CHANGED", "Cambio de estado"

    request = models.ForeignKey(
        WarrantyRequest,
        on_delete=models.PROTECT,
        related_name="history",
    )

    revision = models.PositiveIntegerField()

    action = models.CharField(
        max_length=20,
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

    observation = models.TextField(
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

    changed_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "revision",
            "id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "request",
                    "revision",
                ],
                name="unique_warranty_request_revision",
            )
        ]

    def __str__(self):
        return (
            f"Solicitud #{self.request_id} - "
            f"revisión {self.revision}"
        )
