import csv
import io
import tempfile
import unittest
from pathlib import Path

from validate_ml_dataset import FIELDS, validate_file


class ValidateMlDatasetTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "casos.csv"
        self.row = {
            "case_id": "741c1cfe-2bf5-4f4c-8efd-9e5b903a03ea",
            "origin": "MARTINI",
            "source_verified": "SI",
            "review_status": "VALIDADO",
            "anonymized": "SI",
            "final_status": "DELIVERED",
            "repair_result": "REPARADO",
            "equipment_type": "CELULAR",
            "issue_category_at_intake": "CARGA",
            "finished_on": "2026-09-01",
            "technical_minutes": "73.5",
            "waiting_minutes": "0",
            "time_basis": "MANUAL_VERIFIED",
        }

    def write_rows(self, rows, fields=FIELDS):
        with self.path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def check(self):
        output = io.StringIO()
        valid = validate_file(self.path, output)
        return valid, output.getvalue()

    def test_public_template_uses_the_validator_contract(self):
        template = Path(__file__).resolve().parents[1] / "docs/templates/ml_cases_v1.csv"
        with template.open(encoding="utf-8", newline="") as file:
            self.assertEqual(next(csv.reader(file)), list(FIELDS))
            self.assertEqual(list(csv.reader(file)), [])

    def test_valid_private_export_passes_without_printing_case_id(self):
        self.write_rows([self.row])
        valid, output = self.check()
        self.assertTrue(valid)
        self.assertIn("conformes: 1", output)
        self.assertNotIn(self.row["case_id"], output)

    def test_duplicate_and_unconfirmed_cases_are_rejected_without_values(self):
        other = dict(self.row, source_verified="NO", review_status="PENDIENTE")
        self.write_rows([self.row, other])
        valid, output = self.check()
        self.assertFalse(valid)
        self.assertIn("case_id:duplicado", output)
        self.assertIn("source_verified:valor_no_permitido", output)
        self.assertIn("review_status:valor_no_permitido", output)
        self.assertNotIn(self.row["case_id"], output)

    def test_bad_measurements_and_future_or_invalid_dates_are_rejected(self):
        other = dict(
            self.row,
            technical_minutes="0",
            waiting_minutes="-1",
            finished_on="2999-01-01",
            final_status="RECEIVED",
        )
        self.write_rows([other])
        valid, output = self.check()
        self.assertFalse(valid)
        self.assertIn("technical_minutes:fuera_de_rango", output)
        self.assertIn("waiting_minutes:numero_invalido", output)
        self.assertIn("finished_on:fecha_futura", output)
        self.assertIn("final_status:valor_no_permitido", output)

    def test_unexpected_personal_data_column_is_rejected_without_echo(self):
        self.write_rows([dict(self.row, customer_phone="912345678")], (*FIELDS, "customer_phone"))
        valid, output = self.check()
        self.assertFalse(valid)
        self.assertIn("Encabezado inválido", output)
        self.assertNotIn("912345678", output)
        self.assertNotIn("customer_phone", output)

    def test_empty_export_is_not_treated_as_ready(self):
        self.write_rows([])
        valid, output = self.check()
        self.assertFalse(valid)
        self.assertIn("Filas revisadas: 0", output)

    def test_external_records_are_kept_out_of_local_contract(self):
        self.write_rows([dict(self.row, origin="EXTERNAL")])
        valid, output = self.check()
        self.assertFalse(valid)
        self.assertIn("origin:valor_no_permitido", output)

    def test_truncated_or_extra_cells_are_rejected(self):
        self.path.write_text(",".join(FIELDS) + "\nsolo-una-celda\n", encoding="utf-8")
        valid, output = self.check()
        self.assertFalse(valid)
        self.assertIn("cantidad_de_columnas", output)


if __name__ == "__main__":
    unittest.main()
