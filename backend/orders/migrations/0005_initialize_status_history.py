from django.db import migrations


INITIAL_NOTE = (
    "Registro inicial al incorporar el seguimiento de estados "
    "(HU-10). No representa una transicion historica."
)


def initialize_status_history(apps, schema_editor):
    ServiceOrder = apps.get_model(
        "orders",
        "ServiceOrder",
    )

    OrderStatusHistory = apps.get_model(
        "orders",
        "OrderStatusHistory",
    )

    database = schema_editor.connection.alias

    existing_orders = ServiceOrder.objects.using(
        database
    ).all()

    initial_records = []

    for order in existing_orders:
        initial_records.append(
            OrderStatusHistory(
                order_id=order.id,
                from_status=None,
                to_status=order.status,
                note=INITIAL_NOTE,
                changed_by_id=None,
            )
        )

    OrderStatusHistory.objects.using(
        database
    ).bulk_create(
        initial_records,
        batch_size=500,
    )


def reverse_status_history(apps, schema_editor):
    OrderStatusHistory = apps.get_model(
        "orders",
        "OrderStatusHistory",
    )

    database = schema_editor.connection.alias

    OrderStatusHistory.objects.using(
        database
    ).filter(
        from_status__isnull=True,
        to_status="RECEIVED",
        note=INITIAL_NOTE,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        (
            "orders",
            "0004_serviceorder_status_orderstatushistory",
        ),
    ]

    operations = [
        migrations.RunPython(
            initialize_status_history,
            reverse_status_history,
        ),
    ]