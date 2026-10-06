from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    """Señal de vida para el proxy; no consulta datos ni revela configuración."""
    response = JsonResponse({"status": "ok"})
    response["Cache-Control"] = "no-store"
    return response
