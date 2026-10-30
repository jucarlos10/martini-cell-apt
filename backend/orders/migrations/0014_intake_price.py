from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0013_ordersensitivechangehistory"),
    ]

    operations = [
        migrations.AddField(
            model_name="serviceorder",
            name="intake_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                default=None,
                max_digits=12,
                null=True,
                validators=[MinValueValidator(Decimal("0.00"))],
            ),
        ),
        migrations.AddConstraint(
            model_name="serviceorder",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(intake_price__isnull=True)
                    | models.Q(intake_price__gte=0)
                ),
                name="order_intake_price_nonnegative",
            ),
        ),
        migrations.AlterField(
            model_name="ordersensitivechangehistory",
            name="field",
            field=models.CharField(
                choices=[
                    ("CLIENT", "Cliente asociado"),
                    ("EQUIPMENT", "Equipo asociado"),
                    ("REPORTED_ISSUE", "Problema reportado"),
                    ("INITIAL_OBSERVATIONS", "Observaciones iniciales"),
                    ("INTAKE_PRICE", "Precio informado al ingreso"),
                ],
                max_length=30,
            ),
        ),
    ]
