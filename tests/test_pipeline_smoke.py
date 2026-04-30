from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vfiic_kpis.excel_export import (
    write_partitioned_workbook_for_form,
    write_stacked_comparativo_workbook,
)
from vfiic_kpis.io import read_form
from vfiic_kpis.manifest import reconcile
from vfiic_kpis.metrics import build_form_comparison
from vfiic_kpis.yaml_loader import load_forms_from_yaml


SCHEMA_BODY = """
Coordinacion Periciales:

  VFIIC KPIs Periciales - Demo:
    ingesta:
      archivo: "VFIIC KPIs Periciales - Demo.xlsx"
      hoja: "Form responses"
      columna_fecha: ["Periodo Evaluado", "Periodo a Evaluar"]
      columnas_persona: ["Auxiliar"]
    kpis:
      - columna_origen: "Visitas"
        descripcion: "Visitas realizadas"
      - columna_origen: "Dictamenes"
        descripcion: "Dictamenes realizados"
"""


class TestPipelineSmoke(unittest.TestCase):
    def test_yaml_to_workbooks_minimal_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_path = root / "schema.yaml"
            schema_path.write_text(SCHEMA_BODY, encoding="utf-8")

            input_dir = root / "raw"
            input_dir.mkdir()
            df = pd.DataFrame(
                [
                    {"Periodo a Evaluar": "2026-03-01", "Auxiliar": "A", "Visitas": 2, "Dictamenes": 1},
                    {"Periodo a Evaluar": "2026-04-01", "Auxiliar": "A", "Visitas": 5, "Dictamenes": 3},
                    {"Periodo a Evaluar": "2026-04-01", "Auxiliar": "B", "Visitas": 1, "Dictamenes": 0},
                ]
            )
            df.to_excel(
                input_dir / "VFIIC KPIs Periciales - Demo.xlsx",
                index=False,
                sheet_name="Form responses",
            )

            forms = load_forms_from_yaml(schema_path)
            report = reconcile(forms, input_dir)
            self.assertEqual(len(report.matched), 1)

            resolution = report.matched[0]
            data = read_form(resolution)
            self.assertFalse(data.empty)

            comparison = build_form_comparison(data, resolution)
            self.assertIsNotNone(comparison)
            assert comparison is not None

            stacked_out = root / "comparativo.xlsx"
            partitioned_out = root / "particionado.xlsx"

            write_stacked_comparativo_workbook(results=[comparison], output_path=stacked_out)
            write_partitioned_workbook_for_form(
                data=data,
                form_id=resolution.spec.area_id,
                output_path=partitioned_out,
            )

            self.assertTrue(stacked_out.exists())
            self.assertTrue(partitioned_out.exists())


if __name__ == "__main__":
    unittest.main()
