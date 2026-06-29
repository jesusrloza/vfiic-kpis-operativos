from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re

import pandas as pd

from vfiic_kpis.manifest import FormResolution
from vfiic_kpis.normalize import month_label_full
from vfiic_kpis.text_match import find_matching_column
from vfiic_kpis.yaml_loader import FormSpec, KpiSpec


@dataclass(frozen=True)
class FormComparisonResult:
    """Tabular comparison result for one form in the stacked workbook.

    `df` has one row per KPI with nullable MoM and YoY values. Month-dependent
    header labels are exposed as attributes for the Excel writer.
    """

    spec: FormSpec
    df: pd.DataFrame
    mes_actual_label: str
    mes_anterior_label: str
    mes_anio_anterior_label: str


def _safe_percentage(delta: float | None, baseline: float | None) -> float | None:
    if delta is None or baseline in (None, 0):
        return None
    return (delta / baseline) * 100.0


def _parse_numeric_like(value: object, parser: str) -> float | None:
    if parser == "numeric":
        parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
        return None if pd.isna(parsed) else float(parsed)
    if parser == "sum_cantidad":
        text = "" if value is None else str(value)
        values = re.findall(r"Cantidad:\s*([0-9]+(?:\.[0-9]+)?)", text)
        return float(sum(float(item) for item in values))
    raise ValueError(f"Unsupported value_parser: {parser}")


def _aggregate_for_month(
    df: pd.DataFrame,
    month_dt: datetime,
    column: str,
    aggregation: str,
    value_parser: str,
) -> float:
    mask = (df["periodo_dt"].dt.year == month_dt.year) & (df["periodo_dt"].dt.month == month_dt.month)
    series = df.loc[mask, column]
    parsed = [
        value
        for value in series.map(lambda x: _parse_numeric_like(x, value_parser)).tolist()
        if value is not None
    ]
    if aggregation == "count":
        return float(len(parsed))
    if aggregation == "avg":
        return float(sum(parsed) / len(parsed)) if parsed else 0.0
    return float(sum(parsed))


def _trend_kind(delta: float | None) -> str:
    """Trend always uses the convention that higher is better."""
    if delta is None:
        return "na"
    if delta == 0:
        return "neutral"
    return "positive" if delta > 0 else "negative"


def _previous_month(dt: datetime) -> datetime:
    if dt.month == 1:
        return datetime(dt.year - 1, 12, 1)
    return datetime(dt.year, dt.month - 1, 1)


def _year_ago(dt: datetime) -> datetime:
    return datetime(dt.year - 1, dt.month, 1)


def build_form_comparison(df: pd.DataFrame, resolution: FormResolution) -> FormComparisonResult | None:
    """Build the MoM + YoY comparison for one form.

    - The latest month with data defines dynamic labels.
    - MoM columns are `None` when the previous month is missing.
    - YoY columns are `None` when the same month last year is missing.
    - Each KPI sums all rows in the month.
    Returns `None` when no period could be parsed.
    """
    if df.empty or "periodo_dt" not in df.columns:
        return None
    periods = df["periodo_dt"].dropna()
    if periods.empty:
        return None

    last_dt: datetime = periods.max().to_pydatetime()
    prev_dt = _previous_month(last_dt)
    yoy_dt = _year_ago(last_dt)

    has_prev = ((df["periodo_dt"].dt.year == prev_dt.year) & (df["periodo_dt"].dt.month == prev_dt.month)).any()
    has_yoy = ((df["periodo_dt"].dt.year == yoy_dt.year) & (df["periodo_dt"].dt.month == yoy_dt.month)).any()

    available_columns = list(df.columns)
    rows: list[dict] = []
    for kpi in resolution.spec.kpis:
        actual_column = find_matching_column(kpi.columna_origen, available_columns)
        if actual_column is None:
            continue

        last_value = _aggregate_for_month(df, last_dt, actual_column, kpi.aggregation, kpi.value_parser)
        prev_value = (
            _aggregate_for_month(df, prev_dt, actual_column, kpi.aggregation, kpi.value_parser)
            if has_prev
            else None
        )
        yoy_value = (
            _aggregate_for_month(df, yoy_dt, actual_column, kpi.aggregation, kpi.value_parser)
            if has_yoy
            else None
        )

        diff_mom = None if prev_value is None else last_value - prev_value
        diff_yoy = None if yoy_value is None else last_value - yoy_value

        rows.append(
            {
                "indicador": kpi.descripcion,
                "valor_actual": last_value,
                "valor_mes_anterior": prev_value,
                "diferencia_mom": diff_mom,
                "porcentaje_mom": _safe_percentage(diff_mom, prev_value),
                "tendencia_mom": _trend_kind(diff_mom),
                "valor_anio_anterior": yoy_value,
                "diferencia_yoy": diff_yoy,
                "porcentaje_yoy": _safe_percentage(diff_yoy, yoy_value),
                "tendencia_yoy": _trend_kind(diff_yoy),
            }
        )

    if not rows:
        return None

    return FormComparisonResult(
        spec=resolution.spec,
        df=pd.DataFrame(rows),
        mes_actual_label=month_label_full(last_dt),
        mes_anterior_label=month_label_full(prev_dt),
        mes_anio_anterior_label=month_label_full(yoy_dt),
    )


# Compat helpers ---------------------------------------------------------------
# Mantienen import path estable para tests que aún consultan utilidades.

__all__ = [
    "FormComparisonResult",
    "build_form_comparison",
    "_aggregate_for_month",
    "_parse_numeric_like",
    "_safe_percentage",
    "_trend_kind",
]
