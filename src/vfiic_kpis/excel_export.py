from __future__ import annotations

from pathlib import Path

import pandas as pd

from vfiic_kpis.excel_styling import apply_sheet_theme
from vfiic_kpis.excel_theme import load_excel_theme
from vfiic_kpis.paths import (
    DEFAULT_COMPARISON_THEME,
    DEFAULT_PARTITIONED_THEME,
)


def write_partitioned_workbook(
    data: pd.DataFrame,
    output_path: Path,
    theme_path: Path | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    theme = load_excel_theme(theme_path or DEFAULT_PARTITIONED_THEME)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        original = data.drop(columns=["_agent_sort"], errors="ignore")
        original.to_excel(writer, sheet_name="original", index=False)
        apply_sheet_theme(
            writer.book["original"],
            writer.book,
            list(original.columns),
            theme,
        )

        for month_key in sorted(data["periodo_mes_key"].dropna().unique()):
            month_df = data[data["periodo_mes_key"] == month_key].copy()
            month_df = month_df.sort_values(by="_agent_sort", ascending=True)
            month_df = month_df.drop(columns=["_agent_sort"], errors="ignore")
            sheet_title = str(month_key)[:31]
            month_df.to_excel(writer, sheet_name=sheet_title, index=False)
            apply_sheet_theme(
                writer.book[sheet_title],
                writer.book,
                list(month_df.columns),
                theme,
            )


def write_comparison_workbook(
    comparison: pd.DataFrame,
    output_path: Path,
    theme_path: Path | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    theme = load_excel_theme(theme_path or DEFAULT_COMPARISON_THEME)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        comparison.to_excel(writer, sheet_name="comparativo", index=False)
        apply_sheet_theme(
            writer.book["comparativo"],
            writer.book,
            list(comparison.columns),
            theme,
        )
