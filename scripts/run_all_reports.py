from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from vfiic_kpis.excel_export import (
    write_comparison_v2_workbook,
    write_comparison_workbook,
    write_partitioned_workbook,
)
from vfiic_kpis.io import read_all_inputs
from vfiic_kpis.metrics import build_monthly_comparison, build_monthly_comparison_v2
from vfiic_kpis.paths import (
    DEFAULT_COMPARISON_OUTPUT,
    DEFAULT_COMPARISON_THEME,
    DEFAULT_COMPARISON_V2_OUTPUT,
    DEFAULT_COMPARISON_V2_THEME,
    DEFAULT_INPUT_DIR,
    DEFAULT_PARTITIONED_OUTPUT,
    DEFAULT_PARTITIONED_THEME,
    DEFAULT_SPECS_DIR,
)
from vfiic_kpis.spec_loader import load_all_specs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera el workbook particionado y el comparativo mensual en una sola corrida.",
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--specs-dir", type=Path, default=DEFAULT_SPECS_DIR)
    parser.add_argument(
        "--partitioned-output",
        type=Path,
        default=DEFAULT_PARTITIONED_OUTPUT,
    )
    parser.add_argument(
        "--comparison-output",
        type=Path,
        default=DEFAULT_COMPARISON_OUTPUT,
    )
    parser.add_argument(
        "--partitioned-theme",
        type=Path,
        default=DEFAULT_PARTITIONED_THEME,
        help="TOML de tema para el workbook particionado.",
    )
    parser.add_argument(
        "--comparison-theme",
        type=Path,
        default=DEFAULT_COMPARISON_THEME,
        help="TOML de tema para el comparativo.",
    )
    parser.add_argument(
        "--with-comparison-v2",
        action="store_true",
        help="Si se activa, genera tambien el comparativo V2.",
    )
    parser.add_argument(
        "--comparison-v2-output",
        type=Path,
        default=DEFAULT_COMPARISON_V2_OUTPUT,
    )
    parser.add_argument(
        "--comparison-v2-theme",
        type=Path,
        default=DEFAULT_COMPARISON_V2_THEME,
        help="TOML de tema para el comparativo V2.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    specs = load_all_specs(args.specs_dir)
    data = read_all_inputs(args.input_dir, specs)
    if data.empty:
        raise SystemExit("No se encontraron datos para generar reportes.")

    write_partitioned_workbook(
        data=data,
        output_path=args.partitioned_output,
        theme_path=args.partitioned_theme,
    )
    print(f"Reporte particionado generado: {args.partitioned_output}")

    comparison = build_monthly_comparison(data, specs=specs)
    if comparison.empty:
        raise SystemExit("No fue posible calcular filas de comparativo.")

    write_comparison_workbook(
        comparison=comparison,
        output_path=args.comparison_output,
        theme_path=args.comparison_theme,
    )
    print(f"Comparativo generado: {args.comparison_output}")

    if args.with_comparison_v2:
        comparison_v2 = build_monthly_comparison_v2(data, specs=specs)
        if comparison_v2.empty:
            raise SystemExit("No fue posible calcular filas de comparativo V2.")
        write_comparison_v2_workbook(
            comparison=comparison_v2,
            output_path=args.comparison_v2_output,
            theme_path=args.comparison_v2_theme,
        )
        print(f"Comparativo V2 generado: {args.comparison_v2_output}")


if __name__ == "__main__":
    main()

