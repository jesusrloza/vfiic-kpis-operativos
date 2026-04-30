from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

import pandas as pd

from vfiic_kpis.excel_export import (
    write_partitioned_workbook_for_form,
    write_stacked_comparativo_workbook,
)
from vfiic_kpis.io import read_form
from vfiic_kpis.log_report import print_and_persist
from vfiic_kpis.normalize import drop_future_period_rows
from vfiic_kpis.manifest import FormResolution, ReconciliationReport, reconcile
from vfiic_kpis.metrics import build_form_comparison
from vfiic_kpis.paths import (
    DEFAULT_COMPARISON_OUTPUT,
    DEFAULT_COMPARISON_V2_THEME,
    DEFAULT_INPUT_DIR,
    DEFAULT_PARTITIONED_DIR,
    DEFAULT_PARTITIONED_THEME,
    DEFAULT_RECONCILIATION_LOG,
    DEFAULT_SCHEMA_PATH,
)
from vfiic_kpis.yaml_loader import load_forms_from_yaml

FormData = tuple[FormResolution, pd.DataFrame]


def _collect_loaded_data(
    matches: tuple[FormResolution, ...],
    log_prefix: str,
) -> list[FormData]:
    """Lee cada formulario una vez; avisos `[datos]` y errores usan `log_prefix`."""
    loaded: list[FormData] = []
    for resolution in matches:
        data = _read_form_or_none(resolution, log_prefix)
        if data is not None:
            loaded.append((resolution, data))
    return loaded


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--reconciliation-log", type=Path, default=DEFAULT_RECONCILIATION_LOG)
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Lista cada archivo generado (particionado); en comparativo muestra recuento de bloques.",
    )


def _load_and_reconcile(schema_path: Path, input_dir: Path) -> ReconciliationReport:
    forms = load_forms_from_yaml(schema_path)
    return reconcile(forms, input_dir)


def _safe_filename(area_id: str) -> str:
    base = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in area_id).strip("_")
    return base or "forma"


def _read_form_or_none(resolution: FormResolution, log_prefix: str) -> pd.DataFrame | None:
    try:
        data = read_form(resolution)
    except Exception as exc:  # noqa: BLE001
        print(f"[{log_prefix}] omitido {resolution.spec.display_name!r}: {exc}")
        return None
    data, n_future = drop_future_period_rows(data)
    if n_future:
        archivo = resolution.spec.archivo or "(sin nombre)"
        print(
            f"[datos] omitidas {n_future} fila(s) con periodo futuro: "
            f"{resolution.spec.display_name} (archivo: {archivo})"
        )
    return data


def _emit_partitioned(
    loaded: list[FormData],
    output_dir: Path,
    theme_path: Path,
    *,
    verbose: bool = False,
) -> list[Path]:
    written: list[Path] = []
    for resolution, data in loaded:
        if data.empty or data["periodo_dt"].dropna().empty:
            print(f"[partitioned] omitido {resolution.spec.display_name!r}: sin periodos parseables")
            continue
        out_path = output_dir / f"{_safe_filename(resolution.spec.area_id)}.xlsx"
        write_partitioned_workbook_for_form(
            data=data,
            form_id=resolution.spec.area_id,
            output_path=out_path,
            theme_path=theme_path,
        )
        written.append(out_path)
        if verbose:
            print(f"[partitioned] {resolution.spec.display_name} -> {out_path}")
    if written:
        print(f"[partitioned] {len(written)} workbook(s) en {output_dir}")
    else:
        print("[partitioned] ningún workbook generado")
    return written


def _process_partitioned(
    matches: tuple[FormResolution, ...],
    output_dir: Path,
    theme_path: Path,
    *,
    verbose: bool = False,
) -> list[Path]:
    loaded = _collect_loaded_data(matches, "partitioned")
    return _emit_partitioned(loaded, output_dir, theme_path, verbose=verbose)


