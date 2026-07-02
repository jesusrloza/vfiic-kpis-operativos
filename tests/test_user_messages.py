from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIB = PROJECT_ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from vfiic_kpis.manifest import FormResolution, ReconciliationReport
from vfiic_kpis.user_messages import (
    SKIP_DUPLICATE_INPUT_FILE,
    SKIP_FILE_NOT_FOUND_IN_INPUTS,
    SKIP_INCOMPLETE_YAML_CONFIG,
    format_reconciliation_summary,
    format_skip_reason,
    format_user_message,
)
from vfiic_kpis.yaml_loader import FormSpec, KpiSpec


def _resolution(display_name: str = "Demo") -> FormResolution:
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
        resolved_person_columns=(),
        available_kpis=("Visitas",),
        missing_columns=(),
        skip_reason=None,
    )


class TestUserMessages(unittest.TestCase):
    def test_permission_error_on_input(self) -> None:
        path = Path("inputs/demo.xlsx")
        msg = format_user_message(PermissionError("denied"), context="read", path=path)
        self.assertIn("demo.xlsx", msg)
        self.assertIn("Excel", msg)

    def test_permission_error_on_output(self) -> None:
        path = Path("outputs/comparativos/comparativo_kpis.xlsx")
        msg = format_user_message(PermissionError("denied"), context="write", path=path)
        self.assertIn("comparativo_kpis.xlsx", msg)
        self.assertIn("abierto", msg.lower())

    def test_file_not_found(self) -> None:
        path = Path("schemas/missing.yaml")
        msg = format_user_message(FileNotFoundError("no"), context="load", path=path)
        self.assertIn("missing.yaml", msg)

    def test_value_error_yaml_hint(self) -> None:
        msg = format_user_message(ValueError("missing `ingesta` block"), context="validate")
        self.assertIn("guia-indicadores-yaml", msg)

    def test_skip_reason_codes(self) -> None:
        self.assertEqual(
            format_skip_reason(SKIP_INCOMPLETE_YAML_CONFIG),
            "configuración incompleta en el YAML",
        )
        self.assertEqual(
            format_skip_reason(SKIP_FILE_NOT_FOUND_IN_INPUTS),
            "archivo no encontrado en inputs",
        )
        self.assertIn(
            "distintas carpetas",
            format_skip_reason(SKIP_DUPLICATE_INPUT_FILE, detail="demo.xlsx: a/demo.xlsx, b/demo.xlsx"),
        )

    def test_reconciliation_summary_omits_processable_list(self) -> None:
        matched = tuple(_resolution(f"Forma {index}") for index in range(3))
        missing = _resolution("Sin archivo")
        missing_file = FormResolution(
            spec=missing.spec,
            file_path=None,
            resolved_sheet=None,
            resolved_date_column=None,
            resolved_person_columns=(),
            available_kpis=(),
            missing_columns=(),
            skip_reason=SKIP_FILE_NOT_FOUND_IN_INPUTS,
        )
        report = ReconciliationReport(
            matched=matched,
            yaml_without_file=(missing_file,),
            input_dir=Path("inputs"),
        )
        summary = format_reconciliation_summary(report)
        self.assertIn("Formularios procesables: 3", summary)
        self.assertNotIn("Forma 0", summary)
        self.assertIn("Sin archivo", summary)


if __name__ == "__main__":
    unittest.main()
