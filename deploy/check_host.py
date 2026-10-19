"""Comprueba el host sin modificar órdenes ni ejecutar migraciones."""

import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.db import DatabaseError, connections  # noqa: E402
from django.db.migrations.executor import MigrationExecutor  # noqa: E402
from django.db.migrations.exceptions import InconsistentMigrationHistory  # noqa: E402


def check_host():
    errors = []

    if settings.DEBUG:
        errors.append("DJANGO_DEBUG debe ser false en el host.")

    hosts = settings.ALLOWED_HOSTS
    if not any(
        host not in {"*", "localhost", "127.0.0.1", "[::1]"}
        and not host.endswith(".example.com")
        for host in hosts
    ):
        errors.append("DJANGO_ALLOWED_HOSTS necesita el dominio real.")

    if len(settings.SECRET_KEY) < 50 or "change_me" in settings.SECRET_KEY:
        errors.append("DJANGO_SECRET_KEY necesita una clave larga y propia del host.")

    media_root = Path(settings.MEDIA_ROOT)
    if not os.getenv("DJANGO_PRIVATE_MEDIA_ROOT"):
        errors.append("Definir DJANGO_PRIVATE_MEDIA_ROOT en un volumen persistente.")
    if not media_root.is_absolute():
        errors.append("DJANGO_PRIVATE_MEDIA_ROOT debe ser una ruta absoluta.")
    else:
        media_root = media_root.resolve()
        if os.getenv("RAILWAY_SERVICE_ID"):
            volume_path = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
            if not volume_path:
                errors.append("Railway necesita un volumen persistente para las fotos privadas.")
            elif not Path(volume_path).is_absolute() or not media_root.is_relative_to(
                Path(volume_path).resolve()
            ):
                errors.append("DJANGO_PRIVATE_MEDIA_ROOT debe estar dentro del volumen de Railway.")
        public_roots = [
            Path(settings.STATIC_ROOT).resolve(),
            (ROOT / "frontend" / "dist").resolve(),
        ]
        if any(media_root == root or media_root.is_relative_to(root) for root in public_roots):
            errors.append("Las fotos privadas están dentro de una carpeta pública.")
        if not media_root.is_dir():
            errors.append("La carpeta privada no existe: crear el volumen persistente.")
        else:
            try:
                with tempfile.NamedTemporaryFile(prefix=".martini-check-", dir=media_root):
                    pass
            except OSError:
                errors.append("El proceso no puede escribir en la carpeta privada.")

    if not (Path(settings.STATIC_ROOT) / "admin" / "css" / "base.css").is_file():
        errors.append("Faltan estáticos de Django admin: ejecutar collectstatic.")

    try:
        connection = connections["default"]
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        executor = MigrationExecutor(connection)
        if executor.migration_plan(executor.loader.graph.leaf_nodes()):
            errors.append("Hay migraciones pendientes: ejecutar migrate.")
    except (DatabaseError, InconsistentMigrationHistory, OSError):
        errors.append("No se pudo consultar PostgreSQL ni comprobar sus migraciones.")
    finally:
        connections.close_all()

    return errors


if __name__ == "__main__":
    problems = check_host()
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        raise SystemExit(1)
    print("Host preparado: configuración, PostgreSQL, migraciones, estáticos y fotos privadas.")
