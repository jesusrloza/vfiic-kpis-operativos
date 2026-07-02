from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from vfiic_kpis.issue_severity import (
    IssueSeverity,
    filter_issues_by_severity,
    is_form_blocking,
    reconciliation_is_blocking,
)
from vfiic_kpis.manifest import FormResolution, ReconciliationReport
from vfiic_kpis.row_validation import (
    ISSUE_MESSAGES,
    ISSUE_SIN_FILAS_VALIDAS,
    ISSUE_SIN_PERIODOS_CALCULABLES,
    RowIssue,
)
from vfiic_kpis.user_messages import format_skip_reason, resolution_to_user_dict

FORM_STATUS_OK = "ok"
FORM_STATUS_PARTIAL = "procesado_parcial"
FORM_STATUS_OMITTED = "omitido"


@dataclass
class FormCaptureSummary:
    resolution: FormResolution
    status: str = FORM_STATUS_OK
    valid_rows: int = 0
    omitted_rows: int = 0
    issues: list[RowIssue] = field(default_factory=list)
    pipeline_reason: str | None = None
    dataframe: pd.DataFrame | None = field(default=None, repr=False)

    def has_issues(self) -> bool:
        return bool(self.issues) or self.status != FORM_STATUS_OK or self.pipeline_reason is not None

    def is_blocking(self) -> bool:
        return is_form_blocking(self)

    def has_critical_issues(self) -> bool:
        return self.is_blocking() or bool(
            filter_issues_by_severity(self.issues, severity=IssueSeverity.BREAKING)
        )


@dataclass
class CaptureErrorReport:
    generated_at: datetime
    input_dir: Path
    schema_path: Path
    reconciliation: ReconciliationReport
    forms: list[FormCaptureSummary] = field(default_factory=list)

    def forms_with_issues(self) -> list[FormCaptureSummary]:
        return [item for item in self.forms if item.has_issues()]

    def forms_with_critical_issues(self) -> list[FormCaptureSummary]:
        return [item for item in self.forms if item.has_critical_issues()]

    def reconciliation_has_issues(self) -> bool:
        report = self.reconciliation
        return bool(
            report.yaml_without_file
            or report.yaml_without_ingesta
            or report.yaml_with_column_issues
            or report.files_without_yaml
            or report.duplicate_input_files
        )

    def reconciliation_has_critical_issues(self) -> bool:
        report = self.reconciliation
        blocking_column_issues = [
            item for item in report.yaml_with_column_issues if reconciliation_is_blocking(item)
        ]
        return bool(
            report.yaml_without_file
            or report.yaml_without_ingesta
            or blocking_column_issues
            or report.duplicate_input_files
        )

    def has_issues(self) -> bool:
        return self.reconciliation_has_issues() or bool(self.forms_with_issues())

    def has_critical_issues(self) -> bool:
        return self.reconciliation_has_critical_issues() or bool(self.forms_with_critical_issues())


def _form_heading(summary: FormCaptureSummary) -> str:
    archivo = summary.resolution.spec.archivo or "(sin nombre)"
    return f"**{summary.resolution.spec.display_name}** (`{archivo}`)"


def _issue_bullet(issue: RowIssue) -> str:
    label = f"Renglón {issue.excel_row}" if issue.cantidad == 1 else f"Renglones {issue.excel_row}"
    detail = issue.mensaje
    if issue.valor:
        detail = f"{detail} Valor: `{issue.valor}`."
    if issue.columna:
        detail = f"{detail} Columna: `{issue.columna}`."
    if issue.cantidad > 1:
        detail = f"{detail} ({issue.cantidad} filas)."
    return f"- {label}: {detail}"


def _issues_for_report(summary: FormCaptureSummary, *, critical_only: bool) -> list[RowIssue]:
    if not critical_only:
        return list(summary.issues)
    if summary.is_blocking():
        breaking = filter_issues_by_severity(summary.issues, severity=IssueSeverity.BREAKING)
        return breaking if breaking else list(summary.issues)
    return filter_issues_by_severity(summary.issues, severity=IssueSeverity.BREAKING)


