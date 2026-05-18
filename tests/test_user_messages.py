from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vfiic_kpis.user_messages import (
    SKIP_FILE_NOT_FOUND_IN_INPUTS,
    SKIP_INCOMPLETE_YAML_CONFIG,
    format_skip_reason,
    format_user_message,
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


if __name__ == "__main__":
    unittest.main()
