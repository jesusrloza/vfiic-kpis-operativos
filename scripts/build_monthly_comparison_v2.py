from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from vfiic_kpis.excel_export import write_comparison_v2_workbook
from vfiic_kpis.io import read_all_inputs
from vfiic_kpis.metrics import build_monthly_comparison_v2
from vfiic_kpis.paths import (
    DEFAULT_COMPARISON_V2_OUTPUT,
    DEFAULT_COMPARISON_V2_THEME,
    DEFAULT_INPUT_DIR,
    DEFAULT_SPECS_DIR,
)
from vfiic_kpis.spec_loader import load_all_specs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera el comparativo mensual V2 con formato por area y semaforo de variacion.",
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--specs-dir", type=Path, default=DEFAULT_SPECS_DIR)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_COMPARISON_V2_OUTPUT,
    )
    parser.add_argument(
        "--theme",
        type=Path,
        default=DEFAULT_COMPARISON_V2_THEME,
        help="TOML de tema para maquetacion del comparativo V2.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    specs = load_all_specs(args.specs_dir)
    data = read_all_inputs(args.input_dir, specs)
    if data.empty:
        raise SystemExit("No se encontraron datos para generar el comparativo V2.")

    comparison = build_monthly_comparison_v2(data, specs=specs)
    if comparison.empty:
        raise SystemExit("No fue posible calcular filas de comparativo V2.")

    write_comparison_v2_workbook(comparison=comparison, output_path=args.output, theme_path=args.theme)
    print(f"Comparativo V2 generado: {args.output}")


if __name__ == "__main__":
    main()
