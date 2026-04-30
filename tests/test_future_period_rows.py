from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vfiic_kpis.manifest import FormResolution
from vfiic_kpis.metrics import build_form_comparison
from vfiic_kpis.normalize import drop_future_period_rows
from vfiic_kpis.yaml_loader import FormSpec, KpiSpec


def _spec_metric() -> FormSpec:
    return FormSpec(
        area_id="demo",
        display_name="Demo",
        direccion="D",
        archivo="demo.xlsx",
        hoja="Form responses",
        columna_fecha_aliases=("Periodo Evaluado",),
        columnas_persona=("Auxiliar",),
        agent_output_column="Agente/Titular",
        kpis=(KpiSpec(columna_origen="metric", descripcion="metric"),),
    )


def _resolution(spec: FormSpec) -> FormResolution:
    return FormResolution(
        spec=spec,
        file_path=Path("demo.xlsx"),
        resolved_sheet="Form responses",
        resolved_date_column="Periodo Evaluado",
        resolved_person_columns=("Auxiliar",),
        available_kpis=tuple(kpi.columna_origen for kpi in spec.kpis),
        missing_columns=(),
        skip_reason=None,
    )


class TestDropFuturePeriodRows(unittest.TestCase):
    def test_drops_rows_after_as_of(self) -> None:
        df = pd.DataFrame(
            [
                {"periodo_dt": pd.Timestamp("2026-03-01"), "metric": 1},
                {"periodo_dt": pd.Timestamp("2027-03-01"), "metric": 999},
            ]
        )
        out, n = drop_future_period_rows(df, as_of=date(2026, 6, 1))
        self.assertEqual(n, 1)
        self.assertEqual(len(out), 1)
        self.assertEqual(out.iloc[0]["metric"], 1)

    def test_keeps_same_day_as_as_of(self) -> None:
        df = pd.DataFrame([{"periodo_dt": pd.Timestamp("2026-06-01"), "x": 1}])
        out, n = drop_future_period_rows(df, as_of=date(2026, 6, 1))
        self.assertEqual(n, 0)
        self.assertEqual(len(out), 1)

    def test_comparativo_uses_max_after_drop(self) -> None:
        df = pd.DataFrame(
            [
                {"periodo_dt": pd.Timestamp("2026-04-01"), "metric": 10},
                {"periodo_dt": pd.Timestamp("2027-03-01"), "metric": 99},
            ]
        )
        filtered, n = drop_future_period_rows(df, as_of=date(2026, 12, 31))
        self.assertEqual(n, 1)
        spec = _spec_metric()
        result = build_form_comparison(filtered, _resolution(spec))
        assert result is not None
        self.assertEqual(result.mes_actual_label, "Abril 2026")


if __name__ == "__main__":
    unittest.main()
