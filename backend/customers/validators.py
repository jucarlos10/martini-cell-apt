import re

from django.core.exceptions import ValidationError


def normalize_rut(value):
    if not value:
        return value

    return re.sub(r"[^0-9Kk]", "", value).upper()


def validate_rut(value):
    rut = normalize_rut(value)

    if len(rut) < 2:
        raise ValidationError("El RUT ingresado no es válido.")

    body = rut[:-1]
    verifier = rut[-1]

    if not body.isdigit():
        raise ValidationError("El RUT ingresado no es válido.")

    total = 0
    multiplier = 2

    for digit in reversed(body):
        total += int(digit) * multiplier
        multiplier = 2 if multiplier == 7 else multiplier + 1

    remainder = 11 - (total % 11)

    if remainder == 11:
        expected = "0"
    elif remainder == 10:
        expected = "K"
    else:
        expected = str(remainder)

    if verifier != expected:
        raise ValidationError("El dígito verificador del RUT no es válido.")
