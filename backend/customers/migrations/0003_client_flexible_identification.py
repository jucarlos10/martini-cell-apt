# Generated for flexible client identification.

import customers.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0002_clientchangehistory"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="identification_type",
            field=models.CharField(
                choices=[
                    ("RUT", "RUT chileno"),
                    ("PASSPORT", "Pasaporte"),
                    ("FOREIGN_DOCUMENT", "Documento extranjero"),
                    ("NONE", "Sin documento"),
                ],
                default="RUT",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="client",
            name="document_number",
            field=models.CharField(
                blank=True,
                default="",
                max_length=50,
            ),
        ),
        migrations.AlterField(
            model_name="client",
            name="phone",
            field=models.CharField(
                blank=True,
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="client",
            name="rut",
            field=models.CharField(
                blank=True,
                max_length=9,
                null=True,
                unique=True,
                validators=[customers.validators.validate_rut],
            ),
        ),
        migrations.AddConstraint(
            model_name="client",
            constraint=models.UniqueConstraint(
                condition=(
                    ~models.Q(document_number="")
                    & ~models.Q(identification_type="NONE")
                ),
                fields=("identification_type", "document_number"),
                name="unique_client_document_by_type",
            ),
        ),
    ]
