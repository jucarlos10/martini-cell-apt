from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(
        source="get_role_display",
        read_only=True,
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "role_display",
            "is_active",
            "is_archived",
        )
        read_only_fields = fields


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "password",
        )
        read_only_fields = ("id",)

    def create(self, validated_data):
        # Las cuentas nuevas quedan activas y sin archivar.
        return User.objects.create_user(**validated_data)


class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password],
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "is_archived",
            "password",
        )
        read_only_fields = ("id",)

    def check_admin_safety(self, instance, attrs):
        request = self.context.get("request")

        new_role = attrs.get("role", instance.role)
        new_archived = attrs.get(
            "is_archived",
            instance.is_archived,
        )

        archive_changed = (
            "is_archived" in attrs
            and new_archived != instance.is_archived
        )

        # Archivar y restaurar dejan la cuenta inactiva.
        # La activación posterior es una operación independiente.
        if attrs.get("is_active") is True and (
            new_archived or archive_changed
        ):
            raise serializers.ValidationError(
                {
                    "is_active": (
                        "No puedes activar una cuenta archivada "
                        "ni activarla en la misma operación en que "
                        "se restaura. Primero restáurala y después "
                        "actívala."
                    )
                }
            )

        new_active = (
            False
            if new_archived or archive_changed
            else attrs.get("is_active", instance.is_active)
        )

        # Un administrador no puede archivar su propia cuenta.
        if (
            request is not None
            and request.user.pk == instance.pk
            and new_archived
            and not instance.is_archived
        ):
            raise serializers.ValidationError(
                {
                    "is_archived": (
                        "No puedes archivar tu propia cuenta."
                    )
                }
            )

        # Se conserva la protección existente:
        # un administrador no puede desactivarse a sí mismo.
        if (
            request is not None
            and request.user.pk == instance.pk
            and not new_active
        ):
            raise serializers.ValidationError(
                {
                    "is_active": (
                        "No puedes desactivar tu propia cuenta."
                    )
                }
            )

        # No permitir que el sistema quede sin
        # administradores activos y sin archivar.
        removes_active_admin = (
            instance.role == User.Role.ADMIN
            and instance.is_active
            and (
                new_role != User.Role.ADMIN
                or not new_active
                or new_archived
            )
        )

        if removes_active_admin:
            other_active_admin_exists = User.objects.filter(
                role=User.Role.ADMIN,
                is_active=True,
                is_archived=False,
            ).exclude(
                pk=instance.pk,
            ).exists()

            if not other_active_admin_exists:
                if new_role != User.Role.ADMIN:
                    field = "role"
                elif new_archived:
                    field = "is_archived"
                else:
                    field = "is_active"

                raise serializers.ValidationError(
                    {
                        field: (
                            "No se puede dejar el sistema "
                            "sin administradores activos."
                        )
                    }
                )

    def validate(self, attrs):
        if self.instance is not None:
            self.check_admin_safety(
                self.instance,
                attrs,
            )

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        # Bloquear las cuentas administradoras para evitar
        # modificaciones simultáneas que dejen al sistema
        # sin administradores activos.
        list(
            User.objects.filter(
                role=User.Role.ADMIN,
            ).order_by(
                "pk"
            ).select_for_update().values_list(
                "pk",
                flat=True,
            )
        )

        # Volver a consultar el estado actual después del bloqueo.
        instance.refresh_from_db()

        # Repetir las validaciones dentro de la transacción.
        self.check_admin_safety(
            instance,
            validated_data,
        )

        password = validated_data.pop("password", None)

        new_archived = validated_data.get(
            "is_archived",
            instance.is_archived,
        )

        archive_changed = (
            "is_archived" in validated_data
            and new_archived != instance.is_archived
        )

        # Tanto archivar como restaurar desactivan la cuenta.
        # Una cuenta archivada tampoco puede permanecer activa.
        if new_archived or archive_changed:
            validated_data["is_active"] = False

        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)

        if password:
            instance.set_password(password)

        instance.save()

        return instance