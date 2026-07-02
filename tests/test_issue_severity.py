from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIB = PROJECT_ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from vfiic_kpis.issue_severity import (
    IssueSeverity,
    format_warning_summary,
    issue_severity,
    reconciliation_is_blocking,
)
from vfiic_kpis.manifest import FormResolution
from vfiic_kpis.row_validation import (
    ISSUE_AGENTE_FALTANTE,
    ISSUE_FECHA_FALTANTE,
    ISSUE_FILAS_VACIAS,
    ISSUE_PERIODO_FUTURO,
    RowIssue,
)
from vfiic_kpis.user_messages import SKIP_PERSON_COLUMN_MISMATCH
from vfiic_kpis.yaml_loader import FormSpec, KpiSpec


def _resolution(skip_reason: str | None = None) -> FormResolution:
    spec = FormSpec(
        area_id="demo",
        display_name="Demo",
        direccion="Test",
        archivo="demo.xlsx",
        hoja=0,
        columna_fecha_aliases=("Periodo Evaluado",),
        columnas_persona=(),
        agent_output_column="Agente/Titular",
        kpis=(KpiSpec(columna_origen="Visitas", descripcion="Visitas"),),
    )
    return FormResolution(
        spec=spec,
        file_path=Path("demo.xlsx"),
        resolved_sheet=0,
        resolved_date_column="Periodo Evaluado",
        resolved_person_columns=(),
        available_kpis=("Visitas",),
        missing_columns=(),
        skip_reason=skip_reason,
    )


class TestIssueSeverity(unittest.TestCase):
    def test_issue_severity_map(self) -> None:
        self.assertEqual(issue_severity(ISSUE_FECHA_FALTANTE), IssueSeverity.BREAKING)
        self.assertEqual(issue_severity(ISSUE_PERIODO_FUTURO), IssueSeverity.WARNING)
        self.assertEqual(issue_severity(ISSUE_AGENTE_FALTANTE), IssueSeverity.INFO)
        self.assertEqual(issue_severity(ISSUE_FILAS_VACIAS), IssueSeverity.INFO)

    def test_person_column_mismatch_is_not_blocking_reconciliation(self) -> None:
        resolution = _resolution(skip_reason=SKIP_PERSON_COLUMN_MISMATCH)
        self.assertFalse(reconciliation_is_blocking(resolution))

    def test_format_warning_summary(self) -> None:
        issues = [
            RowIssue(
                excel_row="2",
                codigo=ISSUE_PERIODO_FUTURO,
                mensaje="Periodo futuro",
            ),
            RowIssue(
                excel_row="3",
                codigo=ISSUE_PERIODO_FUTURO,
                mensaje="Periodo futuro",
            ),
        ]
        summary = format_warning_summary(issues)
        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertIn("2 filas con periodo futuro", summary)


if __name__ == "__main__":
    unittest.main()
