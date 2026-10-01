from django.db import migrations, models


def backfill_warranty_ids(apps, schema_editor):
    history_model = apps.get_model("orders", "OrderWarrantyHistory")
    # Los registros cuyo vínculo ya fue puesto en NULL por una eliminación
    # previa no permiten recuperar su ID original de forma inequívoca.
    history_model.objects.using(schema_editor.connection.alias).filter(
        warranty_id__isnull=False
    ).update(warranty_id_snapshot=models.F("warranty_id"))


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0011_warrantyrequesthistory_changed_by_role_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderwarrantyhistory",
            name="warranty_id_snapshot",
            field=models.PositiveBigIntegerField(db_index=True, null=True),
        ),
        migrations.RunPython(backfill_warranty_ids, migrations.RunPython.noop),
    ]
