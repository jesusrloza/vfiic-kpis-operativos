from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIB = PROJECT_ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from vfiic_kpis.capture_errors import (
    CaptureErrorReport,
    FormCaptureSummary,
    build_form_capture_summary,
    capture_error_report_to_dict,
    format_capture_errors_markdown,
)
from vfiic_kpis.manifest import FormResolution, ReconciliationReport
from vfiic_kpis.row_validation import (
    ISSUE_AGENTE_FALTANTE,
    ISSUE_FILAS_VACIAS,
    RowIssue,
)
from vfiic_kpis.yaml_loader import FormSpec, KpiSpec


def _empty_resolution(display_name: str = "Demo") -> FormResolution:
    spec = FormSpec(
        area_id="demo",
        display_name=display_name,
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
        resolved_person_columns=("Agente - Nombre(s)",),
        available_kpis=("Visitas",),
        missing_columns=(),
        skip_reason=None,
    )


class TestCaptureErrors(unittest.TestCase):
    def test_markdown_includes_actionable_row_issue(self) -> None:
        summary = build_form_capture_summary(
            _empty_resolution("Control de Internamiento"),
            valid_rows=4,
            issues=[
                RowIssue(
                    excel_row="158",
                    codigo=ISSUE_AGENTE_FALTANTE,
                    mensaje="Periodo sin agente — complete nombre y apellidos, o elimine la fila.",
                    columna="Agente/Titular",
                    valor="2026-06-28",
                )
            ],
            omitted_rows=1,
        )
        report = CaptureErrorReport(
            generated_at=datetime(2026, 7, 2, 19, 38, 48),
            input_dir=Path("inputs"),
            schema_path=Path("schemas/indicadores_vfiic_v6.yaml"),
            reconciliation=ReconciliationReport(input_dir=Path("inputs")),
            forms=[summary],
        )
        markdown = format_capture_errors_markdown(report)
        self.assertIn("Control de Internamiento", markdown)
        self.assertIn("Renglón 158", markdown)
        self.assertIn("2026-06-28", markdown)
        self.assertIn("4 fila(s) válida(s) procesada(s)", markdown)
        self.assertNotIn("Reporte crítico", markdown)

    def test_critical_report_excludes_non_blocking_row_issues(self) -> None:
        summary = build_form_capture_summary(
            _empty_resolution("Control de Internamiento"),
            valid_rows=4,
            issues=[
                RowIssue(
                    excel_row="158",
                    codigo=ISSUE_AGENTE_FALTANTE,
                    mensaje="Periodo sin agente — complete nombre y apellidos, o elimine la fila.",
                    columna="Agente/Titular",
                    valor="2026-06-28",
                ),
                RowIssue(
                    excel_row="200-210",
                    codigo=ISSUE_FILAS_VACIAS,
                    mensaje="Filas vacías — elimine el rango formateado sin datos al final de la hoja.",
                    cantidad=11,
                ),
            ],
            omitted_rows=12,
        )
        report = CaptureErrorReport(
            generated_at=datetime(2026, 7, 2, 19, 38, 48),
            input_dir=Path("inputs"),
            schema_path=Path("schemas/indicadores_vfiic_v6.yaml"),
            reconciliation=ReconciliationReport(input_dir=Path("inputs")),
            forms=[summary],
        )
        critical_md = format_capture_errors_markdown(report, critical_only=True)
        self.assertIn("Sin incidencias críticas", critical_md)
        critical_payload = capture_error_report_to_dict(report, critical_only=True)
        self.assertEqual(critical_payload["formularios"], [])

    def test_critical_report_includes_omitted_form(self) -> None:
        summary = build_form_capture_summary(
            _empty_resolution("Sin periodos"),
            valid_rows=0,
            issues=[],
            pipeline_reason="sin periodos parseables",
        )
        report = CaptureErrorReport(
            generated_at=datetime(2026, 7, 2, 19, 38, 48),
            input_dir=Path("inputs"),
            schema_path=Path("schemas/indicadores_vfiic_v6.yaml"),
            reconciliation=ReconciliationReport(input_dir=Path("inputs")),
            forms=[summary],
        )
        critical_md = format_capture_errors_markdown(report, critical_only=True)
        self.assertIn("Sin periodos", critical_md)
        self.assertIn("sin periodos parseables", critical_md)

    def test_clean_report_has_no_issue_sections(self) -> None:
        summary = FormCaptureSummary(
            resolution=_empty_resolution(),
            valid_rows=2,
        )
        report = CaptureErrorReport(
            generated_at=datetime(2026, 7, 2, 19, 38, 48),
            input_dir=Path("inputs"),
            schema_path=Path("schemas/indicadores_vfiic_v6.yaml"),
            reconciliation=ReconciliationReport(input_dir=Path("inputs")),
            forms=[summary],
        )
        self.assertFalse(report.has_issues())


if __name__ == "__main__":
    unittest.main()
