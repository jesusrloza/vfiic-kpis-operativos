from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pd

from vfiic_kpis.capture_errors import (
    CaptureErrorReport,
    FORM_STATUS_OMITTED,
    FORM_STATUS_PARTIAL,
    FormCaptureSummary,
    build_form_capture_summary,
    write_capture_error_report,
)
from vfiic_kpis.excel_export import (
    write_partitioned_workbook_for_form,
    write_stacked_comparativo_workbook,
)
from vfiic_kpis.issue_severity import format_warning_summary, has_warning_issues
from vfiic_kpis.io import read_form
from vfiic_kpis.log_report import print_and_persist
from vfiic_kpis.manifest import FormResolution, ReconciliationReport, reconcile
from vfiic_kpis.metrics import build_form_comparison
from vfiic_kpis.paths import (
    DEFAULT_COMPARISON_OUTPUT_DIR,
    DEFAULT_COMPARISON_THEME,
    DEFAULT_ERRORS_DIR,
    DEFAULT_INPUT_DIR,
    DEFAULT_PARTITIONED_DIR,
    DEFAULT_PARTITIONED_THEME,
    DEFAULT_RECONCILIATION_LOG,
    DEFAULT_SCHEMA_PATH,
    comparison_output_path,
    errors_report_paths,
)
from vfiic_kpis.row_validation import ISSUE_MESSAGES, ISSUE_SIN_PERIODOS_CALCULABLES, RowIssue
from vfiic_kpis.user_messages import (
    MSG_NO_CALCULABLE_ROWS,
    MSG_NO_PARSEABLE_PERIODS,
    TAG_COMPARATIVO,
    TAG_PARTITIONED,
    format_user_message,
    print_capture_errors_clean,
    print_capture_errors_written,
    print_comparativo_blocks,
    print_comparativo_insufficient_data,
    print_comparativo_workbook,
    print_form_warning,
    print_partitioned_count,
    print_partitioned_none,
    print_partitioned_written,
    print_skipped_form,
    print_user_error,
)
from vfiic_kpis.yaml_loader import load_forms_from_yaml

FormData = tuple[FormResolution, pd.DataFrame]


def _issue_row_count(issues: tuple[RowIssue, ...]) -> int:
    return sum(issue.cantidad for issue in issues)


def _collect_loaded_data(
    matches: tuple[FormResolution, ...],
    log_tag: str,
) -> tuple[list[FormData], list[FormCaptureSummary]]:
    summaries: list[FormCaptureSummary] = []
    for resolution in matches:
        summaries.append(_read_form_with_summary(resolution, log_tag))
    loaded = _loaded_from_summaries(summaries)
    return loaded, summaries


def _read_form_with_summary(resolution: FormResolution, log_tag: str) -> FormCaptureSummary:
    try:
        result = read_form(resolution)
    except Exception as exc:  # noqa: BLE001
        reason = format_user_message(exc, context=log_tag, path=resolution.file_path)
        print_skipped_form(log_tag, resolution.spec.display_name, reason)
        return build_form_capture_summary(
            resolution,
            valid_rows=0,
            issues=[],
            pipeline_reason=reason,
        )

    valid_rows = len(result.df)
    omitted_rows = _issue_row_count(result.issues)
    summary = build_form_capture_summary(
        resolution,
        valid_rows=valid_rows,
        issues=list(result.issues),
        omitted_rows=omitted_rows,
        pipeline_reason=MSG_NO_PARSEABLE_PERIODS if valid_rows == 0 else None,
    )
    summary.dataframe = result.df
    if valid_rows == 0:
        print_skipped_form(log_tag, resolution.spec.display_name, MSG_NO_PARSEABLE_PERIODS)
    elif has_warning_issues(list(result.issues)):
        warning = format_warning_summary(list(result.issues))
        if warning:
            print_form_warning(log_tag, resolution.spec.display_name, warning)
    return summary