def _emit_comparativo(
    loaded: list[FormData],
    output_path: Path,
    theme_path: Path,
    *,
    verbose: bool = False,
) -> Path | None:
    results = []
    for resolution, data in loaded:
        if data.empty or data["periodo_dt"].dropna().empty:
            print(f"[comparativo] omitido {resolution.spec.display_name!r}: sin periodos parseables")
            continue
        result = build_form_comparison(data, resolution)
        if result is None or result.df.empty:
            print(f"[comparativo] omitido {resolution.spec.display_name!r}: sin filas calculables")
            continue
        results.append(result)

    if not results:
        print("[comparativo] no hay formularios con datos suficientes; no se generó workbook")
        return None

    write_stacked_comparativo_workbook(
        results=results,
        output_path=output_path,
        theme_path=theme_path,
    )
    if verbose:
        print(f"[comparativo] {len(results)} bloque(s) -> {output_path}")
    else:
        print(f"[comparativo] workbook: {output_path}")
    return output_path


def _process_comparativo(
    matches: tuple[FormResolution, ...],
    output_path: Path,
    theme_path: Path,
    *,
    verbose: bool = False,
) -> Path | None:
    loaded = _collect_loaded_data(matches, "comparativo")
    return _emit_comparativo(loaded, output_path, theme_path, verbose=verbose)


def run_partitioned(args: argparse.Namespace) -> None:
    report = _load_and_reconcile(args.schema, args.input_dir)
    _process_partitioned(report.matched, args.output_dir, args.theme, verbose=args.verbose)
    print_and_persist(report, args.reconciliation_log)


def run_comparativo(args: argparse.Namespace) -> None:
    report = _load_and_reconcile(args.schema, args.input_dir)
    _process_comparativo(report.matched, args.output, args.theme, verbose=args.verbose)
    print_and_persist(report, args.reconciliation_log)


def run_all(args: argparse.Namespace) -> None:
    report = _load_and_reconcile(args.schema, args.input_dir)
    loaded = _collect_loaded_data(report.matched, "run_all")
    _emit_partitioned(loaded, args.partitioned_dir, args.partitioned_theme, verbose=args.verbose)
    _emit_comparativo(loaded, args.comparison_output, args.comparison_theme, verbose=args.verbose)
    print_and_persist(report, args.reconciliation_log)


def _parser_partitioned() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera un Excel particionado por mes para cada formulario en el YAML."
    )
    _add_common_args(parser)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_PARTITIONED_DIR)
    parser.add_argument("--theme", type=Path, default=DEFAULT_PARTITIONED_THEME)
    return parser


def _parser_comparativo() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera el comparativo apilado (un sheet, todos los formularios)."
    )
    _add_common_args(parser)
    parser.add_argument("--output", type=Path, default=DEFAULT_COMPARISON_OUTPUT)
    parser.add_argument("--theme", type=Path, default=DEFAULT_COMPARISON_V2_THEME)
    return parser


def _parser_all() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera particionados por formulario y el comparativo apilado en una corrida."
    )
    _add_common_args(parser)
    parser.add_argument("--partitioned-dir", type=Path, default=DEFAULT_PARTITIONED_DIR)
    parser.add_argument("--partitioned-theme", type=Path, default=DEFAULT_PARTITIONED_THEME)
    parser.add_argument("--comparison-output", type=Path, default=DEFAULT_COMPARISON_OUTPUT)
    parser.add_argument("--comparison-theme", type=Path, default=DEFAULT_COMPARISON_V2_THEME)
    return parser


def _run(parser_factory: Callable[[], argparse.ArgumentParser], handler: Callable[[argparse.Namespace], None]) -> None:
    parser = parser_factory()
    args = parser.parse_args()
    handler(args)


def main_partitioned() -> None:
    _run(_parser_partitioned, run_partitioned)


def main_comparativo() -> None:
    _run(_parser_comparativo, run_comparativo)


def main_run_all() -> None:
    _run(_parser_all, run_all)
