
import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.utils import timezone

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


# HU-14: Costos, precios y márgenes de reparación.
class OrderFinancial(models.Model):
    """
    Información financiera de una orden de servicio.

    El costo de repuestos se obtiene desde OrderPart (HU-13).
    No se almacena nuevamente aquí para evitar duplicaciones.
    """

    order = models.OneToOneField(
        ServiceOrder,
        on_delete=models.PROTECT,
        related_name="financial",
    )

    # Puede quedar pendiente mientras no se defina el precio.
    price_charged = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    labor_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    other_direct_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_financials_created",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_financials_updated",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(price_charged__isnull=True)
                    | models.Q(price_charged__gte=0)
                ),
                name="order_financial_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(labor_cost__gte=0),
                name="order_financial_labor_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(other_direct_cost__gte=0),
                name="order_financial_other_nonnegative",
            ),
        ]

    def __str__(self):
        return f"Finanzas - {self.order.tracking_code}"


# HU-15: Garantías del servicio y de repuestos utilizados.
class OrderWarranty(models.Model):
    class WarrantyType(models.TextChoices):
        SERVICE = "SERVICE", "Garantía del servicio"
        PART = "PART", "Garantía de repuesto"

    class WarrantyStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Vigente"
        EXPIRED = "EXPIRED", "Vencida"
        NOT_APPLICABLE = "NOT_APPLICABLE", "No aplica"
        NOT_STARTED = "NOT_STARTED", "Aún no inicia"

    order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.PROTECT,
        related_name="warranties",
    )

    # Solo se utiliza para una garantía de repuesto.
    # OrderPart conserva el proveedor histórico de HU-13.
    order_part = models.OneToOneField(
        "inventory.OrderPart",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="warranty",
    )

    warranty_type = models.CharField(
        max_length=10,
        choices=WarrantyType.choices,
    )

    is_applicable = models.BooleanField(default=True)

    starts_on = models.DateField(
        null=True,
        blank=True,
    )

    ends_on = models.DateField(
        null=True,
        blank=True,
    )

    conditions = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warranties_created",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warranties_updated",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order_id", "id"]

        constraints = [
            models.UniqueConstraint(
                fields=["order"],
                condition=models.Q(warranty_type="SERVICE"),
                name="unique_service_warranty_per_order",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        warranty_type="SERVICE",
                        order_part__isnull=True,
                    )
                    | models.Q(
                        warranty_type="PART",
                        order_part__isnull=False,
                    )
                ),
                name="warranty_type_matches_part",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        is_applicable=False,
                        starts_on__isnull=True,
                        ends_on__isnull=True,
                    )
                    | models.Q(
                        is_applicable=True,
                        starts_on__isnull=False,
                        ends_on__isnull=False,
                        ends_on__gte=models.F("starts_on"),
                    )
                ),
                name="warranty_valid_date_range",
            ),
        ]

    def clean(self):
        super().clean()

        if self.warranty_type == self.WarrantyType.SERVICE:
            if self.order_part_id is not None:
                raise ValidationError({
                    "order_part": (
                        "La garantía del servicio no debe "
                        "vincularse a un repuesto."
                    )
                })

        elif self.warranty_type == self.WarrantyType.PART:
            if self.order_part_id is None:
                raise ValidationError({
                    "order_part": (
                        "Selecciona el repuesto utilizado "
                        "en esta orden."
                    )
                })

            if (
                self.order_id
                and self.order_part_id
                and self.order_part.order_id != self.order_id
            ):
                raise ValidationError({
                    "order_part": (
                        "El repuesto seleccionado no pertenece "
                        "a esta orden."
                    )
                })

        if not self.is_applicable:
            if self.starts_on is not None or self.ends_on is not None:
                raise ValidationError(
                    "Una garantía que no aplica no debe tener fechas."
                )
            return

        if self.starts_on is None or self.ends_on is None:
            raise ValidationError(
                "Indica las fechas de inicio y término de la garantía."
            )

        if self.ends_on < self.starts_on:
            raise ValidationError({
                "ends_on": (
                    "La fecha de término no puede ser "
                    "anterior a la fecha de inicio."
                )
            })

        if not self.conditions.strip():
            raise ValidationError({
                "conditions": (
                    "Indica las condiciones de la garantía."
                )
            })

    @property
    def current_status(self):
        if not self.is_applicable:
            return self.WarrantyStatus.NOT_APPLICABLE

        today = timezone.localdate()

        if today < self.starts_on:
            return self.WarrantyStatus.NOT_STARTED

        # La fecha de término se considera incluida.
        if today <= self.ends_on:
            return self.WarrantyStatus.ACTIVE

        return self.WarrantyStatus.EXPIRED

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.get_warranty_type_display()} - "
            f"{self.order.tracking_code}"
        )


# HU-15: Historial de creación y modificaciones de garantías.
class OrderWarrantyHistory(models.Model):
    class Action(models.TextChoices):
        CREATED = "CREATED", "Creación"
        UPDATED = "UPDATED", "Actualización"

    warranty = models.ForeignKey(
        OrderWarranty,
        on_delete=models.PROTECT,
        related_name="history",
    )

    revision = models.PositiveIntegerField()

    action = models.CharField(
        max_length=10,
        choices=Action.choices,
    )

    # Copia de los datos de la garantía en esta revisión.
    order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.PROTECT,
        related_name="warranty_history",
    )

    warranty_type = models.CharField(
        max_length=10,
        choices=OrderWarranty.WarrantyType.choices,
    )

    order_part = models.ForeignKey(
        "inventory.OrderPart",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="warranty_history",
    )

    is_applicable = models.BooleanField()

    starts_on = models.DateField(
        null=True,
        blank=True,
    )

    ends_on = models.DateField(
        null=True,
        blank=True,
    )

    conditions = models.TextField(blank=True)

    change_note = models.TextField(blank=True)

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warranty_changes",
    )

    # Conserva el nombre del usuario aunque su cuenta se elimine.
    changed_by_username = models.CharField(
        max_length=150,
        blank=True,
    )

    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["revision"]

        constraints = [
            models.UniqueConstraint(
                fields=["warranty", "revision"],
                name="unique_warranty_revision",
            ),
        ]

    def __str__(self):
        return (
            f"Garantía {self.warranty_id} - "
            f"revisión {self.revision}"
        )
