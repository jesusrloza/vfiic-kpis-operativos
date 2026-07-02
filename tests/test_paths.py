from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIB = PROJECT_ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from vfiic_kpis.paths import (
    comparison_output_path,
    discover_input_capture_timestamp,
    errors_report_paths,
)


class TestComparisonOutputPath(unittest.TestCase):
    def test_uses_execution_timestamp_when_no_capture_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            path = comparison_output_path(
                input_dir=input_dir,
                now=datetime(2026, 7, 2, 13, 14, 40),
            )
            self.assertEqual(
                path,
                Path("outputs/comparativos/comparativo_kpis_20260702_131440.xlsx"),
            )

    def test_uses_capture_folder_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            (input_dir / "Captura de Datos-20260702T193848Z-3-001").mkdir()
            path = comparison_output_path(
                input_dir=input_dir,
                now=datetime(2026, 7, 2, 13, 14, 40),
            )
            self.assertEqual(
                path,
                Path("outputs/comparativos/comparativo_kpis_20260702_193848.xlsx"),
            )

    def test_uses_newest_capture_folder_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            (input_dir / "Captura de Datos-20260501T120000Z-1-001").mkdir()
            (input_dir / "Captura de Datos-20260702T193848Z-3-001").mkdir()
            stamp = discover_input_capture_timestamp(input_dir)
            self.assertEqual(stamp, datetime(2026, 7, 2, 19, 38, 48))

    def test_accepts_equivalent_folder_with_timestamp_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            (input_dir / "export-20260702T193848Z-backup").mkdir()
            path = comparison_output_path(input_dir=input_dir)
            self.assertEqual(
                path,
                Path("outputs/comparativos/comparativo_kpis_20260702_193848.xlsx"),
            )


class TestErrorsReportPaths(unittest.TestCase):
    def test_uses_capture_folder_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            (input_dir / "Captura de Datos-20260702T193848Z-3-001").mkdir()
            md_path, json_path, critical_md_path, critical_json_path = errors_report_paths(input_dir=input_dir)
            self.assertEqual(
                md_path,
                Path("outputs/errors/errores_captura_20260702_193848.md"),
            )
            self.assertEqual(
                json_path,
                Path("outputs/errors/errores_captura_20260702_193848.json"),
            )
            self.assertEqual(
                critical_md_path,
                Path("outputs/errors/errores_captura_20260702_193848_criticos.md"),
            )
            self.assertEqual(
                critical_json_path,
                Path("outputs/errors/errores_captura_20260702_193848_criticos.json"),
            )


if __name__ == "__main__":
    unittest.main()
