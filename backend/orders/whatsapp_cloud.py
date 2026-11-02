"""
Servicio reutilizable para enviar mensajes mediante WhatsApp Cloud API (Meta).

Este módulo:
- usa únicamente la biblioteca estándar de Python;
- obtiene configuración y secretos desde django.conf.settings;
- no registra ni devuelve el access token;
- envía plantillas aprobadas de WhatsApp;
- devuelve el identificador del mensaje entregado por Meta para trazabilidad.

La integración debe mantenerse desacoplada de los flujos de negocio. Las vistas
de órdenes, chat y comprobantes decidirán qué hacer si este servicio no está
configurado o si Meta devuelve un error.
"""

import json
import re
import socket
from dataclasses import dataclass
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


class WhatsAppCloudError(Exception):
    """Error base de la integración con WhatsApp Cloud API."""


class WhatsAppCloudConfigurationError(WhatsAppCloudError):
    """La integración está deshabilitada o faltan variables requeridas."""


class WhatsAppCloudRequestError(WhatsAppCloudError):
    """Meta rechazó la solicitud o no fue posible completar la conexión."""


@dataclass(frozen=True)
class WhatsAppSendResult:
    """Resultado seguro de un envío aceptado por WhatsApp Cloud API."""

    message_id: str
    destination: str
    template_name: str
    provider: str = "META_WHATSAPP_CLOUD"

    def as_dict(self):
        return {
            "provider": self.provider,
            "message_id": self.message_id,
            "destination": self.destination,
            "template_name": self.template_name,
        }


def _setting(name, default=""):
    value = getattr(settings, name, default)
    if isinstance(value, str):
        return value.strip()
    return value


def whatsapp_cloud_configuration_issues():
    """
    Devuelve una lista de problemas de configuración.

    No incluye valores secretos, por lo que el resultado puede utilizarse en
    validaciones internas o pruebas sin exponer el access token.
    """
    issues = []

    if not bool(_setting("WHATSAPP_CLOUD_API_ENABLED", False)):
        issues.append("WhatsApp Cloud API está deshabilitada.")

    required = {
        "WHATSAPP_CLOUD_API_VERSION": "Falta WHATSAPP_CLOUD_API_VERSION.",
        "WHATSAPP_CLOUD_PHONE_NUMBER_ID": "Falta WHATSAPP_CLOUD_PHONE_NUMBER_ID.",
        "WHATSAPP_CLOUD_ACCESS_TOKEN": "Falta WHATSAPP_CLOUD_ACCESS_TOKEN.",
    }

    for setting_name, message in required.items():
        if not _setting(setting_name):
            issues.append(message)

    return issues


def whatsapp_cloud_is_ready():
    """Indica si la configuración mínima para enviar mensajes está disponible."""
    return not whatsapp_cloud_configuration_issues()


def _require_configuration():
    issues = whatsapp_cloud_configuration_issues()
    if issues:
        raise WhatsAppCloudConfigurationError(" ".join(issues))


def normalize_whatsapp_destination(value):
    """
    Normaliza un destino al formato internacional numérico esperado por Meta.

    Se permiten valores almacenados con espacios, paréntesis, guiones o '+'.
    El código de país debe venir incluido desde los datos del cliente.
    """
    raw = str(value or "").strip()
    digits = re.sub(r"\D", "", raw)

    if not digits:
        raise WhatsAppCloudRequestError(
            "El destinatario de WhatsApp no contiene un número válido."
        )

    if len(digits) < 8 or len(digits) > 15:
        raise WhatsAppCloudRequestError(
            "El destinatario de WhatsApp no tiene una longitud internacional válida."
        )

    return digits


def _messages_endpoint():
    base_url = _setting(
        "WHATSAPP_CLOUD_API_BASE_URL",
        "https://graph.facebook.com",
    ).rstrip("/")
    version = _setting("WHATSAPP_CLOUD_API_VERSION")
    phone_number_id = _setting("WHATSAPP_CLOUD_PHONE_NUMBER_ID")

    return f"{base_url}/{version}/{phone_number_id}/messages"


