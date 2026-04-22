from __future__ import annotations

import argparse
from pathlib import Path

from vfiic_kpis.excel_export import write_comparison_workbook
from vfiic_kpis.io import read_all_inputs
from vfiic_kpis.metrics import build_monthly_comparison
from vfiic_kpis.spec_loader import load_all_specs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera un comparativo mensual (MoM y YoY cuando exista).",
    )
    parser.add_argument("--input-dir", type=Path, default=Path("inputs/raw"))
    parser.add_argument("--specs-dir", type=Path, default=Path("inputs/specs"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/comparativos/comparativo_kpis.xlsx"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    specs = load_all_specs(args.specs_dir)
    data = read_all_inputs(args.input_dir, specs)
    if data.empty:
        raise SystemExit("No se encontraron datos para generar el comparativo.")

    comparison = build_monthly_comparison(data, specs=specs)
    if comparison.empty:
        raise SystemExit("No fue posible calcular filas de comparativo.")

    write_comparison_workbook(comparison=comparison, output_path=args.output)
    print(f"Comparativo generado: {args.output}")


if __name__ == "__main__":
    main()