def _loaded_from_summaries(summaries: list[FormCaptureSummary]) -> list[FormData]:
    loaded: list[FormData] = []
    for summary in summaries:
        if summary.valid_rows > 0 and summary.dataframe is not None and not summary.dataframe.empty:
            loaded.append((summary.resolution, summary.dataframe))
    return loaded


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--reconciliation-log", type=Path, default=DEFAULT_RECONCILIATION_LOG)
    parser.add_argument(
        "--errors-dir",
        type=Path,
        default=DEFAULT_ERRORS_DIR,
        help="Directorio para reportes de errores de captura (.md + .json).",
    )
    parser.add_argument(
        "--no-error-report",
        action="store_true",
        help="No escribe el reporte en outputs/errors/.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Lista cada archivo generado (particionado); en comparativo muestra recuento de bloques.",
    )


def _load_and_reconcile(schema_path: Path, input_dir: Path) -> ReconciliationReport:
    try:
        forms = load_forms_from_yaml(schema_path)
    except (FileNotFoundError, ValueError) as exc:
        print_user_error("cargar el schema YAML", exc, path=schema_path)
        raise SystemExit(1) from exc
    return reconcile(forms, input_dir)


def _safe_filename(area_id: str) -> str:
    base = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in area_id).strip("_")
    return base or "forma"


def _summary_lookup(summaries: list[FormCaptureSummary]) -> dict[str, FormCaptureSummary]:
    return {item.resolution.spec.area_id: item for item in summaries}


def _mark_pipeline_skip(
    summaries: list[FormCaptureSummary],
    resolution: FormResolution,
    reason: str,
    *,
    issue_code: str | None = None,
) -> None:
    lookup = _summary_lookup(summaries)
    summary = lookup[resolution.spec.area_id]
    summary.pipeline_reason = reason
    summary.status = FORM_STATUS_OMITTED if summary.valid_rows == 0 else FORM_STATUS_PARTIAL
    if issue_code is not None and not any(issue.codigo == issue_code for issue in summary.issues):
        summary.issues.append(
            RowIssue(
                excel_row="-",
                codigo=issue_code,
                mensaje=ISSUE_MESSAGES[issue_code],
            )
        )


def _emit_partitioned(
    loaded: list[FormData],
    summaries: list[FormCaptureSummary],
    output_dir: Path,
    theme_path: Path,
    *,
    log_tag: str = TAG_PARTITIONED,
    verbose: bool = False,
) -> list[Path]:
    written: list[Path] = []
    for resolution, data in loaded:
        if data.empty or data["periodo_dt"].dropna().empty:
            print_skipped_form(log_tag, resolution.spec.display_name, MSG_NO_PARSEABLE_PERIODS)
            _mark_pipeline_skip(summaries, resolution, MSG_NO_PARSEABLE_PERIODS)
            continue
        out_path = output_dir / f"{_safe_filename(resolution.spec.area_id)}.xlsx"
        try:
            write_partitioned_workbook_for_form(
                data=data,
                form_id=resolution.spec.area_id,
                output_path=out_path,
                theme_path=theme_path,
            )
        except Exception as exc:  # noqa: BLE001
            print_user_error(f"generar particionado ({resolution.spec.display_name})", exc, path=out_path)
            raise SystemExit(1) from exc
        written.append(out_path)
        if verbose:
            print_partitioned_written(resolution.spec.display_name, out_path)
    if written:
        print_partitioned_count(len(written), output_dir)
    else:
        print_partitioned_none()
    return written


