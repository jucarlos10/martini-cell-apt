import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from customers.models import Client
from devices.models import Equipment


class ServiceOrder(models.Model):
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