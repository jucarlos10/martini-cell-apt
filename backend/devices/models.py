from django.conf import settings
from django.db import models

from customers.models import Client


class Equipment(models.Model):
    class EquipmentType(models.TextChoices):
        CELULAR = "CELULAR", "Celular"
        NOTEBOOK = "NOTEBOOK", "Notebook"
        PC = "PC", "PC"
        TABLET = "TABLET", "Tablet"
        OTRO = "OTRO", "Otro"

    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name="equipment",
    )

    equipment_type = models.CharField(
        max_length=20,
        choices=EquipmentType.choices,
    )

    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    imei = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
    )

    serial_number = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
    )

    color = models.CharField(
        max_length=50,
        blank=True,
    )

    observations = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipment_created",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipment_updated",
    )

    def save(self, *args, **kwargs):
        if self.imei:
            self.imei = self.imei.replace(" ", "").replace("-", "").strip()

        if self.serial_number:
            self.serial_number = (
                self.serial_number.replace(" ", "").strip().upper()
            )

        if not self.imei:
            self.imei = None

        if not self.serial_number:
            self.serial_number = None

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.brand} {self.model} "
            f"- {self.client.name}"
        )