def _form_summaries_for_report(
    report: CaptureErrorReport,
    *,
    critical_only: bool,
) -> list[FormCaptureSummary]:
    if critical_only:
        return report.forms_with_critical_issues()
    return report.forms_with_issues()


def format_capture_errors_markdown(
    report: CaptureErrorReport,
    *,
    critical_only: bool = False,
) -> str:
    title = (
        "# Reporte crítico de errores de captura"
        if critical_only
        else "# Reporte de errores de captura"
    )
    lines = [
        title,
        "",
        f"Generado: {report.generated_at.isoformat(timespec='seconds')}",
        f"Inputs: `{report.input_dir.as_posix()}`",
        f"Schema: `{report.schema_path.as_posix()}`",
        "",
    ]

    recon = report.reconciliation
    recon_has_issues = (
        report.reconciliation_has_critical_issues()
        if critical_only
        else report.reconciliation_has_issues()
    )
    if recon_has_issues:
        lines.extend(["## Reconciliación YAML vs inputs", ""])
        column_issues = (
            [item for item in recon.yaml_with_column_issues if reconciliation_is_blocking(item)]
            if critical_only
            else list(recon.yaml_with_column_issues)
        )
        sections = [
            ("Formularios sin archivo en inputs", recon.yaml_without_file),
            ("Configuración incompleta en el YAML", recon.yaml_without_ingesta),
            ("Problemas de columnas o archivos ambiguos", column_issues),
        ]
        for title_text, items in sections:
            if not items:
                continue
            lines.append(f"### {title_text}")
            lines.append("")
            for item in items:
                reason = format_skip_reason(item.skip_reason, detail=item.skip_detail)
                lines.append(f"- **{item.spec.display_name}**: {reason or 'incidencia de reconciliación'}")
            lines.append("")

        if recon.duplicate_input_files:
            lines.append("### Archivos con nombre duplicado en inputs")
            lines.append("")
            for basename, paths in recon.duplicate_input_files:
                rel_paths = ", ".join(
                    path.relative_to(recon.input_dir).as_posix()
                    if recon.input_dir is not None
                    else path.name
                    for path in paths
                )
                lines.append(f"- `{basename}`: {rel_paths}")
            lines.append("")

        if not critical_only and recon.files_without_yaml:
            lines.append("### Archivos en inputs sin entrada en el YAML")
            lines.append("")
            for path in recon.files_without_yaml:
                rel = (
                    path.relative_to(recon.input_dir).as_posix()
                    if recon.input_dir is not None
                    else path.name
                )
                lines.append(f"- `{rel}`")
            lines.append("")

    form_summaries = _form_summaries_for_report(report, critical_only=critical_only)
    if form_summaries:
        lines.extend(["## Incidencias por formulario", ""])
        for summary in form_summaries:
            lines.append(_form_heading(summary))
            lines.append("")
            for issue in _issues_for_report(summary, critical_only=critical_only):
                lines.append(_issue_bullet(issue))
            if summary.valid_rows and not critical_only:
                lines.append(f"- {summary.valid_rows} fila(s) válida(s) procesada(s).")
            if summary.pipeline_reason:
                lines.append(f"- Estado final: **{summary.status}** — {summary.pipeline_reason}.")
            elif summary.status == FORM_STATUS_OMITTED:
                lines.append("- Estado final: **omitido**.")
            lines.append("")

    has_content = recon_has_issues or form_summaries
    if not has_content:
        if critical_only:
            lines.append("Sin incidencias críticas de captura en esta corrida.")
        else:
            lines.append("Sin incidencias de captura en esta corrida.")
    return "\n".join(lines).rstrip() + "\n"


