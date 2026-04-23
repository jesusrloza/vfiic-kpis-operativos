from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vfiic_kpis.metrics import build_monthly_comparison_v2
from vfiic_kpis.spec_loader import AreaSpec, KpiSpec


class TestMetricsV2(unittest.TestCase):
    def test_trend_respects_change_direction(self) -> None:
        data = pd.DataFrame(
            [
                {"area_id": "a1", "periodo_dt": pd.Timestamp("2026-03-01"), "col_good_up": 10, "col_bad_up": 10},
                {"area_id": "a1", "periodo_dt": pd.Timestamp("2026-04-01"), "col_good_up": 15, "col_bad_up": 15},
            ]
        )
        specs = [
            AreaSpec(
                area_id="a1",
                display_name="Area 1",
                source_glob="*.xlsx",
                sheet_name="Form responses",
                date_column="Periodo Evaluado",
                agent_columns=("Agente/Titular",),
                agent_output_column="Agente/Titular",
                kpis=(
                    KpiSpec(name="kpi_up_good", source_column="col_good_up", change_direction="up_is_good"),
                    KpiSpec(name="kpi_up_bad", source_column="col_bad_up", change_direction="down_is_good"),
                ),
            )
        ]

        result = build_monthly_comparison_v2(data, specs)
        self.assertEqual(len(result), 2)
        trend_by_kpi = {row["indicador"]: row["tendencia"] for _, row in result.iterrows()}
        self.assertEqual(trend_by_kpi["kpi_up_good"], "positive")
        self.assertEqual(trend_by_kpi["kpi_up_bad"], "negative")


if __name__ == "__main__":
    unittest.main()
