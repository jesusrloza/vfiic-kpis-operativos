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

from vfiic_kpis.excel_export import write_comparison_v2_workbook, write_partitioned_workbook
from vfiic_kpis.io import read_all_inputs
from vfiic_kpis.metrics import build_monthly_comparison_v2
from vfiic_kpis.spec_loader import load_all_specs


class TestPipelineSmoke(unittest.TestCase):
    def test_end_to_end_minimal_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inputs = root / "inputs"
            specs_dir = inputs / "specs"
            raw_dir = inputs / "raw"
            output_dir = root / "outputs"
            specs_dir.mkdir(parents=True)
            raw_dir.mkdir(parents=True)
            output_dir.mkdir(parents=True)

            spec_path = specs_dir / "area_test.toml"
            spec_path.write_text(
                """
[area]
id = "area_test"
display_name = "Area Test"
source_glob = "input.xlsx"
sheet_name = "Form responses"
date_column = "Periodo Evaluado"
agent_column = "Agente/Titular"
agent_output_column = "Agente/Titular"

[[kpis]]
name = "kpi_total"
source_column = "KPI"
aggregation = "sum"
value_parser = "numeric"
change_direction = "up_is_good"
""".strip(),
                encoding="utf-8",
            )

            df = pd.DataFrame(
                [
                    {"Periodo Evaluado": "2026-03-01", "Agente/Titular": "A", "KPI": 5},
                    {"Periodo Evaluado": "2026-04-01", "Agente/Titular": "A", "KPI": 8},
                ]
            )
            input_path = raw_dir / "input.xlsx"
            df.to_excel(input_path, index=False, sheet_name="Form responses")

            specs = load_all_specs(specs_dir)
            data = read_all_inputs(raw_dir, specs)
            self.assertFalse(data.empty)

            comparison = build_monthly_comparison_v2(data, specs)
            self.assertFalse(comparison.empty)

            partitioned_output = output_dir / "partitioned.xlsx"
            comparison_output = output_dir / "comparison_v2.xlsx"
            write_partitioned_workbook(data=data, output_path=partitioned_output)
            write_comparison_v2_workbook(comparison=comparison, output_path=comparison_output)

            self.assertTrue(partitioned_output.exists())
            self.assertTrue(comparison_output.exists())


if __name__ == "__main__":
    unittest.main()
