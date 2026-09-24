import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from customers.models import Client
from devices.models import Equipment


class ServiceOrder(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "Ingresado"
        DIAGNOSIS = "DIAGNOSIS", "Diagnóstico"
        AUTHORIZATION = "AUTHORIZATION", "Autorización"
        PART = "PART", "Espera de repuesto"
        REPAIR = "REPAIR", "Reparación"
        TESTING = "TESTING", "Pruebas"
        READY = "READY", "Listo para retiro"
        DELIVERED = "DELIVERED", "Entregado"
        CLOSED = "CLOSED", "Cerrado"
        REJECTED = "REJECTED", "No reparado/rechazado"

    tracking_code = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name="service_orders",
    )

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,
        related_name="service_orders",
    )

    reported_issue = models.TextField()

    initial_observations = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED,
    )

    received_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_orders_created",
    )

    def clean(self):
        super().clean()

        if (
            self.client_id
            and self.equipment_id
            and self.equipment.client_id != self.client_id
        ):
            raise ValidationError(
                {
                    "equipment": (
                        "El equipo seleccionado no pertenece "
                        "al cliente indicado."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if not self.tracking_code:
            self.tracking_code = (
                f"MC-{uuid.uuid4().hex[:12].upper()}"
            )

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.tracking_code} - "
            f"{self.client.name} - "
            f"{self.equipment.brand} {self.equipment.model}"
        )


def order_evidence_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()

    return (
        f"order_evidence/"
        f"{instance.order_id}/"
        f"{uuid.uuid4().hex}{extension}"
    )


class OrderEvidence(models.Model):
    class Stage(models.TextChoices):
        RECEPCION = "RECEPCION", "Recepción"
        DIAGNOSTICO = "DIAGNOSTICO", "Diagnóstico"
        REPARACION = "REPARACION", "Reparación"
        ENTREGA = "ENTREGA", "Entrega"
        OTRO = "OTRO", "Otro"

    order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name="evidence",
    )

    stage = models.CharField(
        max_length=20,
        choices=Stage.choices,
    )

    image = models.ImageField(
        upload_to=order_evidence_upload_path,
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
    )

    description = models.CharField(
        max_length=250,
        blank=True,
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_evidence_uploaded",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return (
            f"Evidencia {self.id} - "
            f"{self.order.tracking_code} - "
            f"{self.stage}"
        )


class OrderTechnicalReport(models.Model):
    class Result(models.TextChoices):
        REPARADO = "REPARADO", "Reparado"
        PARCIAL = "PARCIAL", "Reparado parcialmente"
        NO_REPARABLE = "NO_REPARABLE", "No reparable"
        SIN_FALLA = "SIN_FALLA", "Sin falla detectada"

    order = models.OneToOneField(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name="technical_report",
    )

    diagnosis = models.TextField()

    repair_actions = models.TextField()

    repair_observations = models.TextField(
        blank=True,
    )

    parts_description = models.TextField(
        blank=True,
    )

    result = models.CharField(
        max_length=20,
        choices=Result.choices,
    )

    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="technical_reports",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="technical_reports_created",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="technical_reports_updated",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def clean(self):
        super().clean()

        if self.technician_id:
            if self.technician.role != "TECH":
                raise ValidationError(
                    {
                        "technician": (
                            "El responsable debe tener rol de técnico."
                        )
                    }
                )

            if not self.technician.is_active:
                raise ValidationError(
                    {
                        "technician": (
                            "El técnico seleccionado no está activo."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Informe técnico - "
            f"{self.order.tracking_code}"
        )


class OrderTechnicalReportHistory(models.Model):
    report = models.ForeignKey(
        OrderTechnicalReport,
        on_delete=models.CASCADE,
        related_name="history",
    )

    revision = models.PositiveIntegerField()

    diagnosis = models.TextField()

    repair_actions = models.TextField()

    repair_observations = models.TextField(
        blank=True,
    )

    parts_description = models.TextField(
        blank=True,
    )

    result = models.CharField(
        max_length=20,
        choices=OrderTechnicalReport.Result.choices,
    )

    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="technical_report_history",
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="technical_report_changes",
    )

    changed_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["revision"]

        constraints = [
            models.UniqueConstraint(
                fields=["report", "revision"],
                name="unique_technical_report_revision",
            )
        ]

    def __str__(self):
        return (
            f"{self.report.order.tracking_code} - "
            f"revisión {self.revision}"
        )


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.PROTECT,
        related_name="status_history",
    )

    # Vacío únicamente para el registro inicial de la orden.
    from_status = models.CharField(
        max_length=20,
        choices=ServiceOrder.Status.choices,
        null=True,
        blank=True,
    )

    to_status = models.CharField(
        max_length=20,
        choices=ServiceOrder.Status.choices,
    )

    note = models.TextField(
        blank=True,
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_status_changes",
    )

    changed_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["changed_at", "id"]

    def __str__(self):
        return (
            f"{self.order.tracking_code}: "
            f"{self.from_status or 'INICIO'} → {self.to_status}"
        )