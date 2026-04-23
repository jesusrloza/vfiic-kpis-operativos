from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

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


def _add_common_input_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--specs-dir", type=Path, default=DEFAULT_SPECS_DIR)


def _load_data(input_dir: Path, specs_dir: Path):
    specs = load_all_specs(specs_dir)
    data = read_all_inputs(input_dir, specs)
    return specs, data


def run_partitioned(args: argparse.Namespace) -> None:
    _, data = _load_data(args.input_dir, args.specs_dir)
    if data.empty:
        raise SystemExit("No se encontraron datos para generar el reporte particionado.")
    write_partitioned_workbook(data=data, output_path=args.output, theme_path=args.theme)
    print(f"Reporte generado: {args.output}")


def run_comparison(args: argparse.Namespace) -> None:
    specs, data = _load_data(args.input_dir, args.specs_dir)
    if data.empty:
        raise SystemExit("No se encontraron datos para generar el comparativo.")
    comparison = build_monthly_comparison(data, specs=specs)
    if comparison.empty:
        raise SystemExit("No fue posible calcular filas de comparativo.")
    write_comparison_workbook(comparison=comparison, output_path=args.output, theme_path=args.theme)
    print(f"Comparativo generado: {args.output}")


def run_comparison_v2(args: argparse.Namespace) -> None:
    specs, data = _load_data(args.input_dir, args.specs_dir)
    if data.empty:
        raise SystemExit("No se encontraron datos para generar el comparativo V2.")
    comparison = build_monthly_comparison_v2(data, specs=specs)
    if comparison.empty:
        raise SystemExit("No fue posible calcular filas de comparativo V2.")
    write_comparison_v2_workbook(comparison=comparison, output_path=args.output, theme_path=args.theme)
    print(f"Comparativo V2 generado: {args.output}")


def run_all(args: argparse.Namespace) -> None:
    specs, data = _load_data(args.input_dir, args.specs_dir)
    if data.empty:
        raise SystemExit("No se encontraron datos para generar reportes.")

    write_partitioned_workbook(
        data=data,
        output_path=args.partitioned_output,
        theme_path=args.partitioned_theme,
    )
    print(f"Reporte particionado generado: {args.partitioned_output}")

    comparison = build_monthly_comparison_v2(data, specs=specs)
    if comparison.empty:
        raise SystemExit("No fue posible calcular filas de comparativo v2.")
    write_comparison_v2_workbook(
        comparison=comparison,
        output_path=args.comparison_output,
        theme_path=args.comparison_theme,
    )
    print(f"Comparativo V2 generado: {args.comparison_output}")


def _parser_partitioned() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Genera un Excel con hoja original y hojas por mes (YYYY_mon).")
    _add_common_input_args(parser)
    parser.add_argument("--output", type=Path, default=DEFAULT_PARTITIONED_OUTPUT)
    parser.add_argument(
        "--theme",
        type=Path,
        default=DEFAULT_PARTITIONED_THEME,
        help="TOML de tema para maquetación del Excel particionado.",
    )
    return parser


def _parser_comparison() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Genera un comparativo mensual (MoM y YoY cuando exista).")
    _add_common_input_args(parser)
    parser.add_argument("--output", type=Path, default=DEFAULT_COMPARISON_OUTPUT)
    parser.add_argument(
        "--theme",
        type=Path,
        default=DEFAULT_COMPARISON_THEME,
        help="TOML de tema para maquetación del comparativo.",
    )
    return parser


def _parser_comparison_v2() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera el comparativo mensual V2 con formato por area y semaforo de variacion."
    )
    _add_common_input_args(parser)
    parser.add_argument("--output", type=Path, default=DEFAULT_COMPARISON_V2_OUTPUT)
    parser.add_argument(
        "--theme",
        type=Path,
        default=DEFAULT_COMPARISON_V2_THEME,
        help="TOML de tema para maquetacion del comparativo V2.",
    )
    return parser


def _parser_all() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera el workbook particionado y el comparativo mensual en una sola corrida."
    )
    _add_common_input_args(parser)
    parser.add_argument("--partitioned-output", type=Path, default=DEFAULT_PARTITIONED_OUTPUT)
    parser.add_argument("--comparison-output", type=Path, default=DEFAULT_COMPARISON_V2_OUTPUT)
    parser.add_argument(
        "--partitioned-theme",
        type=Path,
        default=DEFAULT_PARTITIONED_THEME,
        help="TOML de tema para el workbook particionado.",
    )
    parser.add_argument(
        "--comparison-theme",
        type=Path,
        default=DEFAULT_COMPARISON_V2_THEME,
        help="TOML de tema para el comparativo (v2).",
    )
    return parser


def _run(parser_factory: Callable[[], argparse.ArgumentParser], handler: Callable[[argparse.Namespace], None]) -> None:
    parser = parser_factory()
    args = parser.parse_args()
    handler(args)


def main_partitioned() -> None:
    _run(_parser_partitioned, run_partitioned)


def main_comparison() -> None:
    _run(_parser_comparison, run_comparison)


def main_comparison_v2() -> None:
    _run(_parser_comparison_v2, run_comparison_v2)


def main_run_all() -> None:
    _run(_parser_all, run_all)
