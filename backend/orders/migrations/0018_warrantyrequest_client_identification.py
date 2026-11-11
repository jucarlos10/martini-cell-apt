# Generated for flexible client identification snapshots in warranty requests.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0017_orderstatusnotification"),
    ]

    operations = [
        migrations.AddField(
            model_name="warrantyrequest",
            name="client_identification_number_snapshot",
            field=models.CharField(
                blank=True,
                default="",
                editable=False,
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="warrantyrequest",
            name="client_identification_type_snapshot",
            field=models.CharField(
                blank=True,
                default="",
                editable=False,
                max_length=20,
            ),
        ),
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
