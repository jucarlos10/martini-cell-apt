from django.db import migrations, models

import customers.validators


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0002_clientchangehistory"),
    ]

    operations = [
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
    ]
