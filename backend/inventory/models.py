
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
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
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
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
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
        return (
            f"Orden {self.order_id} - "
            f"{self.part.name} x {self.quantity}"
        )