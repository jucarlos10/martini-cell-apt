from django.conf import settings
from django.db import models

from .validators import normalize_rut, validate_rut


class Client(models.Model):
    rut = models.CharField(
        max_length=9,
        unique=True,
        validators=[validate_rut],
    )
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_updated",
    )

    def clean_fields(self, exclude=None):
        self.rut = normalize_rut(self.rut)
        super().clean_fields(exclude=exclude)

    def save(self, *args, **kwargs):
        self.rut = normalize_rut(self.rut)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.rut}"


class ClientChangeHistory(models.Model):
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="change_history",
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="client_changes",
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    changes = models.JSONField()

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"Cambio cliente {self.client_id} - {self.changed_at}"
