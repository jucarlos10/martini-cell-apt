from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        TECH = "TECH", "Tecnico"
        HELPER = "HELPER", "Ayudante"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.HELPER,
    )

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"
