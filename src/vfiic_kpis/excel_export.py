from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_partitioned_workbook(
    data: pd.DataFrame,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        original = data.drop(columns=["_agent_sort"], errors="ignore")
        original.to_excel(writer, sheet_name="original", index=False)

        for month_key in sorted(data["periodo_mes_key"].dropna().unique()):
            month_df = data[data["periodo_mes_key"] == month_key].copy()
            month_df = month_df.sort_values(by="_agent_sort", ascending=True)
            month_df = month_df.drop(columns=["_agent_sort"], errors="ignore")
            month_df.to_excel(writer, sheet_name=str(month_key)[:31], index=False)


def write_comparison_workbook(comparison: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        comparison.to_excel(writer, sheet_name="comparativo", index=False)

