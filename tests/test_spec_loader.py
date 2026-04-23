from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vfiic_kpis.spec_loader import load_area_spec


class TestSpecLoader(unittest.TestCase):
    def test_change_direction_defaults_to_up_is_good(self) -> None:
        body = """
[area]
id = "x"
display_name = "X"
source_glob = "*.xlsx"
sheet_name = "Form responses"
date_column = "Periodo Evaluado"
agent_column = "Agente/Titular"
agent_output_column = "Agente/Titular"

[[kpis]]
name = "k1"
source_column = "Col 1"
aggregation = "sum"
value_parser = "numeric"
"""
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False, encoding="utf-8") as handle:
            handle.write(body)
            path = Path(handle.name)
        try:
            spec = load_area_spec(path)
            self.assertEqual(spec.kpis[0].change_direction, "up_is_good")
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
