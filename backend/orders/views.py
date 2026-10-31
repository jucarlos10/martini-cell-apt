import mimetypes
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import quote
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import (
    CanManageOperationalRecord,
    IsAdminOrTechRole,
)

from .models import (
    OrderChatConversation,
    OrderChatMessage,
    OrderChatNotification,
    OrderEvidence,
    OrderReceptionReceipt,
    OrderReceptionReceiptDelivery,
    OrderSensitiveChangeHistory,
    OrderStatusHistory,
    OrderStatusNotification,
    OrderTechnicalReport,
    ServiceOrder,
)
from .serializers import (
    OrderChatConversationDetailSerializer,
    OrderChatConversationListSerializer,
    OrderChatMessageCreateSerializer,
    OrderChatPublicConversationSerializer,
    OrderChatStatusUpdateSerializer,
    OrderEvidenceSerializer,
    OrderReceptionReceiptDeliveryRequestSerializer,
    OrderReceptionReceiptSerializer,
    OrderSensitiveChangeHistorySerializer,
    OrderStatusNotificationSerializer,
    OrderTechnicalReportHistorySerializer,
    OrderTechnicalReportSerializer,
    ServiceOrderSerializer,
)
from .services import calculate_order_times
from .whatsapp_cloud import (
    WhatsAppCloudError,
    send_template_message,
)


# Transiciones permitidas para la primera versión de HU-10.
# Conservamos los diez estados existentes en el frontend.
STATUS_TRANSITIONS = {
    ServiceOrder.Status.RECEIVED: (
        ServiceOrder.Status.DIAGNOSIS,
    ),
    ServiceOrder.Status.DIAGNOSIS: (
        ServiceOrder.Status.AUTHORIZATION,
        ServiceOrder.Status.REJECTED,
    ),
    ServiceOrder.Status.AUTHORIZATION: (
        ServiceOrder.Status.PART,
        ServiceOrder.Status.REPAIR,
        ServiceOrder.Status.REJECTED,
    ),
    ServiceOrder.Status.PART: (
        ServiceOrder.Status.REPAIR,
        ServiceOrder.Status.REJECTED,
    ),
    ServiceOrder.Status.REPAIR: (
        ServiceOrder.Status.PART,
        ServiceOrder.Status.TESTING,
    ),
    ServiceOrder.Status.TESTING: (
        ServiceOrder.Status.REPAIR,
        ServiceOrder.Status.READY,
    ),
    ServiceOrder.Status.READY: (
        ServiceOrder.Status.DELIVERED,
    ),
    ServiceOrder.Status.REJECTED: (
        ServiceOrder.Status.READY,
    ),
    ServiceOrder.Status.DELIVERED: (
        ServiceOrder.Status.CLOSED,
    ),
    ServiceOrder.Status.CLOSED: (),
}


class OrderStatusChangeSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=ServiceOrder.Status.choices,
    )

    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
    )


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    from_status_display = serializers.CharField(
        source="get_from_status_display",
        read_only=True,
    )

    to_status_display = serializers.CharField(
        source="get_to_status_display",
        read_only=True,
    )

    changed_by_username = serializers.SerializerMethodField()

    notifications = OrderStatusNotificationSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = OrderStatusHistory
        fields = (
            "id",
            "from_status",
            "from_status_display",
            "to_status",
            "to_status_display",
            "note",
            "changed_by",
            "changed_by_username",
            "changed_at",
            "notifications",
        )

        read_only_fields = fields

    def get_changed_by_username(self, obj):
        if not obj.changed_by_id:
            return None

        return obj.changed_by.username


def get_order_status_data(order):
    allowed = STATUS_TRANSITIONS.get(
        order.status,
        (),
    )

    return {
        "order_id": order.id,
        "tracking_code": order.tracking_code,
        "status": order.status,
        "status_display": order.get_status_display(),
        "allowed_transitions": [
            {
                "status": next_status,
                "status_display": ServiceOrder.Status(
                    next_status
                ).label,
            }
            for next_status in allowed
        ],
    }


class ServiceOrderListCreateView(ListCreateAPIView):
    queryset = (
        ServiceOrder.objects
        .select_related("client", "equipment", "created_by")
        .all()
        .order_by("-received_at")
    )
    serializer_class = ServiceOrderSerializer
    permission_classes = [
        IsAuthenticated,
        CanManageOperationalRecord,
    ]

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user
        )


class ServiceOrderDetailView(RetrieveUpdateAPIView):
    queryset = (
        ServiceOrder.objects
        .select_related("client", "equipment", "created_by")
        .all()
    )
    serializer_class = ServiceOrderSerializer
    permission_classes = [
        IsAuthenticated,
        CanManageOperationalRecord,
    ]


# HU-34: generación y entrega del comprobante de recepción.
def _masked_identifier(value):
    if not value:
        return ""

    value = str(value).strip()

    if len(value) <= 4:
        return value

    return f"{'*' * (len(value) - 4)}{value[-4:]}"


def _build_reception_receipt_snapshot(order):
    equipment = order.equipment
    client = order.client

    identifier_label = ""
    identifier_value = ""

    if equipment.imei:
        identifier_label = "IMEI"
        identifier_value = _masked_identifier(equipment.imei)
    elif equipment.serial_number:
        identifier_label = "Número de serie"
        identifier_value = _masked_identifier(equipment.serial_number)

    received_by = ""

    if order.created_by_id:
        received_by = order.created_by.username

    return {
        "business": {
            "name": "Martini Cell",
        },
        "order": {
            "id": order.id,
            "tracking_code": order.tracking_code,
            "received_at": order.received_at.isoformat(),
            "status": order.status,
            "status_display": order.get_status_display(),
        },
        "client": {
            "name": client.name,
            "phone": client.phone,
            "email": client.email,
        },
        "equipment": {
            "type": equipment.equipment_type,
            "type_display": equipment.get_equipment_type_display(),
            "brand": equipment.brand,
            "model": equipment.model,
            "color": equipment.color,
            "identifier_label": identifier_label,
            "identifier": identifier_value,
        },
        "reception": {
            "reported_issue": order.reported_issue,
            "initial_observations": order.initial_observations,
            "received_accessories": order.received_accessories,
            "deposit_amount": str(order.deposit_amount),
            "received_by": received_by,
            "confirmation": (
                "Martini Cell confirma la recepción del equipo "
                "descrito en este comprobante."
            ),
        },
        "tracking": {
            "instructions": (
                "Conserva este código. Es el mismo código de la orden "
                "y se utiliza para consultar el estado de la reparación."
            ),
        },
    }


def _get_or_create_reception_receipt(order, user):
    receipt, created = OrderReceptionReceipt.objects.get_or_create(
        order=order,
        defaults={
            "snapshot": _build_reception_receipt_snapshot(order),
            "generated_by": user,
        },
    )

    return receipt, created


