from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIB = PROJECT_ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from vfiic_kpis.normalize import parse_iso_date


class TestNormalize(unittest.TestCase):
    def test_parse_excel_serial_date(self) -> None:
        parsed = parse_iso_date(46022)
        self.assertEqual(parsed.date(), datetime(2025, 12, 31).date())

    def test_parse_iso_text(self) -> None:
        parsed = parse_iso_date("2026-04-01")
        self.assertEqual(parsed.date(), datetime(2026, 4, 1).date())


if __name__ == "__main__":
    unittest.main()
