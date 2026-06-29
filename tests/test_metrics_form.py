from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIB = PROJECT_ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from vfiic_kpis.manifest import FormResolution
from vfiic_kpis.metrics import build_form_comparison
from vfiic_kpis.yaml_loader import FormSpec, KpiSpec


def _spec_with_kpis(*kpi_columns: str) -> FormSpec:
    return FormSpec(
        area_id="demo",
        display_name="Demo",
        direccion="D",
        archivo="demo.xlsx",
        hoja="Form responses",
        columna_fecha_aliases=("Periodo Evaluado",),
        columnas_persona=("Auxiliar",),
        agent_output_column="Agente/Titular",
        kpis=tuple(KpiSpec(columna_origen=col, descripcion=col) for col in kpi_columns),
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


class TestBuildFormComparison(unittest.TestCase):
    def test_mom_and_yoy_when_history_available(self) -> None:
        df = pd.DataFrame(
            [
                {"periodo_dt": pd.Timestamp("2025-04-01"), "metric": 100},
                {"periodo_dt": pd.Timestamp("2026-03-01"), "metric": 200},
                {"periodo_dt": pd.Timestamp("2026-03-01"), "metric": 50},
                {"periodo_dt": pd.Timestamp("2026-04-01"), "metric": 300},
                {"periodo_dt": pd.Timestamp("2026-04-01"), "metric": 100},
            ]
        )
        spec = _spec_with_kpis("metric")
        result = build_form_comparison(df, _resolution(spec))
        self.assertIsNotNone(result)
        assert result is not None
        row = result.df.iloc[0]
        self.assertEqual(row["valor_actual"], 400.0)
        self.assertEqual(row["valor_mes_anterior"], 250.0)
        self.assertEqual(row["valor_anio_anterior"], 100.0)
        self.assertEqual(row["diferencia_mom"], 150.0)
        self.assertEqual(row["diferencia_yoy"], 300.0)
        self.assertEqual(row["tendencia_mom"], "positive")
        self.assertEqual(row["tendencia_yoy"], "positive")
        self.assertEqual(result.mes_actual_label, "Abril 2026")
        self.assertEqual(result.mes_anterior_label, "Marzo 2026")
        self.assertEqual(result.mes_anio_anterior_label, "Abril 2025")

    def test_no_yoy_leaves_columns_null(self) -> None:
        df = pd.DataFrame(
            [
                {"periodo_dt": pd.Timestamp("2026-03-01"), "metric": 5},
                {"periodo_dt": pd.Timestamp("2026-04-01"), "metric": 7},
            ]
        )
        spec = _spec_with_kpis("metric")
        result = build_form_comparison(df, _resolution(spec))
        assert result is not None
        row = result.df.iloc[0]
        self.assertEqual(row["valor_actual"], 7.0)
        self.assertEqual(row["valor_mes_anterior"], 5.0)
        self.assertIsNone(row["valor_anio_anterior"])
        self.assertIsNone(row["diferencia_yoy"])
        self.assertIsNone(row["porcentaje_yoy"])
        self.assertEqual(row["tendencia_yoy"], "na")
        self.assertEqual(result.mes_anterior_label, "Marzo 2026")
        self.assertEqual(result.mes_anio_anterior_label, "Abril 2025")

    def test_single_month_only(self) -> None:
        df = pd.DataFrame([{"periodo_dt": pd.Timestamp("2026-04-01"), "metric": 9}])
        spec = _spec_with_kpis("metric")
        result = build_form_comparison(df, _resolution(spec))
        assert result is not None
        row = result.df.iloc[0]
        self.assertEqual(row["valor_actual"], 9.0)
        self.assertIsNone(row["valor_mes_anterior"])
        self.assertIsNone(row["diferencia_mom"])
        self.assertIsNone(row["porcentaje_mom"])
        self.assertEqual(row["tendencia_mom"], "na")
        self.assertEqual(result.mes_anterior_label, "Marzo 2026")
        self.assertEqual(result.mes_anio_anterior_label, "Abril 2025")

    def test_skips_kpi_when_column_missing_in_df(self) -> None:
        df = pd.DataFrame(
            [
                {"periodo_dt": pd.Timestamp("2026-03-01"), "metric": 1},
                {"periodo_dt": pd.Timestamp("2026-04-01"), "metric": 2},
            ]
        )
        spec = _spec_with_kpis("metric", "no_existe")
        result = build_form_comparison(df, _resolution(spec))
        assert result is not None
        self.assertEqual(len(result.df), 1)
        self.assertEqual(result.df.iloc[0]["indicador"], "metric")


if __name__ == "__main__":
    unittest.main()
