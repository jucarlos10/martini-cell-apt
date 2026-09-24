
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
            "password",
        )
        read_only_fields = ("id",)

    def check_admin_safety(self, instance, attrs):
        new_role = attrs.get("role", instance.role)
        new_active = attrs.get("is_active", instance.is_active)

        request = self.context.get("request")

        # Un administrador no puede desactivar su propia cuenta.
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

        # Comprobar si la modificación quitaría a un
        # administrador activo de su función.
        removes_active_admin = (
            instance.role == User.Role.ADMIN
            and instance.is_active
            and (
                new_role != User.Role.ADMIN
                or not new_active
            )
        )

        if removes_active_admin:
            other_active_admin_exists = User.objects.filter(
                role=User.Role.ADMIN,
                is_active=True,
            ).exclude(
                pk=instance.pk,
            ).exists()

            if not other_active_admin_exists:
                field = (
                    "role"
                    if new_role != User.Role.ADMIN
                    else "is_active"
                )

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
        # Bloquear los administradores durante la modificación
        # para evitar que dos cambios simultáneos dejen
        # el sistema sin administradores activos.
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

        # Recuperar los valores actuales después del bloqueo.
        instance.refresh_from_db()

        # Volver a verificar las reglas dentro de la transacción.
        self.check_admin_safety(
            instance,
            validated_data,
        )

        password = validated_data.pop("password", None)

        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)

        if password:
            instance.set_password(password)

        instance.save()

        return instance