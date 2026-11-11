from django.conf import settings
from django.db import models

from .validators import normalize_rut, validate_rut


class Client(models.Model):
    class IdentificationType(models.TextChoices):
        RUT = "RUT", "RUT chileno"
        PASSPORT = "PASSPORT", "Pasaporte"
        FOREIGN_DOCUMENT = "FOREIGN_DOCUMENT", "Documento extranjero"
        NONE = "NONE", "Sin documento"

    identification_type = models.CharField(
        max_length=20,
        choices=IdentificationType.choices,
        default=IdentificationType.RUT,
    )

    rut = models.CharField(
        max_length=9,
        unique=True,
        validators=[validate_rut],
        null=True,
        blank=True,
    )

    document_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    name = models.CharField(max_length=150)
    phone = models.CharField(
        max_length=30,
        blank=True,
    )
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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "identification_type",
                    "document_number",
                ),
                condition=(
                    ~models.Q(document_number="")
                    & ~models.Q(
                        identification_type=IdentificationType.NONE
                    )
                ),
                name="unique_client_document_by_type",
            ),
        ]

    @property
    def identification_value(self):
        if self.identification_type == self.IdentificationType.RUT:
            return self.rut or ""

        if self.identification_type in {
            self.IdentificationType.PASSPORT,
            self.IdentificationType.FOREIGN_DOCUMENT,
        }:
            return self.document_number

        return ""

    @property
    def identification_display(self):
        label = self.get_identification_type_display()
        value = self.identification_value

        if value:
            return f"{label}: {value}"

        return label

    def clean_fields(self, exclude=None):
        if self.identification_type == self.IdentificationType.RUT:
            self.rut = normalize_rut(self.rut)
        else:
            self.rut = None

        if self.identification_type in {
            self.IdentificationType.PASSPORT,
            self.IdentificationType.FOREIGN_DOCUMENT,
        }:
            self.document_number = (
                str(self.document_number or "")
                .strip()
                .upper()
            )
        else:
            self.document_number = ""

        super().clean_fields(exclude=exclude)

    def save(self, *args, **kwargs):
        if self.identification_type == self.IdentificationType.RUT:
            self.rut = normalize_rut(self.rut)
            self.document_number = ""
        elif self.identification_type in {
            self.IdentificationType.PASSPORT,
            self.IdentificationType.FOREIGN_DOCUMENT,
        }:
            self.rut = None
            self.document_number = (
                str(self.document_number or "")
                .strip()
                .upper()
            )
        else:
            self.rut = None
            self.document_number = ""

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.identification_display}"


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