def capture_error_report_to_dict(
    report: CaptureErrorReport,
    *,
    critical_only: bool = False,
) -> dict:
    recon = report.reconciliation
    input_dir = recon.input_dir
    column_issues = (
        [item for item in recon.yaml_with_column_issues if reconciliation_is_blocking(item)]
        if critical_only
        else list(recon.yaml_with_column_issues)
    )
    form_summaries = _form_summaries_for_report(report, critical_only=critical_only)
    payload: dict = {
        "generado_en": report.generated_at.isoformat(timespec="seconds"),
        "input_dir": str(report.input_dir),
        "schema": str(report.schema_path),
        "critico": critical_only,
        "reconciliacion": {
            "sin_archivo": [resolution_to_user_dict(item) for item in recon.yaml_without_file],
            "config_incompleta": [resolution_to_user_dict(item) for item in recon.yaml_without_ingesta],
            "problemas_columnas": [resolution_to_user_dict(item) for item in column_issues],
            "archivos_duplicados": [
                {
                    "nombre": basename,
                    "rutas": [
                        path.relative_to(input_dir).as_posix() if input_dir is not None else path.name
                        for path in paths
                    ],
                }
                for basename, paths in recon.duplicate_input_files
            ],
        },
        "formularios": [
            {
                "display_name": summary.resolution.spec.display_name,
                "area_id": summary.resolution.spec.area_id,
                "archivo": summary.resolution.spec.archivo,
                "archivo_resuelto": (
                    str(summary.resolution.file_path) if summary.resolution.file_path else None
                ),
                "estado": summary.status,
                "filas_validas": summary.valid_rows,
                "filas_omitidas": summary.omitted_rows,
                "motivo_pipeline": summary.pipeline_reason,
                "incidencias": [
                    issue.to_dict() for issue in _issues_for_report(summary, critical_only=critical_only)
                ],
            }
            for summary in form_summaries
        ],
        "totales": {
            "formularios_con_incidencias": len(form_summaries),
            "reconciliacion_con_incidencias": bool(
                recon.yaml_without_file
                or recon.yaml_without_ingesta
                or column_issues
                or recon.duplicate_input_files
            ),
        },
    }
    if not critical_only:
        payload["reconciliacion"]["archivos_sin_schema"] = [
            path.relative_to(input_dir).as_posix() if input_dir is not None else path.name
            for path in recon.files_without_yaml
        ]
    return payload


def write_capture_error_report(
    report: CaptureErrorReport,
    *,
    markdown_path: Path,
    json_path: Path,
    critical_markdown_path: Path | None = None,
    critical_json_path: Path | None = None,
) -> None:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(format_capture_errors_markdown(report), encoding="utf-8")
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(capture_error_report_to_dict(report), handle, ensure_ascii=False, indent=2)

    if critical_markdown_path is None or critical_json_path is None:
        return

    critical_markdown_path.write_text(
        format_capture_errors_markdown(report, critical_only=True),
        encoding="utf-8",
    )
    with critical_json_path.open("w", encoding="utf-8") as handle:
        json.dump(
            capture_error_report_to_dict(report, critical_only=True),
            handle,
            ensure_ascii=False,
            indent=2,
        )


def build_form_capture_summary(
    resolution: FormResolution,
    *,
    valid_rows: int,
    issues: list[RowIssue],
    pipeline_reason: str | None = None,
    omitted_rows: int = 0,
) -> FormCaptureSummary:
    all_issues = list(issues)
    if valid_rows == 0 and not any(issue.codigo == ISSUE_SIN_FILAS_VALIDAS for issue in all_issues):
        all_issues.append(
            RowIssue(
                excel_row="-",
                codigo=ISSUE_SIN_FILAS_VALIDAS,
                mensaje=ISSUE_MESSAGES[ISSUE_SIN_FILAS_VALIDAS],
            )
        )

    if valid_rows == 0:
        status = FORM_STATUS_OMITTED
    elif all_issues or pipeline_reason:
        status = FORM_STATUS_PARTIAL
    else:
        status = FORM_STATUS_OK

    return FormCaptureSummary(
        resolution=resolution,
        status=status,
        valid_rows=valid_rows,
        omitted_rows=omitted_rows,
        issues=all_issues,
        pipeline_reason=pipeline_reason,
        dataframe=None,
    )
