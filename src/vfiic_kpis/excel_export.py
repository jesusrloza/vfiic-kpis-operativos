from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl.utils import get_column_letter

from vfiic_kpis.excel_styling import apply_comparison_v2_sheet_theme, apply_sheet_theme
from vfiic_kpis.excel_theme import load_excel_theme
from vfiic_kpis.paths import (
    DEFAULT_COMPARISON_THEME,
    DEFAULT_COMPARISON_V2_THEME,
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


def write_comparison_v2_workbook(
    comparison: pd.DataFrame,
    output_path: Path,
    theme_path: Path | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    theme = load_excel_theme(theme_path or DEFAULT_COMPARISON_V2_THEME)
    if comparison.empty:
        raise ValueError("comparison no puede estar vacio para generar comparativo v2.")

    required = {"area_nombre", "indicador_label", "mes_actual_full", "valor_actual", "diferencia", "porcentaje", "tendencia"}
    missing = required.difference(set(comparison.columns))
    if missing:
        raise ValueError(f"comparison no contiene columnas requeridas para v2: {sorted(missing)}")

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for area_nombre, area_df in comparison.groupby("area_nombre", sort=True):
            sheet_title = str(area_nombre)[:31] or "Area"
            area_export = area_df.reset_index(drop=True).copy()
            # Evita encabezados duplicados al renombrar indicador_label -> indicador.
            # Los encabezados duplicados rompen la definición de Table en Excel.
            area_export = area_export.drop(columns=["indicador"], errors="ignore")
            current_month_label = str(area_export["mes_actual_full"].iloc[0])
            previous_month_label = "Mes base"
            has_base = "mes_base_full" in area_export.columns and area_export["mes_base_full"].notna().any()
            if has_base:
                previous_month_label = str(area_export["mes_base_full"].dropna().iloc[0])

            area_export = area_export.rename(
                columns={
                    "indicador_label": "indicador",
                    "valor_actual": current_month_label,
                    "valor_base": previous_month_label,
                }
            )
            export_columns = ["indicador", current_month_label]
            if previous_month_label in area_export.columns:
                export_columns.append(previous_month_label)
            export_columns.extend(["diferencia", "porcentaje", "tendencia"])
            area_export = area_export.loc[:, [c for c in export_columns if c in area_export.columns]]
            area_export.to_excel(writer, sheet_name=sheet_title, index=False, startrow=1)
            ws = writer.book[sheet_title]
            apply_comparison_v2_sheet_theme(
                ws=ws,
                workbook=writer.book,
                internal_columns=list(area_export.columns),
                theme=theme,
                area_title=str(area_nombre),
            )
            if "tendencia" in area_export.columns:
                tendencia_idx = area_export.columns.get_loc("tendencia") + 1
                ws.column_dimensions[get_column_letter(tendencia_idx)].hidden = True