def _emit_comparativo(
    loaded: list[FormData],
    summaries: list[FormCaptureSummary],
    output_path: Path,
    theme_path: Path,
    *,
    log_tag: str = TAG_COMPARATIVO,
    verbose: bool = False,
) -> Path | None:
    results = []
    for resolution, data in loaded:
        if data.empty or data["periodo_dt"].dropna().empty:
            print_skipped_form(log_tag, resolution.spec.display_name, MSG_NO_PARSEABLE_PERIODS)
            _mark_pipeline_skip(summaries, resolution, MSG_NO_PARSEABLE_PERIODS)
            continue
        result = build_form_comparison(data, resolution)
        if result is None or result.df.empty:
            print_skipped_form(log_tag, resolution.spec.display_name, MSG_NO_CALCULABLE_ROWS)
            _mark_pipeline_skip(
                summaries,
                resolution,
                MSG_NO_CALCULABLE_ROWS,
                issue_code=ISSUE_SIN_PERIODOS_CALCULABLES,
            )
            continue
        results.append(result)

    if not results:
        print_comparativo_insufficient_data()
        return None

    try:
        write_stacked_comparativo_workbook(
            results=results,
            output_path=output_path,
            theme_path=theme_path,
        )
    except Exception as exc:  # noqa: BLE001
        print_user_error("generar el comparativo", exc, path=output_path)
        raise SystemExit(1) from exc
    if verbose:
        print_comparativo_blocks(len(results), output_path)
    else:
        print_comparativo_workbook(output_path)
    return output_path


def _maybe_write_error_report(
    report: ReconciliationReport,
    summaries: list[FormCaptureSummary],
    args: argparse.Namespace,
) -> None:
    if args.no_error_report:
        return

    capture_report = CaptureErrorReport(
        generated_at=datetime.now(),
        input_dir=args.input_dir,
        schema_path=args.schema,
        reconciliation=report,
        forms=summaries,
    )
    if not capture_report.has_issues():
        print_capture_errors_clean()
        return

    markdown_path, json_path, critical_markdown_path, critical_json_path = errors_report_paths(
        input_dir=args.input_dir,
        errors_dir=args.errors_dir,
    )
    write_capture_error_report(
        capture_report,
        markdown_path=markdown_path,
        json_path=json_path,
        critical_markdown_path=critical_markdown_path,
        critical_json_path=critical_json_path,
    )
    print_capture_errors_written(
        len(capture_report.forms_with_issues()),
        markdown_path,
        critical_markdown_path=critical_markdown_path,
    )


def _finalize_run(
    report: ReconciliationReport,
    summaries: list[FormCaptureSummary],
    args: argparse.Namespace,
) -> None:
    print_and_persist(report, args.reconciliation_log)
    _maybe_write_error_report(report, summaries, args)


def run_partitioned(args: argparse.Namespace) -> None:
    report = _load_and_reconcile(args.schema, args.input_dir)
    _, summaries = _collect_loaded_data(report.matched, TAG_PARTITIONED)
    loaded = _loaded_from_summaries(summaries)
    _emit_partitioned(loaded, summaries, args.output_dir, args.theme, verbose=args.verbose)
    _finalize_run(report, summaries, args)


def run_comparativo(args: argparse.Namespace) -> None:
    report = _load_and_reconcile(args.schema, args.input_dir)
    _, summaries = _collect_loaded_data(report.matched, TAG_COMPARATIVO)
    loaded = _loaded_from_summaries(summaries)
    output_path = args.output or comparison_output_path(input_dir=args.input_dir)
    _emit_comparativo(loaded, summaries, output_path, args.theme, verbose=args.verbose)
    _finalize_run(report, summaries, args)


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
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Ruta del Excel comparativo "
            f"(por defecto: {DEFAULT_COMPARISON_OUTPUT_DIR}/comparativo_kpis_<timestamp>.xlsx)."
        ),
    )
    parser.add_argument("--theme", type=Path, default=DEFAULT_COMPARISON_THEME)
    return parser


def _run(parser_factory: Callable[[], argparse.ArgumentParser], handler: Callable[[argparse.Namespace], None]) -> None:
    parser = parser_factory()
    args = parser.parse_args()
    handler(args)


def main_partitioned() -> None:
    _run(_parser_partitioned, run_partitioned)


def main_comparativo() -> None:
    _run(_parser_comparativo, run_comparativo)
