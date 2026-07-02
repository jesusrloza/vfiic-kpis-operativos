from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIB = PROJECT_ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from vfiic_kpis.manifest import FormResolution
from vfiic_kpis.row_validation import (
    ISSUE_AGENTE_FALTANTE,
    ISSUE_FILAS_VACIAS,
    ISSUE_PERIODO_FUTURO,
    validate_and_prepare,
)
from vfiic_kpis.yaml_loader import FormSpec, KpiSpec


def _resolution(*, kpis: tuple[str, ...] = ("Visitas",)) -> FormResolution:
    spec = FormSpec(
        area_id="demo",
        display_name="Demo",
        direccion="Test",
        archivo="demo.xlsx",
        hoja=0,
        columna_fecha_aliases=("Periodo Evaluado",),
        columnas_persona=(
            "Agente - Nombre(s)",
            "Agente - Apellido Paterno",
            "Agente - Apellido Materno",
        ),
        agent_output_column="Agente/Titular",
        kpis=tuple(KpiSpec(columna_origen=name, descripcion=name) for name in kpis),
    )
    return FormResolution(
        spec=spec,
        file_path=Path("demo.xlsx"),
        resolved_sheet=0,
        resolved_date_column="Periodo Evaluado",
        resolved_person_columns=(
            "Agente - Nombre(s)",
            "Agente - Apellido Paterno",
            "Agente - Apellido Materno",
        ),
        available_kpis=kpis,
        missing_columns=(),
        skip_reason=None,
    )


class TestRowValidation(unittest.TestCase):
    def test_groups_consecutive_empty_rows(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Periodo Evaluado": "2026-03-01",
                    "Agente - Nombre(s)": "Ana",
                    "Agente - Apellido Paterno": "Lopez",
                    "Agente - Apellido Materno": "Perez",
                    "Visitas": 1,
                },
                {
                    "Periodo Evaluado": pd.NaT,
                    "Agente - Nombre(s)": pd.NA,
                    "Agente - Apellido Paterno": pd.NA,
                    "Agente - Apellido Materno": pd.NA,
                    "Visitas": pd.NA,
                },
                {
                    "Periodo Evaluado": pd.NaT,
                    "Agente - Nombre(s)": pd.NA,
                    "Agente - Apellido Paterno": pd.NA,
                    "Agente - Apellido Materno": pd.NA,
                    "Visitas": pd.NA,
                },
            ]
        )
        df["Agente/Titular"] = ["Ana Lopez Perez", "", ""]
        out, issues = validate_and_prepare(
            df,
            _resolution(),
            date_column="Periodo Evaluado",
            agent_column="Agente/Titular",
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].codigo, ISSUE_FILAS_VACIAS)
        self.assertEqual(issues[0].excel_row, "3-4")
        self.assertEqual(issues[0].cantidad, 2)

    def test_orphan_date_without_agent(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Periodo Evaluado": "2026-06-28",
                    "Agente - Nombre(s)": "",
                    "Agente - Apellido Paterno": "",
                    "Agente - Apellido Materno": "",
                    "Visitas": 3,
                }
            ]
        )
        df["Agente/Titular"] = ""
        out, issues = validate_and_prepare(
            df,
            _resolution(),
            date_column="Periodo Evaluado",
            agent_column="Agente/Titular",
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(issues[0].codigo, ISSUE_AGENTE_FALTANTE)
        self.assertEqual(issues[0].excel_row, "2")

    def test_keeps_valid_rows_after_blank_gap(self) -> None:
        rows = [
            {
                "Periodo Evaluado": "2026-03-01",
                "Agente - Nombre(s)": "Ana",
                "Agente - Apellido Paterno": "Lopez",
                "Agente - Apellido Materno": "Perez",
                "Visitas": 1,
            },
            {
                "Periodo Evaluado": pd.NaT,
                "Agente - Nombre(s)": pd.NA,
                "Agente - Apellido Paterno": pd.NA,
                "Agente - Apellido Materno": pd.NA,
                "Visitas": pd.NA,
            },
            {
                "Periodo Evaluado": "2026-04-01",
                "Agente - Nombre(s)": "Ana",
                "Agente - Apellido Paterno": "Lopez",
                "Agente - Apellido Materno": "Perez",
                "Visitas": 2,
            },
        ]
        df = pd.DataFrame(rows)
        df["Agente/Titular"] = ["Ana Lopez Perez", "", "Ana Lopez Perez"]
        out, issues = validate_and_prepare(
            df,
            _resolution(),
            date_column="Periodo Evaluado",
            agent_column="Agente/Titular",
        )
        self.assertEqual(len(out), 2)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].excel_row, "3")

    def test_future_period_is_reported(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Periodo Evaluado": "2099-01-01",
                    "Agente - Nombre(s)": "Ana",
                    "Agente - Apellido Paterno": "Lopez",
                    "Agente - Apellido Materno": "Perez",
                    "Visitas": 1,
                }
            ]
        )
        df["Agente/Titular"] = "Ana Lopez Perez"
        out, issues = validate_and_prepare(
            df,
            _resolution(),
            date_column="Periodo Evaluado",
            agent_column="Agente/Titular",
            as_of=date(2026, 6, 1),
        )
        self.assertTrue(out.empty)
        self.assertEqual(issues[0].codigo, ISSUE_PERIODO_FUTURO)


if __name__ == "__main__":
    unittest.main()
