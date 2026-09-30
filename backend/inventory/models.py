from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Supplier(models.Model):
    """Proveedor de repuestos."""

    name = models.CharField(max_length=150)
    contact_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class Part(models.Model):
    """Repuesto disponible en el catálogo."""

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="parts",
    )

    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(unit_cost__gte=0),
                name="part_unit_cost_gte_0",
            ),
        ]

    def __str__(self):
        return f"{self.name} - {self.supplier.name}"


class OrderPart(models.Model):
    """
    Registro de un repuesto utilizado en una orden.

    Se conserva el proveedor y el costo unitario de la
    operación, aunque posteriormente cambie el catálogo.

    HU-25 no elimina físicamente el registro cuando se anula
    un uso de repuesto. La anulación queda trazada y el
    registro histórico se conserva.
    """

    order = models.ForeignKey(
        "orders.ServiceOrder",
        on_delete=models.PROTECT,
        related_name="used_parts",
    )

    part = models.ForeignKey(
        Part,
        on_delete=models.PROTECT,
        related_name="order_usages",
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="order_part_usages",
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    note = models.CharField(
        max_length=250,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_parts_registered",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    is_cancelled = models.BooleanField(default=False)

    cancellation_reason = models.TextField(blank=True)

    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_parts_cancelled",
    )

    cancelled_by_username = models.CharField(
        max_length=150,
        blank=True,
        editable=False,
    )

    cancelled_by_role = models.CharField(
        max_length=20,
        blank=True,
        editable=False,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name="order_part_quantity_gte_1",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_cost__gte=0),
                name="order_part_unit_cost_gte_0",
            ),
        ]

    @property
    def subtotal(self):
        return self.quantity * self.unit_cost

    def __str__(self):
        suffix = " [ANULADO]" if self.is_cancelled else ""
        return (
            f"Orden {self.order_id} - "
            f"{self.part.name} x {self.quantity}{suffix}"
        )


class OrderPartCorrectionHistory(models.Model):
    """
    Auditoría de correcciones realizadas a un uso de repuesto.

    HU-24 permite corregir directamente solo cantidad y nota.
    Repuesto, proveedor y costo unitario conservan su valor
    histórico y deben tratarse mediante anulación y nuevo uso.
    """

    class Field(models.TextChoices):
        QUANTITY = "QUANTITY", "Cantidad"
        NOTE = "NOTE", "Nota"

    order_part = models.ForeignKey(
        OrderPart,
        on_delete=models.PROTECT,
        related_name="correction_history",
    )

    field_name = models.CharField(
        max_length=20,
        choices=Field.choices,
    )

    old_value = models.TextField()
    new_value = models.TextField()
    reason = models.TextField()

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_part_corrections",
    )

    changed_by_username = models.CharField(
        max_length=150,
        blank=True,
        editable=False,
    )

    changed_by_role = models.CharField(
        max_length=20,
        blank=True,
        editable=False,
    )

    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["changed_at", "id"]

    def __str__(self):
        return (
            f"Corrección uso {self.order_part_id} - "
            f"{self.get_field_name_display()}"
        )
