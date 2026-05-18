from __future__ import annotations

from pathlib import Path

DEFAULT_INPUT_DIR = Path("inputs")
DEFAULT_SCHEMA_PATH = Path("schemas/indicadores_vfiic_v5.yaml")

DEFAULT_PARTITIONED_DIR = Path("outputs/particionados")
DEFAULT_COMPARISON_OUTPUT = Path("outputs/comparativos/comparativo_kpis.xlsx")
DEFAULT_RECONCILIATION_LOG = Path("logs/reconciliacion.json")

DEFAULT_COMPARISON_THEME = Path("themes/excel_comparison.toml")
DEFAULT_PARTITIONED_THEME = Path("themes/excel_partitioned.toml")
