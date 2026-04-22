from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from vfiic_kpis.excel_export import write_partitioned_workbook
from vfiic_kpis.io import read_all_inputs
from vfiic_kpis.paths import (
    DEFAULT_INPUT_DIR,
    DEFAULT_PARTITIONED_OUTPUT,
    DEFAULT_PARTITIONED_THEME,
    DEFAULT_SPECS_DIR,
)
from vfiic_kpis.spec_loader import load_all_specs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera un Excel con hoja original y hojas por mes (YYYY_mon).",
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--specs-dir", type=Path, default=DEFAULT_SPECS_DIR)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_PARTITIONED_OUTPUT,
    )
    parser.add_argument(
        "--theme",
        type=Path,
        default=DEFAULT_PARTITIONED_THEME,
        help="TOML de tema para maquetación del Excel particionado.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    specs = load_all_specs(args.specs_dir)
    data = read_all_inputs(args.input_dir, specs)
    if data.empty:
        raise SystemExit("No se encontraron datos para generar el reporte particionado.")

    write_partitioned_workbook(data=data, output_path=args.output, theme_path=args.theme)
    print(f"Reporte generado: {args.output}")


if __name__ == "__main__":
    main()

