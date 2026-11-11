from django.db import migrations, models


def populate_client_codes(apps, schema_editor):
    Client = apps.get_model("customers", "Client")

    for client in Client.objects.filter(
        client_code__isnull=True
    ).order_by("pk").iterator():
        Client.objects.filter(pk=client.pk).update(
            client_code=f"CLI-{client.pk:06d}"
        )


def clear_client_codes(apps, schema_editor):
    Client = apps.get_model("customers", "Client")
    Client.objects.update(client_code=None)


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0003_client_flexible_identification"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="client_code",
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=20,
                null=True,
                unique=True,
            ),
        ),
        migrations.RunPython(
            populate_client_codes,
            clear_client_codes,
        ),
    ]
