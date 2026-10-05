"""Revisa el contrato CSV privado de HU-17 sin consultar ni modificar la BD.

Solo imprime cantidades, números de fila y códigos de error. Nunca imprime
valores de los casos, que podrían contener información sensible por accidente.
"""

import argparse
import csv
import re
import sys
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation


FIELDS = (
    "case_id",
    "origin",
    "source_verified",
    "review_status",
    "anonymized",
    "final_status",
    "repair_result",
    "equipment_type",
    "issue_category_at_intake",
    "finished_on",
    "technical_minutes",
    "waiting_minutes",
    "time_basis",
)

ALLOWED = {
    "origin": {"MARTINI"},
    "source_verified": {"SI"},
    "review_status": {"VALIDADO"},
    "anonymized": {"SI"},
    "final_status": {"DELIVERED", "CLOSED"},
    "repair_result": {"REPARADO", "PARCIAL"},
    "equipment_type": {"CELULAR", "NOTEBOOK", "PC", "TABLET", "OTRO"},
    "issue_category_at_intake": {
        "PANTALLA", "BATERIA", "CARGA", "SOFTWARE", "PLACA", "OTRA"
    },
    "time_basis": {"STATUS_HISTORY", "MANUAL_VERIFIED"},
}


def validate_row(row, seen_ids, today):
    """Devuelve códigos de error; no devuelve ni muestra valores de celdas."""
    errors = []

    if None in row or any(value is None for value in row.values()):
        return ["cantidad_de_columnas"]

    if any(len(value) > 120 for value in row.values()):
        return ["celda_demasiado_larga"]

    for field in FIELDS:
        if not row[field] or row[field] != row[field].strip():
            errors.append(f"{field}:vacio_o_espacios")

    if errors:
        return errors

    try:
        case_uuid = uuid.UUID(row["case_id"])
        if case_uuid.version != 4 or str(case_uuid) != row["case_id"]:
            raise ValueError
    except ValueError:
        errors.append("case_id:uuid4_invalido")
    else:
        if case_uuid in seen_ids:
            errors.append("case_id:duplicado")
        seen_ids.add(case_uuid)

    for field, allowed in ALLOWED.items():
        if row[field] not in allowed:
            errors.append(f"{field}:valor_no_permitido")

    raw_date = row["finished_on"]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
        errors.append("finished_on:fecha_invalida")
    else:
        try:
            finished = date.fromisoformat(raw_date)
            if finished > today:
                errors.append("finished_on:fecha_futura")
        except ValueError:
            errors.append("finished_on:fecha_invalida")

    for field, lower, upper in (
        ("technical_minutes", Decimal("0"), Decimal("10080")),
        ("waiting_minutes", Decimal("0"), Decimal("129600")),
    ):
        value = row[field]
        if not re.fullmatch(r"\d+(?:\.\d{1,2})?", value):
            errors.append(f"{field}:numero_invalido")
            continue
        try:
            number = Decimal(value)
        except InvalidOperation:
            errors.append(f"{field}:numero_invalido")
            continue
        if number < lower or number > upper or (field == "technical_minutes" and number == 0):
            errors.append(f"{field}:fuera_de_rango")

    return errors


def validate_file(path, out=sys.stdout):
    """Retorna True si el CSV cumple el contrato estructural."""
    count = 0
    failed = 0
    notices = []
    seen_ids = set()
    today = date.today()

    try:
        with open(path, encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file, strict=True)
            if reader.fieldnames != list(FIELDS):
                out.write("Encabezado inválido: use las 13 columnas del contrato v1 en el orden indicado.\n")
                return False

            for row in reader:
                count += 1
                errors = validate_row(row, seen_ids, today)
                if errors:
                    failed += 1
                    if len(notices) < 20:
                        notices.append((reader.line_num, errors))
    except (OSError, UnicodeError, csv.Error):
        out.write("No se pudo leer un CSV UTF-8 válido. Revise formato y permisos.\n")
        return False

    for line, errors in notices:
        out.write(f"Línea {line}: {', '.join(errors)}\n")
    if failed > len(notices):
        out.write(f"Otras filas con errores: {failed - len(notices)}\n")
    out.write(f"Filas revisadas: {count}; conformes: {count - failed}; con errores: {failed}.\n")
    out.write("La conformidad estructural no verifica la procedencia ni autoriza entrenar un modelo.\n")
    return count > 0 and failed == 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Valida un CSV privado para HU-17, sin escribir datos.")
    parser.add_argument("csv_path", help="Ruta local del CSV UTF-8 con los casos revisados")
    args = parser.parse_args(argv)
    return 0 if validate_file(args.csv_path) else 1


if __name__ == "__main__":
    sys.exit(main())
