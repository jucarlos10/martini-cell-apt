
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    OrderWarranty,
    OrderWarrantyHistory,
    ServiceOrder,
)


WARRANTY_FIELDS = {
    "warranty_type",
    "order_part",
    "is_applicable",
    "starts_on",
    "ends_on",
    "conditions",
}


@transaction.atomic
def save_warranty_with_history(
    *,
    order,
    user,
    validated_data,
    warranty=None,
    change_note="",
):
    """
    Crea o actualiza una garantía y registra su revisión.

    La garantía y su historial se guardan en una misma
    transacción para conservar la trazabilidad.
    """

    unexpected_fields = set(validated_data) - WARRANTY_FIELDS

    if unexpected_fields:
        raise ValidationError(
            "Se recibieron campos no permitidos para la garantía."
        )

    is_creation = warranty is None

    if not is_creation and not change_note.strip():
        raise ValidationError({
            "change_note": (
                "Indica el motivo de la modificación."
            )
        })

    # Bloquear la orden evita revisiones simultáneas
    # que puedan generar conflictos de numeración.
    locked_order = ServiceOrder.objects.select_for_update().get(
        pk=order.pk
    )

    if is_creation:
        warranty = OrderWarranty(
            order=locked_order,
            created_by=user,
        )
        action = OrderWarrantyHistory.Action.CREATED

    else:
        warranty = OrderWarranty.objects.select_for_update().get(
            pk=warranty.pk,
            order=locked_order,
        )
        action = OrderWarrantyHistory.Action.UPDATED

    for field, value in validated_data.items():
        setattr(warranty, field, value)

    warranty.updated_by = user

    # El modelo valida fechas, tipo y pertenencia del
    # repuesto a la orden antes de guardar.
    warranty.save()

    last_revision = (
        OrderWarrantyHistory.objects
        .filter(warranty=warranty)
        .order_by("-revision")
        .values_list("revision", flat=True)
        .first()
    ) or 0

    OrderWarrantyHistory.objects.create(
        warranty=warranty,
        revision=last_revision + 1,
        action=action,
        order=locked_order,
        warranty_type=warranty.warranty_type,
        order_part=warranty.order_part,
        is_applicable=warranty.is_applicable,
        starts_on=warranty.starts_on,
        ends_on=warranty.ends_on,
        conditions=warranty.conditions,
        change_note=change_note.strip(),
        changed_by=user,
        changed_by_username=user.get_username(),
    )

    return warranty