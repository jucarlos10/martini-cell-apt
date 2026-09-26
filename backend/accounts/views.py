from django.db import transaction
from django.db.models.deletion import ProtectedError, RestrictedError
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .permissions import IsAdminRole
from .serializers import (
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class UserListCreateView(ListCreateAPIView):
    queryset = User.objects.all().order_by("id")
    permission_classes = [IsAdminRole]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserCreateSerializer
        return UserSerializer


def user_has_related_records(user):
    """
    Comprueba si otros modelos conservan referencias a esta cuenta.

    Se revisan las relaciones inversas del modelo User para incluir
    clientes, equipos, órdenes, informes, historiales y cualquier
    otra relación registrada en los modelos de Django.

    No se limita a las relaciones PROTECT: también comprueba las
    relaciones SET_NULL, porque eliminarlas podría perder información
    sobre quién realizó una operación.
    """
    for relation in user._meta.related_objects:
        related_model = relation.related_model
        related_field = relation.field.name

        if related_model._base_manager.filter(
            **{related_field: user.pk}
        ).exists():
            return True

    return False


class UserDetailView(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    permission_classes = [IsAdminRole]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer
        return UserSerializer

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        # Mantener el mismo criterio de seguridad utilizado al
        # modificar administradores: bloquear sus registros para
        # evitar operaciones simultáneas incompatibles.
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

        # Obtener y bloquear la cuenta que se desea eliminar.
        user = get_object_or_404(
            self.get_queryset().select_for_update(),
            pk=kwargs["pk"],
        )

        self.check_object_permissions(request, user)

        # Nadie puede eliminar su propia cuenta.
        if request.user.pk == user.pk:
            return Response(
                {
                    "detail": (
                        "No puedes eliminar tu propia cuenta."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # El sistema debe conservar al menos un administrador
        # activo y sin archivar.
        if (
            user.role == User.Role.ADMIN
            and user.is_active
            and not user.is_archived
        ):
            other_active_admin_exists = User.objects.filter(
                role=User.Role.ADMIN,
                is_active=True,
                is_archived=False,
            ).exclude(
                pk=user.pk,
            ).exists()

            if not other_active_admin_exists:
                return Response(
                    {
                        "detail": (
                            "No se puede eliminar al último "
                            "administrador activo del sistema."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Impedir la eliminación si existen registros vinculados,
        # incluso cuando la relación permitiría SET_NULL.
        if user_has_related_records(user):
            return Response(
                {
                    "detail": (
                        "Este usuario tiene registros históricos "
                        "vinculados y no puede eliminarse "
                        "definitivamente. Puedes desactivarlo "
                        "o archivarlo para conservar la trazabilidad."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Protección adicional por si existe alguna relación
        # protegida que no haya sido detectada previamente.
        try:
            user.delete()
        except (ProtectedError, RestrictedError):
            return Response(
                {
                    "detail": (
                        "No se puede eliminar este usuario porque "
                        "existen registros vinculados. Puedes "
                        "desactivarlo o archivarlo."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )