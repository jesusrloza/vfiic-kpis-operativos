from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from vfiic_kpis.manifest import FormResolution
from vfiic_kpis.normalize import (
    is_missing_date,
    month_key,
    month_label,
    normalize_sort_text,
    parse_iso_date,
)
from vfiic_kpis.text_match import find_matching_column

ISSUE_FILAS_VACIAS = "filas_vacias"
ISSUE_FECHA_FALTANTE = "fecha_faltante"
ISSUE_FECHA_INVALIDA = "fecha_invalida"
ISSUE_AGENTE_FALTANTE = "agente_faltante"
ISSUE_PERIODO_FUTURO = "periodo_futuro"
ISSUE_SIN_FILAS_VALIDAS = "sin_filas_validas"
ISSUE_SIN_PERIODOS_CALCULABLES = "sin_periodos_calculables"

ISSUE_MESSAGES: dict[str, str] = {
    ISSUE_FILAS_VACIAS: "Filas vacías — elimine el rango formateado sin datos al final de la hoja.",
    ISSUE_FECHA_FALTANTE: "Falta el periodo evaluado — complete la columna de fecha o elimine la fila.",
    ISSUE_FECHA_INVALIDA: "Periodo evaluado no reconocido — use un formato de fecha válido.",
    ISSUE_AGENTE_FALTANTE: "Periodo sin agente — complete nombre y apellidos, o elimine la fila.",
    ISSUE_PERIODO_FUTURO: "Periodo futuro — la fila no se incluye hasta que corresponda el mes evaluado.",
    ISSUE_SIN_FILAS_VALIDAS: "Ninguna fila válida — revise periodo, agente y datos de captura.",
    ISSUE_SIN_PERIODOS_CALCULABLES: "No hay periodos suficientes para calcular el comparativo.",
}


@dataclass(frozen=True)
class RowIssue:
    """One validation finding tied to an Excel row or row range."""

    excel_row: str
    codigo: str
    mensaje: str
    columna: str | None = None
    valor: str | None = None
    cantidad: int = 1

    def to_dict(self) -> dict:
        payload: dict = {
            "renglon": self.excel_row,
            "codigo": self.codigo,
            "mensaje": self.mensaje,
        }
        if self.columna is not None:
            payload["columna"] = self.columna
        if self.valor is not None:
            payload["valor"] = self.valor
        if self.cantidad > 1:
            payload["cantidad"] = self.cantidad
        return payload


def _excel_row_label(start: int, end: int | None = None) -> str:
    if end is None or end == start:
        return str(start)
    return f"{start}-{end}"


def _format_value(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, (pd.Timestamp, datetime)):
        if pd.isna(value):
            return ""
        return value.strftime("%Y-%m-%d")
    return str(value).strip()


def _is_blank(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip() == ""


def _resolved_kpi_columns(resolution: FormResolution, available_columns: list[str]) -> list[str]:
    columns: list[str] = []
    for kpi in resolution.spec.kpis:
        match = find_matching_column(kpi.columna_origen, available_columns)
        if match is not None:
            columns.append(match)
    return columns


def _row_has_kpi_data(row: pd.Series, kpi_columns: list[str]) -> bool:
    return any(not _is_blank(row[col]) for col in kpi_columns)


def _row_is_completely_empty(
    row: pd.Series,
    *,
    date_column: str,
    agent_column: str,
    kpi_columns: list[str],
) -> bool:
    if not _is_blank(row[date_column]):
        return False
    if not _is_blank(row[agent_column]):
        return False
    return not _row_has_kpi_data(row, kpi_columns)


def _is_future_period(dt: datetime, *, as_of: date) -> bool:
    ref_ym = as_of.year * 12 + as_of.month
    period_ym = dt.year * 12 + dt.month
    return period_ym > ref_ym


def _flush_empty_run(
    issues: list[RowIssue],
    *,
    start_row: int | None,
    end_row: int | None,
) -> None:
    if start_row is None:
        return
    end = end_row if end_row is not None else start_row
    count = end - start_row + 1
    issues.append(
        RowIssue(
            excel_row=_excel_row_label(start_row, end if count > 1 else None),
            codigo=ISSUE_FILAS_VACIAS,
            mensaje=ISSUE_MESSAGES[ISSUE_FILAS_VACIAS],
            cantidad=count,
        )
    )


def validate_and_prepare(
    df: pd.DataFrame,
    resolution: FormResolution,
    *,
    date_column: str,
    agent_column: str,
    as_of: date | None = None,
) -> tuple[pd.DataFrame, list[RowIssue]]:
    """Validate each row, drop invalid ones, and add normalized period/agent columns."""
    if df.empty:
        return df.copy(), []

    ref = as_of or date.today()
    available_columns = list(df.columns)
    kpi_columns = _resolved_kpi_columns(resolution, available_columns)

    valid_indices: list[int] = []
    issues: list[RowIssue] = []
    empty_start: int | None = None
    empty_end: int | None = None

    for idx, row in df.iterrows():
        assert isinstance(idx, int)
        excel_row = idx + 2

        if _row_is_completely_empty(
            row,
            date_column=date_column,
            agent_column=agent_column,
            kpi_columns=kpi_columns,
        ):
            if empty_start is None:
                empty_start = excel_row
            empty_end = excel_row
            continue

        if empty_start is not None:
            _flush_empty_run(issues, start_row=empty_start, end_row=empty_end)
            empty_start = None
            empty_end = None

        date_value = row[date_column]
        agent_value = row[agent_column]
        has_other_data = not _is_blank(agent_value) or _row_has_kpi_data(row, kpi_columns)

        if is_missing_date(date_value):
            if has_other_data:
                issues.append(
                    RowIssue(
                        excel_row=str(excel_row),
                        codigo=ISSUE_FECHA_FALTANTE,
                        mensaje=ISSUE_MESSAGES[ISSUE_FECHA_FALTANTE],
                        columna=date_column,
                        valor=_format_value(date_value) or None,
                    )
                )
            continue

        try:
            period_dt = parse_iso_date(date_value)
        except ValueError:
            issues.append(
                RowIssue(
                    excel_row=str(excel_row),
                    codigo=ISSUE_FECHA_INVALIDA,
                    mensaje=ISSUE_MESSAGES[ISSUE_FECHA_INVALIDA],
                    columna=date_column,
                    valor=_format_value(date_value),
                )
            )
            continue

        if _is_future_period(period_dt, as_of=ref):
            issues.append(
                RowIssue(
                    excel_row=str(excel_row),
                    codigo=ISSUE_PERIODO_FUTURO,
                    mensaje=ISSUE_MESSAGES[ISSUE_PERIODO_FUTURO],
                    columna=date_column,
                    valor=_format_value(date_value),
                )
            )
            continue

        if _is_blank(agent_value):
            if not _row_has_kpi_data(row, kpi_columns):
                issues.append(
                    RowIssue(
                        excel_row=str(excel_row),
                        codigo=ISSUE_AGENTE_FALTANTE,
                        mensaje=ISSUE_MESSAGES[ISSUE_AGENTE_FALTANTE],
                        columna=agent_column,
                        valor=_format_value(date_value),
                    )
                )
                continue
            issues.append(
                RowIssue(
                    excel_row=str(excel_row),
                    codigo=ISSUE_AGENTE_FALTANTE,
                    mensaje=ISSUE_MESSAGES[ISSUE_AGENTE_FALTANTE],
                    columna=agent_column,
                    valor=_format_value(date_value),
                )
            )

        valid_indices.append(idx)

    if empty_start is not None:
        _flush_empty_run(issues, start_row=empty_start, end_row=empty_end)

    if not valid_indices:
        return df.iloc[0:0].copy(), issues

    out = df.loc[valid_indices].copy().reset_index(drop=True)
    out["periodo_dt"] = out[date_column].map(parse_iso_date)
    out["periodo_mes_key"] = out["periodo_dt"].map(month_key)
    out["periodo_mes_label"] = out["periodo_dt"].map(month_label)
    out["_agent_sort"] = out[agent_column].map(normalize_sort_text)
    return out, issues
