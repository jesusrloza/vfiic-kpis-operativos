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

from vfiic_kpis.io import read_all_inputs
from vfiic_kpis.spec_loader import AreaSpec, KpiSpec


class TestIOValidation(unittest.TestCase):
    def test_reports_missing_source_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = Path(tmp_dir)
            specs = [
                AreaSpec(
                    area_id="a1",
                    display_name="Area 1",
                    source_glob="missing.xlsx",
                    sheet_name="Form responses",
                    date_column="Periodo Evaluado",
                    agent_columns=("Agente/Titular",),
                    agent_output_column="Agente/Titular",
                    kpis=(KpiSpec(name="kpi_1", source_column="KPI"),),
                )
            ]
            with self.assertRaises(ValueError):
                read_all_inputs(input_dir, specs)

    def test_reports_missing_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = Path(tmp_dir)
            df = pd.DataFrame([{"Periodo Evaluado": "2026-04-01", "Agente/Titular": "A"}])
            df.to_excel(input_dir / "source.xlsx", index=False, sheet_name="Form responses")
            specs = [
                AreaSpec(
                    area_id="a1",
                    display_name="Area 1",
                    source_glob="source.xlsx",
                    sheet_name="Form responses",
                    date_column="Periodo Evaluado",
                    agent_columns=("Agente/Titular",),
                    agent_output_column="Agente/Titular",
                    kpis=(KpiSpec(name="kpi_1", source_column="KPI"),),
                )
            ]
            with self.assertRaises(ValueError):
                read_all_inputs(input_dir, specs)


if __name__ == "__main__":
    unittest.main()
