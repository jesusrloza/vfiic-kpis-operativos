from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from vfiic_kpis.manifest import FormResolution
from vfiic_kpis.row_validation import (
    ISSUE_AGENTE_FALTANTE,
    ISSUE_FECHA_FALTANTE,
    ISSUE_FECHA_INVALIDA,
    ISSUE_FILAS_VACIAS,
    ISSUE_PERIODO_FUTURO,
    ISSUE_SIN_FILAS_VALIDAS,
    ISSUE_SIN_PERIODOS_CALCULABLES,
    RowIssue,
)
from vfiic_kpis.user_messages import (
    SKIP_AMBIGUOUS_INPUT_FILE,
    SKIP_DATE_COLUMN_MISMATCH,
    SKIP_DUPLICATE_INPUT_FILE,
    SKIP_FILE_NOT_FOUND_IN_INPUTS,
    SKIP_HEADER_READ_FAILED,
    SKIP_INCOMPLETE_YAML_CONFIG,
    SKIP_KPI_COLUMN_MISMATCH,
    SKIP_PERSON_COLUMN_MISMATCH,
)

if TYPE_CHECKING:
    from vfiic_kpis.capture_errors import FormCaptureSummary


class IssueSeverity(str, Enum):
    BREAKING = "breaking"
    WARNING = "warning"
    INFO = "info"


ISSUE_SEVERITY: dict[str, IssueSeverity] = {
    ISSUE_FECHA_FALTANTE: IssueSeverity.BREAKING,
    ISSUE_FECHA_INVALIDA: IssueSeverity.BREAKING,
    ISSUE_SIN_FILAS_VALIDAS: IssueSeverity.BREAKING,
    ISSUE_SIN_PERIODOS_CALCULABLES: IssueSeverity.BREAKING,
    ISSUE_PERIODO_FUTURO: IssueSeverity.WARNING,
    ISSUE_AGENTE_FALTANTE: IssueSeverity.INFO,
    ISSUE_FILAS_VACIAS: IssueSeverity.INFO,
}

BLOCKING_SKIP_REASONS: frozenset[str] = frozenset(
    {
        SKIP_INCOMPLETE_YAML_CONFIG,
        SKIP_FILE_NOT_FOUND_IN_INPUTS,
        SKIP_DATE_COLUMN_MISMATCH,
        SKIP_KPI_COLUMN_MISMATCH,
        SKIP_HEADER_READ_FAILED,
        SKIP_AMBIGUOUS_INPUT_FILE,
        SKIP_DUPLICATE_INPUT_FILE,
    }
)

NON_BLOCKING_SKIP_REASONS: frozenset[str] = frozenset({SKIP_PERSON_COLUMN_MISMATCH})


def issue_severity(codigo: str) -> IssueSeverity:
    return ISSUE_SEVERITY.get(codigo, IssueSeverity.WARNING)


def filter_issues_by_severity(
    issues: list[RowIssue],
    *,
    severity: IssueSeverity,
) -> list[RowIssue]:
    return [issue for issue in issues if issue_severity(issue.codigo) == severity]


def reconciliation_is_blocking(resolution: FormResolution) -> bool:
    if resolution.skip_reason is None:
        return False
    if resolution.skip_reason in NON_BLOCKING_SKIP_REASONS:
        return False
    return resolution.skip_reason in BLOCKING_SKIP_REASONS or resolution.skip_reason not in NON_BLOCKING_SKIP_REASONS


def is_form_blocking(summary: FormCaptureSummary) -> bool:
    if summary.valid_rows == 0:
        return True
    if summary.pipeline_reason is not None:
        return True
    return False


def has_warning_issues(issues: list[RowIssue]) -> bool:
    return any(issue_severity(issue.codigo) == IssueSeverity.WARNING for issue in issues)


def format_warning_summary(issues: list[RowIssue]) -> str | None:
    warnings = filter_issues_by_severity(issues, severity=IssueSeverity.WARNING)
    if not warnings:
        return None
    parts: list[str] = []
    by_code: dict[str, int] = {}
    for issue in warnings:
        by_code[issue.codigo] = by_code.get(issue.codigo, 0) + issue.cantidad
    for codigo, count in sorted(by_code.items()):
        if codigo == ISSUE_PERIODO_FUTURO:
            label = "periodo futuro"
        else:
            label = codigo.replace("_", " ")
        noun = "fila" if count == 1 else "filas"
        parts.append(f"{count} {noun} con {label}")
    return "; ".join(parts) + "; ver reporte de errores"
