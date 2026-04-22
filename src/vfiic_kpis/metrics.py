from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re

import pandas as pd

from vfiic_kpis.normalize import month_label
from vfiic_kpis.spec_loader import AreaSpec, KpiSpec


@dataclass(frozen=True)
class ComparisonResult:
    area_id: str
    area_nombre: str
    indicador: str
    ultimo_mes: str
    valor_ultimo_mes: float
    mes_anterior: str | None
    valor_mes_anterior: float | None
    diferencia_numero_mom: float | None
    diferencia_porcentaje_mom: float | None
    mes_anio_previo: str | None
    valor_mes_anio_previo: float | None
    diferencia_numero_yoy: float | None
    diferencia_porcentaje_yoy: float | None


def _safe_percentage(delta: float | None, baseline: float | None) -> float | None:
    if delta is None or baseline in (None, 0):
        return None
    return (delta / baseline) * 100.0


def _parse_numeric_like(value: object, parser: str) -> float:
    if parser == "numeric":
        parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
        return 0.0 if pd.isna(parsed) else float(parsed)

    if parser == "sum_cantidad":
        text = "" if value is None else str(value)
        values = re.findall(r"Cantidad:\s*([0-9]+(?:\.[0-9]+)?)", text)
        return float(sum(float(item) for item in values))

    raise ValueError(f"value_parser no soportado: {parser}")


def _sum_for_month(df: pd.DataFrame, month_dt: datetime, kpi: KpiSpec) -> float:
    mask = (df["periodo_dt"].dt.year == month_dt.year) & (df["periodo_dt"].dt.month == month_dt.month)
    series = df.loc[mask, kpi.source_column]
    return float(series.map(lambda x: _parse_numeric_like(x, kpi.value_parser)).sum())


def build_monthly_comparison(df: pd.DataFrame, specs: list[AreaSpec]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    results: list[ComparisonResult] = []
    for spec in specs:
        area_df = df[df["area_id"] == spec.area_id].copy()
        if area_df.empty:
            continue

        last_dt = area_df["periodo_dt"].max().to_pydatetime()
        prev_dt = datetime(last_dt.year - 1, 12, 1) if last_dt.month == 1 else datetime(last_dt.year, last_dt.month - 1, 1)
        yoy_dt = datetime(last_dt.year - 1, last_dt.month, 1)

        has_prev = ((area_df["periodo_dt"].dt.year == prev_dt.year) & (area_df["periodo_dt"].dt.month == prev_dt.month)).any()
        has_yoy = ((area_df["periodo_dt"].dt.year == yoy_dt.year) & (area_df["periodo_dt"].dt.month == yoy_dt.month)).any()

        for kpi in spec.kpis:
            last_value = _sum_for_month(area_df, last_dt, kpi)
            prev_value = _sum_for_month(area_df, prev_dt, kpi) if has_prev else None
            yoy_value = _sum_for_month(area_df, yoy_dt, kpi) if has_yoy else None

            diff_mom = None if prev_value is None else last_value - prev_value
            diff_yoy = None if yoy_value is None else last_value - yoy_value

            results.append(
                ComparisonResult(
                    area_id=spec.area_id,
                    area_nombre=spec.display_name,
                    indicador=kpi.name,
                    ultimo_mes=month_label(last_dt),
                    valor_ultimo_mes=last_value,
                    mes_anterior=month_label(prev_dt) if has_prev else None,
                    valor_mes_anterior=prev_value,
                    diferencia_numero_mom=diff_mom,
                    diferencia_porcentaje_mom=_safe_percentage(diff_mom, prev_value),
                    mes_anio_previo=month_label(yoy_dt) if has_yoy else None,
                    valor_mes_anio_previo=yoy_value,
                    diferencia_numero_yoy=diff_yoy,
                    diferencia_porcentaje_yoy=_safe_percentage(diff_yoy, yoy_value),
                )
            )

    return pd.DataFrame([result.__dict__ for result in results])