def _format_clp(value):
    """Formatea un monto en pesos chilenos, sin decimales."""
    try:
        amount = Decimal(str(value or "0"))
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal("0")

    return f"${amount:,.0f}".replace(",", ".")


def _receipt_email_body(receipt):
    snapshot = receipt.snapshot
    order_data = snapshot.get("order", {})
    client_data = snapshot.get("client", {})
    equipment_data = snapshot.get("equipment", {})
    reception_data = snapshot.get("reception", {})

    received_at = order_data.get("received_at", "")
    formatted_received_at = received_at

    if receipt.order.received_at:
        chile_time = receipt.order.received_at.astimezone(
            ZoneInfo("America/Santiago")
        )
        formatted_received_at = chile_time.strftime(
            "%d-%m-%Y %H:%M"
        )

    identifier = ""
    if equipment_data.get("identifier"):
        identifier = (
            f"{equipment_data.get('identifier_label', 'Identificador')}: "
            f"{equipment_data['identifier']}\n"
        )

    accessories = reception_data.get("received_accessories") or "Sin accesorios informados"
    observations = reception_data.get("initial_observations") or "Sin observaciones iniciales"

    return (
        "MARTINI CELL - COMPROBANTE DE RECEPCIÓN\n\n"
        f"Orden: {order_data.get('tracking_code', '')}\n"
        f"Fecha y hora de recepción: {formatted_received_at}\n\n"
        f"Cliente: {client_data.get('name', '')}\n"
        f"Teléfono: {client_data.get('phone', '')}\n"
        f"Correo: {client_data.get('email', '') or 'No registrado'}\n\n"
        f"Equipo: {equipment_data.get('type_display', '')}\n"
        f"Marca / modelo: {equipment_data.get('brand', '')} "
        f"{equipment_data.get('model', '')}\n"
        f"{identifier}"
        f"Falla informada: {reception_data.get('reported_issue', '')}\n"
        f"Condición / observaciones iniciales: {observations}\n"
        f"Accesorios recibidos: {accessories}\n"
        f"Abono recibido: {_format_clp(reception_data.get('deposit_amount'))}\n"
        f"Recibido por: {reception_data.get('received_by', '')}\n\n"
        f"{reception_data.get('confirmation', '')}\n\n"
        "Conserva el código de la orden para consultar posteriormente "
        "el estado de la reparación.\n"
    )


def _whatsapp_number(phone):
    digits = re.sub(r"\D", "", phone or "")

    # Los celulares chilenos suelen almacenarse como 9XXXXXXXX.
    # Para wa.me se utiliza el código de país sin el signo +.
    if len(digits) == 9 and digits.startswith("9"):
        digits = f"56{digits}"

    return digits


class OrderReceptionReceiptView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsAdminOrTechRole,
    ]

    def get_order(self, pk):
        return get_object_or_404(
            ServiceOrder.objects.select_related(
                "client",
                "equipment",
                "created_by",
            ),
            pk=pk,
        )

    def get(self, request, pk):
        order = self.get_order(pk)

        receipt = get_object_or_404(
            OrderReceptionReceipt.objects
            .select_related(
                "order",
                "generated_by",
            )
            .prefetch_related("deliveries"),
            order=order,
        )

        return Response(
            OrderReceptionReceiptSerializer(receipt).data
        )

    @transaction.atomic
    def post(self, request, pk):
        order = self.get_order(pk)

        receipt, created = _get_or_create_reception_receipt(
            order,
            request.user,
        )

        receipt = (
            OrderReceptionReceipt.objects
            .select_related(
                "order",
                "generated_by",
            )
            .prefetch_related("deliveries")
            .get(pk=receipt.pk)
        )

        return Response(
            OrderReceptionReceiptSerializer(receipt).data,
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )


class OrderReceptionReceiptDeliveryView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsAdminOrTechRole,
    ]

    def get_order(self, pk):
        return get_object_or_404(
            ServiceOrder.objects.select_related(
                "client",
                "equipment",
                "created_by",
            ),
            pk=pk,
        )

    def post(self, request, pk):
        request_serializer = (
            OrderReceptionReceiptDeliveryRequestSerializer(
                data=request.data
            )
        )
        request_serializer.is_valid(raise_exception=True)

        delivery_method = request_serializer.validated_data[
            "delivery_method"
        ]

        order = self.get_order(pk)
        receipt, _ = _get_or_create_reception_receipt(
            order,
            request.user,
        )

        if (
            delivery_method
            == OrderReceptionReceiptDelivery.DeliveryMethod.EMAIL
        ):
            return self._deliver_email(
                order,
                receipt,
                request.user,
            )

        if (
            delivery_method
            == OrderReceptionReceiptDelivery.DeliveryMethod.WHATSAPP
        ):
            return self._prepare_whatsapp(
                order,
                receipt,
                request.user,
            )

        return self._register_print(
            order,
            receipt,
            request.user,
        )

    def _deliver_email(self, order, receipt, user):
        destination = (order.client.email or "").strip()

        if not destination:
            return Response(
                {
                    "detail": (
                        "El cliente no tiene un correo electrónico "
                        "registrado."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.preferred_notification_channel = (
            ServiceOrder.NotificationChannel.EMAIL
        )
        order.save(
            update_fields=[
                "preferred_notification_channel",
                "updated_at",
            ]
        )

        try:
            email = EmailMessage(
                subject=(
                    "Martini Cell - Comprobante de recepción "
                    f"{order.tracking_code}"
                ),
                body=_receipt_email_body(receipt),
                to=[destination],
            )
            sent_count = email.send(using="default")

            if sent_count != 1:
                raise RuntimeError(
                    "El servicio de correo no confirmó el envío."
                )

        except Exception as error:
            delivery = OrderReceptionReceiptDelivery.objects.create(
                receipt=receipt,
                delivery_method=(
                    OrderReceptionReceiptDelivery.DeliveryMethod.EMAIL
                ),
                status=(
                    OrderReceptionReceiptDelivery.DeliveryStatus.FAILED
                ),
                destination=destination,
                detail=str(error)[:1000],
                delivered_by=user,
            )

            return Response(
                {
                    "detail": (
                        "El comprobante está generado, pero no fue posible "
                        "enviar el correo. La orden no fue modificada ni "
                        "eliminada."
                    ),
                    "delivery": {
                        "id": delivery.id,
                        "status": delivery.status,
                    },
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        delivery = OrderReceptionReceiptDelivery.objects.create(
            receipt=receipt,
            delivery_method=(
                OrderReceptionReceiptDelivery.DeliveryMethod.EMAIL
            ),
            status=OrderReceptionReceiptDelivery.DeliveryStatus.SENT,
            destination=destination,
            detail="Comprobante enviado por correo electrónico.",
            delivered_by=user,
        )

        return Response(
            {
                "detail": "Comprobante enviado por correo electrónico.",
                "preferred_notification_channel": (
                    order.preferred_notification_channel
                ),
                "delivery": {
                    "id": delivery.id,
                    "status": delivery.status,
                    "destination": delivery.destination,
                },
            },
            status=status.HTTP_201_CREATED,
        )

    def _prepare_whatsapp(self, order, receipt, user):
        destination = _whatsapp_number(order.client.phone)

        if not destination:
            return Response(
                {
                    "detail": (
                        "El cliente no tiene un teléfono registrado "
                        "para WhatsApp."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.preferred_notification_channel = (
            ServiceOrder.NotificationChannel.WHATSAPP
        )
        order.save(
            update_fields=[
                "preferred_notification_channel",
                "updated_at",
            ]
        )

        message = (
            "Hola. Martini Cell confirma la recepción de tu equipo. "
            f"Tu código de orden y seguimiento es {order.tracking_code}. "
            "Puedes consultar el estado de la reparación directamente en: "
            f"{_public_tracking_url(order.tracking_code)}"
        )

        whatsapp_url = (
            f"https://wa.me/{destination}?text={quote(message)}"
        )

        cloud_api_enabled = bool(
            getattr(
                settings,
                "WHATSAPP_CLOUD_API_ENABLED",
                False,
            )
        )
        cloud_api_error = ""

        if cloud_api_enabled:
            template_name = (
                getattr(
                    settings,
                    "WHATSAPP_TEMPLATE_RECEPTION",
                    "",
                )
                or ""
            ).strip()

            try:
                send_result = send_template_message(
                    to=destination,
                    template_name=template_name,
                    body_parameters=[
                        order.tracking_code,
                    ],
                    language_code=getattr(
                        settings,
                        "WHATSAPP_TEMPLATE_LANGUAGE",
                        "es_CL",
                    ),
                )
            except WhatsAppCloudError as error:
                cloud_api_error = str(error)[:700]

                if not bool(
                    getattr(
                        settings,
                        "WHATSAPP_CLOUD_FALLBACK_TO_WA_ME",
                        False,
                    )
                ):
                    delivery = (
                        OrderReceptionReceiptDelivery.objects.create(
                            receipt=receipt,
                            delivery_method=(
                                OrderReceptionReceiptDelivery
                                .DeliveryMethod.WHATSAPP
                            ),
                            status=(
                                OrderReceptionReceiptDelivery
                                .DeliveryStatus.FAILED
                            ),
                            destination=destination,
                            detail=(
                                "El comprobante está generado, pero no fue "
                                "posible enviarlo mediante WhatsApp Cloud API. "
                                f"{cloud_api_error}"
                            )[:1000],
                            delivered_by=user,
                        )
                    )

                    return Response(
                        {
                            "detail": (
                                "El comprobante está generado, pero no fue "
                                "posible enviarlo por WhatsApp."
                            ),
                            "preferred_notification_channel": (
                                order.preferred_notification_channel
                            ),
                            "receipt": OrderReceptionReceiptSerializer(
                                receipt
                            ).data,
                            "delivery": {
                                "id": delivery.id,
                                "status": delivery.status,
                                "destination": delivery.destination,
                            },
                        },
                        status=status.HTTP_502_BAD_GATEWAY,
                    )
            else:
                delivery = OrderReceptionReceiptDelivery.objects.create(
                    receipt=receipt,
                    delivery_method=(
                        OrderReceptionReceiptDelivery.DeliveryMethod.WHATSAPP
                    ),
                    status=(
                        OrderReceptionReceiptDelivery.DeliveryStatus.SENT
                    ),
                    destination=send_result.destination,
                    detail=(
                        "Comprobante enviado mediante WhatsApp Cloud API. "
                        f"ID de Meta: {send_result.message_id}."
                    )[:1000],
                    delivered_by=user,
                )

                return Response(
                    {
                        "detail": (
                            "Comprobante enviado mediante WhatsApp Cloud API."
                        ),
                        "preferred_notification_channel": (
                            order.preferred_notification_channel
                        ),
                        "whatsapp_url": "",
                        "message": "",
                        "receipt": OrderReceptionReceiptSerializer(
                            receipt
                        ).data,
                        "delivery": {
                            "id": delivery.id,
                            "status": delivery.status,
                            "destination": delivery.destination,
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )

        if cloud_api_error:
            detail = (
                "WhatsApp Cloud API no pudo completar el envío. "
                "Se preparó el respaldo manual mediante wa.me. "
                f"{cloud_api_error}"
            )[:1000]
        else:
            detail = (
                "Mensaje de WhatsApp preparado para envío manual. "
                "WhatsApp Cloud API aún no está habilitada."
            )

        delivery = OrderReceptionReceiptDelivery.objects.create(
            receipt=receipt,
            delivery_method=(
                OrderReceptionReceiptDelivery.DeliveryMethod.WHATSAPP
            ),
            status=(
                OrderReceptionReceiptDelivery.DeliveryStatus.PREPARED
            ),
            destination=destination,
            detail=detail,
            delivered_by=user,
        )

        return Response(
            {
                "detail": "Mensaje de WhatsApp preparado.",
                "preferred_notification_channel": (
                    order.preferred_notification_channel
                ),
                "whatsapp_url": whatsapp_url,
                "message": message,
                "receipt": OrderReceptionReceiptSerializer(
                    receipt
                ).data,
                "delivery": {
                    "id": delivery.id,
                    "status": delivery.status,
                    "destination": delivery.destination,
                },
            },
            status=status.HTTP_201_CREATED,
        )


    def _register_print(self, order, receipt, user):
        if order.client.email:
            order.preferred_notification_channel = (
                ServiceOrder.NotificationChannel.EMAIL
            )
            order.save(
                update_fields=[
                    "preferred_notification_channel",
                    "updated_at",
                ]
            )

        elif (
            order.preferred_notification_channel
            != ServiceOrder.NotificationChannel.WHATSAPP
            or not order.client.phone
        ):
            return Response(
                {
                    "detail": (
                        "El comprobante puede imprimirse, pero el cliente "
                        "no tiene correo registrado. Selecciona WhatsApp "
                        "como canal de notificaciones antes de confirmar "
                        "la entrega impresa."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        delivery = OrderReceptionReceiptDelivery.objects.create(
            receipt=receipt,
            delivery_method=(
                OrderReceptionReceiptDelivery.DeliveryMethod.PRINT
            ),
            status=OrderReceptionReceiptDelivery.DeliveryStatus.PRINTED,
            destination="",
            detail="Comprobante preparado y confirmado como impreso.",
            delivered_by=user,
        )

        return Response(
            {
                "detail": "Entrega impresa registrada.",
                "preferred_notification_channel": (
                    order.preferred_notification_channel
                ),
                "receipt": OrderReceptionReceiptSerializer(
                    receipt
                ).data,
                "delivery": {
                    "id": delivery.id,
                    "status": delivery.status,
                },
            },
            status=status.HTTP_201_CREATED,
        )



# HU-36: notificación al cliente cuando Martini Cell responde el chat.
def _public_tracking_url(tracking_code=""):
    configured_url = getattr(
        settings,
        "FRONTEND_PUBLIC_URL",
        "",
    ).strip()

    if configured_url:
        base_url = configured_url.rstrip("/")
    elif settings.DEBUG:
        base_url = "http://localhost:5173"
    else:
        base_url = "https://martini-cell-frontend.vercel.app"

    url = f"{base_url}/consulta"
    normalized_code = str(tracking_code or "").strip().upper()

    if normalized_code:
        return (
            f"{url}?codigo="
            f"{quote(normalized_code, safe='')}"
        )

    return url


def _chat_notification_text(order):
    return (
        "Hola. Martini Cell tiene una nueva respuesta para tu orden "
        f"{order.tracking_code}. "
        "Puedes revisarla directamente en: "
        f"{_public_tracking_url(order.tracking_code)}"
    )


def _chat_notification_email_body(order):
    return (
        "MARTINI CELL\n\n"
        "Tienes una nueva respuesta en el chat de tu orden.\n\n"
        f"Código de orden y seguimiento: {order.tracking_code}\n"
        f"Consulta: {_public_tracking_url(order.tracking_code)}\n\n"
        "Por seguridad, este correo no incluye el contenido del mensaje. "
        "Ingresa a la consulta pública y utiliza tu código de seguimiento "
        "para revisar la conversación.\n"
    )


def _serialize_chat_notification(notification):
    return {
        "id": notification.id,
        "message": notification.message_id,
        "channel": notification.channel,
        "channel_display": notification.get_channel_display(),
        "status": notification.status,
        "status_display": notification.get_status_display(),
        "destination": notification.destination,
        "prepared_message": notification.prepared_message,
        "action_url": notification.action_url,
        "detail": notification.detail,
        "created_at": notification.created_at,
    }


def _notify_chat_reply(message, user):
    """
    Procesa la notificación después de que la respuesta del chat ya fue
    confirmada en base de datos. Nunca debe borrar ni revertir el mensaje.
    """
    conversation = message.conversation
    order = conversation.order
    channel = order.preferred_notification_channel

    if not channel:
        return {
            "status": "FAILED",
            "channel": "",
            "detail": (
                "La respuesta fue guardada, pero la orden no tiene un "
                "canal preferido de notificaciones configurado."
            ),
        }

    existing = (
        OrderChatNotification.objects
        .filter(
            message=message,
            channel=channel,
        )
        .select_related("triggered_by")
        .first()
    )

    if existing is not None:
        result = _serialize_chat_notification(existing)
        result["duplicate_prevented"] = True
        return result

    common_values = {
        "order": order,
        "conversation": conversation,
        "message": message,
        "channel": channel,
        "triggered_by": user,
    }

    if channel == ServiceOrder.NotificationChannel.EMAIL:
        destination = (order.client.email or "").strip()

        if not destination:
            notification = OrderChatNotification.objects.create(
                **common_values,
                status=OrderChatNotification.Status.FAILED,
                destination="",
                detail=(
                    "La respuesta fue guardada, pero el cliente no tiene "
                    "un correo electrónico registrado."
                ),
            )
            return _serialize_chat_notification(notification)

        try:
            email = EmailMessage(
                subject=(
                    "Martini Cell - Nueva respuesta "
                    f"{order.tracking_code}"
                ),
                body=_chat_notification_email_body(order),
                to=[destination],
            )
            sent_count = email.send(using="default")

            if sent_count != 1:
                raise RuntimeError(
                    "El servicio de correo no confirmó el envío."
                )

        except Exception as error:
            notification = OrderChatNotification.objects.create(
                **common_values,
                status=OrderChatNotification.Status.FAILED,
                destination=destination,
                detail=str(error)[:1000],
            )
            return _serialize_chat_notification(notification)

        notification = OrderChatNotification.objects.create(
            **common_values,
            status=OrderChatNotification.Status.SENT,
            destination=destination,
            detail=(
                "Aviso de nueva respuesta enviado por correo electrónico."
            ),
        )
        return _serialize_chat_notification(notification)

    if channel == ServiceOrder.NotificationChannel.WHATSAPP:
        destination = _whatsapp_number(order.client.phone)

        if not destination:
            notification = OrderChatNotification.objects.create(
                **common_values,
                status=OrderChatNotification.Status.FAILED,
                destination="",
                detail=(
                    "La respuesta fue guardada, pero el cliente no tiene "
                    "un teléfono registrado para WhatsApp."
                ),
            )
            return _serialize_chat_notification(notification)

        cloud_api_enabled = bool(
            getattr(
                settings,
                "WHATSAPP_CLOUD_API_ENABLED",
                False,
            )
        )
        cloud_api_error = ""

        if cloud_api_enabled:
            template_name = (
                getattr(
                    settings,
                    "WHATSAPP_TEMPLATE_CHAT_REPLY",
                    "",
                )
                or ""
            ).strip()

            try:
                send_result = send_template_message(
                    to=destination,
                    template_name=template_name,
                    body_parameters=[
                        order.tracking_code,
                    ],
                    language_code=getattr(
                        settings,
                        "WHATSAPP_TEMPLATE_LANGUAGE",
                        "es_CL",
                    ),
                )
            except WhatsAppCloudError as error:
                cloud_api_error = str(error)[:700]

                if not bool(
                    getattr(
                        settings,
                        "WHATSAPP_CLOUD_FALLBACK_TO_WA_ME",
                        False,
                    )
                ):
                    notification = OrderChatNotification.objects.create(
                        **common_values,
                        status=OrderChatNotification.Status.FAILED,
                        destination=destination,
                        detail=(
                            "La respuesta del chat fue guardada, pero no fue "
                            "posible enviar el aviso mediante WhatsApp "
                            f"Cloud API. {cloud_api_error}"
                        )[:1000],
                    )
                    return _serialize_chat_notification(notification)
            else:
                notification = OrderChatNotification.objects.create(
                    **common_values,
                    status=OrderChatNotification.Status.SENT,
                    destination=send_result.destination,
                    detail=(
                        "Aviso de nueva respuesta enviado mediante "
                        "WhatsApp Cloud API. "
                        f"ID de Meta: {send_result.message_id}."
                    )[:1000],
                )
                return _serialize_chat_notification(notification)

        prepared_message = _chat_notification_text(order)
        action_url = (
            f"https://wa.me/{destination}"
            f"?text={quote(prepared_message)}"
        )

        if cloud_api_error:
            detail = (
                "WhatsApp Cloud API no pudo completar el envío. "
                "Se preparó el respaldo manual mediante wa.me. "
                f"{cloud_api_error}"
            )[:1000]
        else:
            detail = (
                "Aviso de WhatsApp preparado para envío manual. "
                "WhatsApp Cloud API aún no está habilitada. "
                "La respuesta del chat ya quedó guardada."
            )

        notification = OrderChatNotification.objects.create(
            **common_values,
            status=OrderChatNotification.Status.PREPARED,
            destination=destination,
            prepared_message=prepared_message,
            action_url=action_url,
            detail=detail,
        )
        return _serialize_chat_notification(notification)

    return {
        "status": "FAILED",
        "channel": channel,
        "detail": (
            "La respuesta fue guardada, pero el canal preferido "
            "configurado no es compatible."
        ),
    }


# HU-35: chat público e interno asociado a una orden.
def _chat_conversation_queryset():
    return (
        OrderChatConversation.objects
        .select_related(
            "order",
            "order__client",
            "order__equipment",
            "closed_by",
        )
        .prefetch_related(
            Prefetch(
                "messages",
                queryset=(
                    OrderChatMessage.objects
                    .select_related("sender_user")
                    .order_by("created_at", "id")
                ),
            )
        )
    )


def _get_public_order_by_tracking_code(tracking_code):
    return get_object_or_404(
        ServiceOrder.objects.select_related(
            "client",
            "equipment",
        ),
        tracking_code__iexact=(tracking_code or "").strip(),
    )


def _get_chat_conversation(pk):
    return get_object_or_404(
        _chat_conversation_queryset(),
        pk=pk,
    )


def _mark_chat_read_by_client(conversation):
    OrderChatMessage.objects.filter(
        conversation=conversation,
        sender_type=OrderChatMessage.SenderType.STAFF,
        read_by_client_at__isnull=True,
    ).update(
        read_by_client_at=timezone.now()
    )


def _mark_chat_read_by_staff(conversation):
    OrderChatMessage.objects.filter(
        conversation=conversation,
        sender_type=OrderChatMessage.SenderType.CLIENT,
        read_by_staff_at__isnull=True,
    ).update(
        read_by_staff_at=timezone.now()
    )


class PublicOrderChatView(APIView):
    """
    Chat del cliente usando únicamente el tracking_code existente.

    La respuesta pública se limita al estado del chat y sus mensajes.
    No expone usuarios internos, datos financieros, notas privadas ni
    otros detalles de la orden.
    """

    permission_classes = [AllowAny]

    def get(self, request, tracking_code):
        order = _get_public_order_by_tracking_code(
            tracking_code
        )

        try:
            conversation = order.chat_conversation
        except OrderChatConversation.DoesNotExist:
            return Response(
                {
                    "tracking_code": order.tracking_code,
                    "status": None,
                    "status_display": "Sin conversación",
                    "created_at": None,
                    "updated_at": None,
                    "messages": [],
                }
            )

        _mark_chat_read_by_client(conversation)

        conversation = (
            _chat_conversation_queryset()
            .get(pk=conversation.pk)
        )

        return Response(
            OrderChatPublicConversationSerializer(
                conversation
            ).data
        )

    @transaction.atomic
    def post(self, request, tracking_code):
        order = get_object_or_404(
            ServiceOrder.objects.select_for_update(),
            tracking_code__iexact=(tracking_code or "").strip(),
        )

        request_serializer = OrderChatMessageCreateSerializer(
            data=request.data
        )
        request_serializer.is_valid(raise_exception=True)

        conversation, created = (
            OrderChatConversation.objects
            .select_for_update()
            .get_or_create(
                order=order,
                defaults={
                    "status": OrderChatConversation.Status.NEW,
                },
            )
        )

        if (
            conversation.status
            == OrderChatConversation.Status.CLOSED
        ):
            return Response(
                {
                    "detail": (
                        "Esta conversación está cerrada. "
                        "Martini Cell debe reabrirla antes de "
                        "recibir nuevos mensajes."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Si Martini Cell ya había respondido, un nuevo mensaje del
        # cliente vuelve a dejar la conversación pendiente.
        if (
            not created
            and conversation.status
            == OrderChatConversation.Status.ANSWERED
        ):
            conversation.status = (
                OrderChatConversation.Status.PENDING
            )
            conversation.save(
                update_fields=[
                    "status",
                    "closed_at",
                    "closed_by",
                    "updated_at",
                ]
            )

        OrderChatMessage.objects.create(
            conversation=conversation,
            sender_type=OrderChatMessage.SenderType.CLIENT,
            sender_user=None,
            body=request_serializer.validated_data["body"],
        )

        conversation = (
            _chat_conversation_queryset()
            .get(pk=conversation.pk)
        )

        return Response(
            OrderChatPublicConversationSerializer(
                conversation
            ).data,
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )


class OrderChatConversationListView(APIView):
    """
    Bandeja interna de conversaciones para ADMIN y TECH.
    """

    permission_classes = [
        IsAuthenticated,
        IsAdminOrTechRole,
    ]

    def get(self, request):
        conversations = (
            OrderChatConversation.objects
            .select_related(
                "order",
                "order__client",
                "order__equipment",
            )
            .prefetch_related(
                Prefetch(
                    "messages",
                    queryset=(
                        OrderChatMessage.objects
                        .select_related("sender_user")
                        .order_by("created_at", "id")
                    ),
                )
            )
            .annotate(
                unread_staff_count=Count(
                    "messages",
                    filter=Q(
                        messages__sender_type=(
                            OrderChatMessage.SenderType.CLIENT
                        ),
                        messages__read_by_staff_at__isnull=True,
                    ),
                )
            )
            .order_by("-updated_at", "-id")
        )

        requested_status = (
            request.query_params.get("status", "")
            .strip()
            .upper()
        )

        if requested_status:
            valid_statuses = {
                choice
                for choice, _ in (
                    OrderChatConversation.Status.choices
                )
            }

            if requested_status not in valid_statuses:
                return Response(
                    {
                        "detail": (
                            "El estado indicado no es válido."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            conversations = conversations.filter(
                status=requested_status
            )

        unread_only = (
            request.query_params.get("unread", "")
            .strip()
            .lower()
        )

        if unread_only in {"1", "true", "yes", "on"}:
            conversations = conversations.filter(
                unread_staff_count__gt=0
            )

        serializer = OrderChatConversationListSerializer(
            conversations,
            many=True,
        )

        return Response(serializer.data)

    def post(self, request):
        """
        HU-38: permite a ADMIN/TECH iniciar una conversación usando el
        tracking_code de una orden, aunque el cliente nunca haya escrito.

        Si la conversación ya existe, se reutiliza para conservar un único
        historial por orden. La notificación se procesa después de confirmar
        el mensaje para que un fallo de EMAIL/WhatsApp no lo revierta.
        """
        tracking_code = str(
            request.data.get("tracking_code") or ""
        ).strip().upper()

        if not tracking_code:
            return Response(
                {
                    "detail": (
                        "Ingresa el código de orden para iniciar "
                        "la conversación."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        request_serializer = OrderChatMessageCreateSerializer(
            data={
                "body": request.data.get("body", ""),
            }
        )
        request_serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            order = get_object_or_404(
                ServiceOrder.objects
                .select_for_update()
                .select_related(
                    "client",
                    "equipment",
                ),
                tracking_code__iexact=tracking_code,
            )

            conversation, created = (
                OrderChatConversation.objects
                .select_for_update()
                .get_or_create(
                    order=order,
                    defaults={
                        "status": (
                            OrderChatConversation.Status.ANSWERED
                        ),
                    },
                )
            )

            if (
                conversation.status
                == OrderChatConversation.Status.CLOSED
            ):
                return Response(
                    {
                        "detail": (
                            "La conversación de esta orden está cerrada. "
                            "Reábrela antes de enviar un nuevo mensaje."
                        ),
                        "conversation_id": conversation.id,
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            _mark_chat_read_by_staff(conversation)

            message = OrderChatMessage.objects.create(
                conversation=conversation,
                sender_type=OrderChatMessage.SenderType.STAFF,
                sender_user=request.user,
                body=request_serializer.validated_data["body"],
            )

            conversation.status = (
                OrderChatConversation.Status.ANSWERED
            )
            conversation.save(
                update_fields=[
                    "status",
                    "closed_at",
                    "closed_by",
                    "updated_at",
                ]
            )

        notification_result = _notify_chat_reply(
            message,
            request.user,
        )

        conversation = _get_chat_conversation(
            conversation.pk
        )

        response_data = dict(
            OrderChatConversationDetailSerializer(
                conversation
            ).data
        )
        response_data["conversation_created"] = created
        response_data["public_tracking_url"] = (
            _public_tracking_url(order.tracking_code)
        )
        response_data["notification_result"] = (
            notification_result
        )

        return Response(
            response_data,
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )


class OrderChatConversationDetailView(APIView):
    """
    Consulta y respuesta interna de una conversación.
    Abrir el detalle marca como leídos los mensajes del cliente.
    """

    permission_classes = [
        IsAuthenticated,
        IsAdminOrTechRole,
    ]

    def get(self, request, pk):
        conversation = _get_chat_conversation(pk)

        _mark_chat_read_by_staff(conversation)

        conversation = _get_chat_conversation(pk)

        return Response(
            OrderChatConversationDetailSerializer(
                conversation
            ).data
        )

    def post(self, request, pk):
        request_serializer = OrderChatMessageCreateSerializer(
            data=request.data
        )
        request_serializer.is_valid(raise_exception=True)

        # La respuesta y el estado del chat se confirman primero.
        # La notificación se procesa después para que un fallo del canal
        # nunca revierta ni elimine el mensaje ya enviado.
        with transaction.atomic():
            conversation = get_object_or_404(
                OrderChatConversation.objects
                .select_for_update()
                .select_related(
                    "order",
                    "order__client",
                ),
                pk=pk,
            )

            if (
                conversation.status
                == OrderChatConversation.Status.CLOSED
            ):
                return Response(
                    {
                        "detail": (
                            "La conversación está cerrada. "
                            "Reábrela antes de responder."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            # Al responder, todo lo que estaba pendiente del cliente
            # queda leído por el personal que está atendiendo el chat.
            _mark_chat_read_by_staff(conversation)

            message = OrderChatMessage.objects.create(
                conversation=conversation,
                sender_type=OrderChatMessage.SenderType.STAFF,
                sender_user=request.user,
                body=request_serializer.validated_data["body"],
            )

            conversation.status = (
                OrderChatConversation.Status.ANSWERED
            )
            conversation.save(
                update_fields=[
                    "status",
                    "closed_at",
                    "closed_by",
                    "updated_at",
                ]
            )

        notification_result = _notify_chat_reply(
            message,
            request.user,
        )

        conversation = _get_chat_conversation(pk)

        response_data = dict(
            OrderChatConversationDetailSerializer(
                conversation
            ).data
        )
        response_data["public_tracking_url"] = (
            _public_tracking_url(
                conversation.order.tracking_code
            )
        )
        response_data["notification_result"] = notification_result

        return Response(
            response_data,
            status=status.HTTP_201_CREATED,
        )


class OrderChatConversationStatusView(APIView):
    """
    Cierra o reabre una conversación sin perder mensajes.

    Los estados NEW/PENDING/ANSWERED se administran por actividad del
    chat; desde este endpoint solo se permite cerrar o reabrir.
    """

    permission_classes = [
        IsAuthenticated,
        IsAdminOrTechRole,
    ]

    @transaction.atomic
    def patch(self, request, pk):
        request_serializer = OrderChatStatusUpdateSerializer(
            data=request.data
        )
        request_serializer.is_valid(raise_exception=True)

        new_status = request_serializer.validated_data[
            "status"
        ]

        conversation = get_object_or_404(
            OrderChatConversation.objects
            .select_for_update()
            .select_related("order"),
            pk=pk,
        )

        if (
            conversation.status
            == OrderChatConversation.Status.CLOSED
        ):
            if (
                new_status
                != OrderChatConversation.Status.PENDING
            ):
                return Response(
                    {
                        "detail": (
                            "Una conversación cerrada solo puede "
                            "reabrirse como Pendiente de respuesta."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            conversation.status = (
                OrderChatConversation.Status.PENDING
            )
            conversation.closed_at = None
            conversation.closed_by = None

        else:
            if (
                new_status
                != OrderChatConversation.Status.CLOSED
            ):
                return Response(
                    {
                        "detail": (
                            "El estado operativo del chat cambia "
                            "automáticamente con los mensajes. "
                            "Desde esta acción solo puedes cerrar "
                            "la conversación."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            conversation.status = (
                OrderChatConversation.Status.CLOSED
            )
            conversation.closed_at = timezone.now()
            conversation.closed_by = request.user

        conversation.save(
            update_fields=[
                "status",
                "closed_at",
                "closed_by",
                "updated_at",
            ]
        )

        conversation = _get_chat_conversation(pk)

        return Response(
            OrderChatConversationDetailSerializer(
                conversation
            ).data
        )


# HU-27: historial inmutable de cambios sensibles de la orden.
class OrderSensitiveChangeHistoryView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsAdminOrTechRole,
    ]

    def get(self, request, pk):
        order = get_object_or_404(
            ServiceOrder,
            pk=pk,
        )

        history = (
            OrderSensitiveChangeHistory.objects
            .filter(order=order)
            .select_related("changed_by")
            .order_by("changed_at", "id")
        )

        serializer = OrderSensitiveChangeHistorySerializer(
            history,
            many=True,
        )

        return Response(serializer.data)


# HU-37: notificaciones automáticas por cambios de estado de la orden.
def _status_notification_text(order, status_history):
    new_status_display = ServiceOrder.Status(
        status_history.to_status
    ).label

    return (
        "Hola. Martini Cell informa que tu orden "
        f"{order.tracking_code} cambió de estado a "
        f"\"{new_status_display}\". "
        "Puedes revisar el seguimiento directamente en: "
        f"{_public_tracking_url(order.tracking_code)}"
    )


def _status_notification_email_body(order, status_history):
    new_status_display = ServiceOrder.Status(
        status_history.to_status
    ).label

    return (
        "MARTINI CELL\n\n"
        "El estado de tu orden fue actualizado.\n\n"
        f"Código de orden y seguimiento: {order.tracking_code}\n"
        f"Nuevo estado: {new_status_display}\n"
        f"Consulta: {_public_tracking_url(order.tracking_code)}\n\n"
        "Por seguridad, este correo no incluye notas internas, costos "
        "ni detalles técnicos privados. Ingresa a la consulta pública "
        "y utiliza el mismo código de seguimiento para revisar el avance.\n"
    )


def _serialize_status_notification(notification):
    return {
        "id": notification.id,
        "status_history": notification.status_history_id,
        "channel": notification.channel,
        "channel_display": notification.get_channel_display(),
        "status": notification.status,
        "status_display": notification.get_status_display(),
        "destination": notification.destination,
        "prepared_message": notification.prepared_message,
        "action_url": notification.action_url,
        "detail": notification.detail,
        "created_at": notification.created_at,
    }


def _notify_status_change(status_history, user):
    """
    Procesa la notificación únicamente después de confirmar el cambio
    de estado y su historial. Un fallo del canal no revierte la transición.
    """
    order = status_history.order
    channel = order.preferred_notification_channel

    if not channel:
        return {
            "status": "FAILED",
            "channel": "",
            "detail": (
                "El estado fue actualizado, pero la orden no tiene un "
                "canal preferido de notificaciones configurado."
            ),
        }

    existing = (
        OrderStatusNotification.objects
        .filter(
            status_history=status_history,
            channel=channel,
        )
        .select_related("triggered_by")
        .first()
    )

    if existing is not None:
        result = _serialize_status_notification(existing)
        result["duplicate_prevented"] = True
        return result

    common_values = {
        "order": order,
        "status_history": status_history,
        "channel": channel,
        "triggered_by": user,
    }

    if channel == ServiceOrder.NotificationChannel.EMAIL:
        destination = (order.client.email or "").strip()

        if not destination:
            notification = OrderStatusNotification.objects.create(
                **common_values,
                status=OrderStatusNotification.Status.FAILED,
                destination="",
                detail=(
                    "El estado fue actualizado, pero el cliente no tiene "
                    "un correo electrónico registrado."
                ),
            )
            return _serialize_status_notification(notification)

        try:
            email = EmailMessage(
                subject=(
                    "Martini Cell - Estado actualizado "
                    f"{order.tracking_code}"
                ),
                body=_status_notification_email_body(
                    order,
                    status_history,
                ),
                to=[destination],
            )
            sent_count = email.send(using="default")

            if sent_count != 1:
                raise RuntimeError(
                    "El servicio de correo no confirmó el envío."
                )

        except Exception as error:
            notification = OrderStatusNotification.objects.create(
                **common_values,
                status=OrderStatusNotification.Status.FAILED,
                destination=destination,
                detail=str(error)[:1000],
            )
            return _serialize_status_notification(notification)

        notification = OrderStatusNotification.objects.create(
            **common_values,
            status=OrderStatusNotification.Status.SENT,
            destination=destination,
            detail=(
                "Aviso de cambio de estado enviado por correo electrónico."
            ),
        )
        return _serialize_status_notification(notification)

    if channel == ServiceOrder.NotificationChannel.WHATSAPP:
        destination = _whatsapp_number(order.client.phone)

        if not destination:
            notification = OrderStatusNotification.objects.create(
                **common_values,
                status=OrderStatusNotification.Status.FAILED,
                destination="",
                detail=(
                    "El estado fue actualizado, pero el cliente no tiene "
                    "un teléfono registrado para WhatsApp."
                ),
            )
            return _serialize_status_notification(notification)

        cloud_api_enabled = bool(
            getattr(
                settings,
                "WHATSAPP_CLOUD_API_ENABLED",
                False,
            )
        )
        cloud_api_error = ""

        if cloud_api_enabled:
            template_name = (
                getattr(
                    settings,
                    "WHATSAPP_TEMPLATE_STATUS_CHANGE",
                    "",
                )
                or ""
            ).strip()

            new_status_display = ServiceOrder.Status(
                status_history.to_status
            ).label

            try:
                send_result = send_template_message(
                    to=destination,
                    template_name=template_name,
                    body_parameters=[
                        order.tracking_code,
                        new_status_display,
                    ],
                    language_code=getattr(
                        settings,
                        "WHATSAPP_TEMPLATE_LANGUAGE",
                        "es_CL",
                    ),
                )
            except WhatsAppCloudError as error:
                cloud_api_error = str(error)[:700]

                if not bool(
                    getattr(
                        settings,
                        "WHATSAPP_CLOUD_FALLBACK_TO_WA_ME",
                        False,
                    )
                ):
                    notification = (
                        OrderStatusNotification.objects.create(
                            **common_values,
                            status=(
                                OrderStatusNotification.Status.FAILED
                            ),
                            destination=destination,
                            detail=(
                                "El estado fue actualizado, pero no fue "
                                "posible enviar el aviso mediante WhatsApp "
                                f"Cloud API. {cloud_api_error}"
                            )[:1000],
                        )
                    )
                    return _serialize_status_notification(
                        notification
                    )
            else:
                notification = OrderStatusNotification.objects.create(
                    **common_values,
                    status=OrderStatusNotification.Status.SENT,
                    destination=send_result.destination,
                    detail=(
                        "Aviso de cambio de estado enviado mediante "
                        "WhatsApp Cloud API. "
                        f"ID de Meta: {send_result.message_id}."
                    )[:1000],
                )
                return _serialize_status_notification(notification)

        prepared_message = _status_notification_text(
            order,
            status_history,
        )
        action_url = (
            f"https://wa.me/{destination}"
            f"?text={quote(prepared_message)}"
        )

        if cloud_api_error:
            detail = (
                "WhatsApp Cloud API no pudo completar el envío. "
                "Se preparó el respaldo manual mediante wa.me. "
                f"{cloud_api_error}"
            )[:1000]
        else:
            detail = (
                "Aviso de WhatsApp preparado para envío manual. "
                "WhatsApp Cloud API aún no está habilitada. "
                "El cambio de estado ya quedó guardado."
            )

        notification = OrderStatusNotification.objects.create(
            **common_values,
            status=OrderStatusNotification.Status.PREPARED,
            destination=destination,
            prepared_message=prepared_message,
            action_url=action_url,
            detail=detail,
        )
        return _serialize_status_notification(notification)

    return {
        "status": "FAILED",
        "channel": channel,
        "detail": (
            "El estado fue actualizado, pero el canal preferido "
            "configurado no es compatible."
        ),
    }


class OrderStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(
            ServiceOrder,
            pk=pk,
        )

        return Response(
            get_order_status_data(order)
        )

    def patch(self, request, pk):
        if request.user.role not in {"ADMIN", "TECH"}:
            return Response(
                {
                    "detail": (
                        "No tienes permiso para cambiar "
                        "el estado de una orden."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OrderStatusChangeSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        new_status = serializer.validated_data["status"]
        note = serializer.validated_data.get(
            "note",
            "",
        )

        # Primero se confirman la transición y su historial. La
        # notificación se procesa fuera de esta transacción para que
        # un fallo de EMAIL/WhatsApp nunca revierta el nuevo estado.
        with transaction.atomic():
            order = get_object_or_404(
                ServiceOrder.objects
                .select_for_update()
                .select_related("client"),
                pk=pk,
            )

            previous_status = order.status

            allowed = STATUS_TRANSITIONS.get(
                previous_status,
                (),
            )

            if new_status not in allowed:
                return Response(
                    {
                        "detail": (
                            "No está permitido cambiar el estado "
                            f"de {order.get_status_display()} "
                            f"a {ServiceOrder.Status(new_status).label}."
                        ),
                        "current_status": previous_status,
                        "allowed_transitions": list(allowed),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            order.status = new_status
            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            status_history = OrderStatusHistory.objects.create(
                order=order,
                from_status=previous_status,
                to_status=new_status,
                note=note,
                changed_by=request.user,
            )

        notification_result = _notify_status_change(
            status_history,
            request.user,
        )

        response_data = get_order_status_data(order)
        response_data["notification_result"] = notification_result

        return Response(response_data)


class OrderStatusHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(
            ServiceOrder,
            pk=pk,
        )

        history = (
            OrderStatusHistory.objects
            .filter(order=order)
            .select_related("changed_by")
            .prefetch_related(
                Prefetch(
                    "notifications",
                    queryset=(
                        OrderStatusNotification.objects
                        .select_related("triggered_by")
                        .order_by("created_at", "id")
                    ),
                )
            )
            .order_by("changed_at", "id")
        )

        serializer = OrderStatusHistorySerializer(
            history,
            many=True,
        )

        return Response(serializer.data)


class OrderTimesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(
            ServiceOrder,
            pk=pk,
        )

        try:
            result = calculate_order_times(order)
        except ValueError as error:
            return Response(
                {
                    "detail": str(error),
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(result)


class OrderEvidenceListCreateView(ListCreateAPIView):
    serializer_class = OrderEvidenceSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_order(self):
        return get_object_or_404(
            ServiceOrder,
            pk=self.kwargs["pk"],
        )

    def get_queryset(self):
        order = self.get_order()

        return (
            OrderEvidence.objects
            .filter(order=order)
            .select_related("uploaded_by", "order")
            .order_by("created_at")
        )

    def perform_create(self, serializer):
        serializer.save(
            order=self.get_order(),
            uploaded_by=self.request.user,
        )


class OrderEvidenceDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, evidence_id):
        evidence = get_object_or_404(
            OrderEvidence,
            pk=evidence_id,
            order_id=pk,
        )

        evidence.image.open("rb")

        content_type, _ = mimetypes.guess_type(
            evidence.image.name
        )

        response = FileResponse(
            evidence.image,
            content_type=content_type or "application/octet-stream",
        )

        response["Content-Disposition"] = (
            f'inline; filename="evidence-{evidence.id}"'
        )

        return response


class OrderTechnicalReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get_order(self, pk):
        return get_object_or_404(
            ServiceOrder,
            pk=pk,
        )

    def can_modify(self, user):
        return user.role in {
            "ADMIN",
            "TECH",
        }

    def get(self, request, pk):
        order = self.get_order(pk)

        report = get_object_or_404(
            OrderTechnicalReport.objects.select_related(
                "order",
                "technician",
                "created_by",
                "updated_by",
            ),
            order=order,
        )

        serializer = OrderTechnicalReportSerializer(
            report
        )

        return Response(serializer.data)

    @transaction.atomic
    def post(self, request, pk):
        if not self.can_modify(request.user):
            return Response(
                {
                    "detail": (
                        "No tienes permiso para registrar "
                        "un informe técnico."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        order = get_object_or_404(
            ServiceOrder.objects.select_for_update(),
            pk=pk,
        )

        if order.status in {
            ServiceOrder.Status.DELIVERED,
            ServiceOrder.Status.CLOSED,
        }:
            return Response(
                {
                    "detail": (
                        "No se puede registrar un informe técnico "
                        "en una orden entregada o cerrada."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if OrderTechnicalReport.objects.filter(
            order=order
        ).exists():
            return Response(
                {
                    "detail": (
                        "La orden ya posee un informe técnico."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OrderTechnicalReportSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        report = serializer.save(
            order=order,
            created_by=request.user,
            updated_by=request.user,
        )

        response_serializer = (
            OrderTechnicalReportSerializer(report)
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @transaction.atomic
    def patch(self, request, pk):
        if not self.can_modify(request.user):
            return Response(
                {
                    "detail": (
                        "No tienes permiso para modificar "
                        "un informe técnico."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        order = get_object_or_404(
            ServiceOrder.objects.select_for_update(),
            pk=pk,
        )

        if order.status in {
            ServiceOrder.Status.DELIVERED,
            ServiceOrder.Status.CLOSED,
        }:
            return Response(
                {
                    "detail": (
                        "No se puede modificar un informe técnico "
                        "en una orden entregada o cerrada."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        report = get_object_or_404(
            OrderTechnicalReport,
            order=order,
        )

        serializer = OrderTechnicalReportSerializer(
            report,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True
        )

        report = serializer.save(
            updated_by=request.user
        )

        response_serializer = (
            OrderTechnicalReportSerializer(report)
        )

        return Response(
            response_serializer.data
        )


class OrderTechnicalReportHistoryView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsAdminOrTechRole,
    ]

    def get(self, request, pk):
        order = get_object_or_404(
            ServiceOrder,
            pk=pk,
        )

        report = get_object_or_404(
            OrderTechnicalReport,
            order=order,
        )

        history = (
            report.history
            .select_related(
                "technician",
                "changed_by",
            )
            .order_by("revision")
        )

        serializer = (
            OrderTechnicalReportHistorySerializer(
                history,
                many=True,
            )
        )

        return Response(serializer.data)