def _text_parameters(values: Iterable):
    parameters = []
    for value in values or []:
        parameters.append(
            {
                "type": "text",
                "text": str(value),
            }
        )
    return parameters


def _template_payload(
    destination,
    template_name,
    body_parameters=None,
    language_code=None,
):
    template = {
        "name": template_name,
        "language": {
            "code": language_code
            or _setting("WHATSAPP_TEMPLATE_LANGUAGE", "es_CL")
            or "es_CL",
        },
    }

    parameters = _text_parameters(body_parameters)
    if parameters:
        template["components"] = [
            {
                "type": "body",
                "parameters": parameters,
            }
        ]

    return {
        "messaging_product": "whatsapp",
        "to": destination,
        "type": "template",
        "template": template,
    }


def _safe_meta_error_detail(payload):
    """
    Extrae una descripción útil de un error de Meta sin incluir headers,
    credenciales ni el cuerpo completo de la petición.
    """
    if not isinstance(payload, dict):
        return ""

    error = payload.get("error")
    if not isinstance(error, dict):
        return ""

    parts = []

    error_type = str(error.get("type") or "").strip()
    error_code = error.get("code")
    error_message = str(error.get("message") or "").strip()

    if error_type:
        parts.append(error_type)
    if error_code not in (None, ""):
        parts.append(f"código {error_code}")
    if error_message:
        parts.append(error_message)

    return " - ".join(parts)


def _parse_json_bytes(raw):
    if not raw:
        return {}

    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}


def send_template_message(
    *,
    to,
    template_name,
    body_parameters=None,
    language_code=None,
):
    """
    Envía una plantilla aprobada mediante WhatsApp Cloud API.

    Args:
        to: teléfono internacional del destinatario.
        template_name: nombre exacto de la plantilla aprobada en Meta.
        body_parameters: valores posicionales para {{1}}, {{2}}, etc.
        language_code: idioma de la plantilla; usa settings por defecto.

    Returns:
        WhatsAppSendResult.

    Raises:
        WhatsAppCloudConfigurationError: si la integración no está lista.
        WhatsAppCloudRequestError: si el destino, plantilla o llamada falla.
    """
    _require_configuration()

    destination = normalize_whatsapp_destination(to)
    template_name = str(template_name or "").strip()

    if not template_name:
        raise WhatsAppCloudRequestError(
            "No se configuró el nombre de la plantilla de WhatsApp."
        )

    payload = _template_payload(
        destination=destination,
        template_name=template_name,
        body_parameters=body_parameters,
        language_code=language_code,
    )

    request = Request(
        _messages_endpoint(),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_setting('WHATSAPP_CLOUD_ACCESS_TOKEN')}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    timeout = int(_setting("WHATSAPP_CLOUD_TIMEOUT", 10) or 10)

    try:
        with urlopen(request, timeout=timeout) as response:
            response_payload = _parse_json_bytes(response.read())
            status_code = getattr(response, "status", 200)

    except HTTPError as exc:
        error_payload = _parse_json_bytes(exc.read())
        detail = _safe_meta_error_detail(error_payload)
        message = f"WhatsApp Cloud API respondió HTTP {exc.code}."
        if detail:
            message = f"{message} {detail}"
        raise WhatsAppCloudRequestError(message) from exc

    except (URLError, TimeoutError, socket.timeout) as exc:
        raise WhatsAppCloudRequestError(
            "No fue posible conectar con WhatsApp Cloud API."
        ) from exc

    if not 200 <= int(status_code) < 300:
        raise WhatsAppCloudRequestError(
            f"WhatsApp Cloud API respondió HTTP {status_code}."
        )

    messages = response_payload.get("messages")
    if not isinstance(messages, list) or not messages:
        raise WhatsAppCloudRequestError(
            "WhatsApp Cloud API no devolvió un identificador de mensaje."
        )

    first_message = messages[0] if isinstance(messages[0], dict) else {}
    message_id = str(first_message.get("id") or "").strip()

    if not message_id:
        raise WhatsAppCloudRequestError(
            "WhatsApp Cloud API no devolvió un identificador de mensaje."
        )

    return WhatsAppSendResult(
        message_id=message_id,
        destination=destination,
        template_name=template_name,
    )
