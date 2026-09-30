from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminRole(BasePermission):
    """
    Permite acceso exclusivamente a usuarios ADMIN.
    """

    message = "No tienes permisos para realizar esta accion."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "ADMIN"
        )


class IsAdminOrTechRole(BasePermission):
    """
    Permite acceso exclusivamente a ADMIN y TECH.
    """

    message = "No tienes permisos para realizar esta accion."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in {"ADMIN", "TECH"}
        )


class CanManageOperationalRecord(BasePermission):
    """
    Matriz base HU-26 para registros operacionales.

    ADMIN:
        consultar, crear, modificar y eliminar.

    TECH:
        consultar, crear y modificar.

    HELPER:
        consultar y crear.
        No puede modificar ni eliminar.

    La eliminación queda reservada exclusivamente a ADMIN.
    """

    message = "No tienes permisos para realizar esta accion."

    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        # Todos los perfiles internos pueden consultar.
        if request.method in SAFE_METHODS:
            return True

        # Todos los perfiles internos pueden registrar
        # información inicial/recepción.
        if request.method == "POST":
            return user.role in {
                "ADMIN",
                "TECH",
                "HELPER",
            }

        # ADMIN y TECH pueden modificar registros existentes.
        if request.method in {"PUT", "PATCH"}:
            return user.role in {
                "ADMIN",
                "TECH",
            }

        # Solo ADMIN puede eliminar.
        if request.method == "DELETE":
            return user.role == "ADMIN"

        return False
