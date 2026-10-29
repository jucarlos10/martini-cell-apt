from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0003_client_optional_rut"),
        ("orders", "0014_intake_price"),
    ]

    operations = [
        migrations.AlterField(
            model_name="warrantyrequest",
            name="client_rut_snapshot",
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=20,
            ),
        ),
    ]
