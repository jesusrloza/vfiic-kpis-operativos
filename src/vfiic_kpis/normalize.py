from __future__ import annotations

from datetime import datetime
import unicodedata

import pandas as pd

SPANISH_MONTH_ABBR = {
    1: "ene",
    2: "feb",
    3: "mar",
    4: "abr",
    5: "may",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "sep",
    10: "oct",
    11: "nov",
    12: "dic",
}


def parse_iso_date(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    return datetime.strptime(text, "%Y-%m-%d")


def month_key(dt: datetime) -> str:
    return f"{dt.year}_{SPANISH_MONTH_ABBR[dt.month]}"


def month_label(dt: datetime) -> str:
    return f"{SPANISH_MONTH_ABBR[dt.month]} {dt.year}"


def normalize_sort_text(value: object) -> str:
    text = "" if value is None else str(value).strip()
    decomposed = unicodedata.normalize("NFKD", text)
    no_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return no_accents.casefold()


def prepare_common_columns(df: pd.DataFrame, date_column: str, agent_column: str) -> pd.DataFrame:
    out = df.copy()
    out["periodo_dt"] = out[date_column].map(parse_iso_date)
    out["periodo_mes_key"] = out["periodo_dt"].map(month_key)
    out["periodo_mes_label"] = out["periodo_dt"].map(month_label)
    out["_agent_sort"] = out[agent_column].map(normalize_sort_text)
    return out

