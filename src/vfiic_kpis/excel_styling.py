from __future__ import annotations

import re
from datetime import date, datetime, time
from typing import Any

from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.filters import AutoFilter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.worksheet import Worksheet

from vfiic_kpis.excel_theme import (
    ColumnFormatRule,
    ExcelTheme,
    first_matching_rule,
    header_fill_argb,
    header_font_argb,
    resolve_header_label,
    semantic_color_argb,
    title_fill_argb,
    title_font_argb,
)


def _alignment_for(align: str) -> Alignment | None:
    value = align.lower()
    if value in ("", "general", "auto"):
        return None
    if value not in ("left", "right", "center", "justify"):
        return None
    return Alignment(horizontal=value, vertical="center")


def _collect_table_names(workbook: Workbook) -> set[str]:
    names: set[str] = set()
    for worksheet in workbook.worksheets:
        for table in worksheet.tables.values():
            names.add(table.displayName)
    return names


def _allocate_table_display_name(workbook: Workbook, seed: str) -> str:
    raw = re.sub(r"[^A-Za-z0-9_]", "_", seed).strip("_") or "Tabla"
    if raw[0].isdigit():
        raw = "T_" + raw
    base = raw[:200]
    used = _collect_table_names(workbook)
    candidate = base
    counter = 1
    while candidate in used:
        suffix = f"_{counter}"
        candidate = (base[: 200 - len(suffix)] + suffix)[:255]
        counter += 1
    return candidate[:255]


def _maybe_coerce_large_number(cell: Any, rule: ColumnFormatRule) -> None:
    if not rule.coerce_large_number_to_text:
        return
    value = cell.value
    if isinstance(value, float) and value.is_integer():
        iv = int(value)
        if abs(iv) >= 10**12:
            cell.value = str(iv)
        return
    if isinstance(value, int) and abs(value) >= 10**12:
        cell.value = str(value)


def _apply_body_formats(
    ws: Worksheet,
    internal_columns: list[str],
    theme: ExcelTheme,
    data_row_start: int,
) -> None:
    max_row = ws.max_row or 0
    max_col = ws.max_column or 0
    if max_row < data_row_start or max_col < 1:
        return

    for col_idx in range(1, max_col + 1):
        internal = internal_columns[col_idx - 1] if col_idx - 1 < len(internal_columns) else ""
        rule = first_matching_rule(internal, theme.column_formats) if internal else None
        for row_idx in range(data_row_start, max_row + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            if rule is not None:
                _maybe_coerce_large_number(cell, rule)
                cell.number_format = rule.number_format
                align = _alignment_for(rule.align)
                if align is not None:
                    cell.alignment = align
            else:
                value = cell.value
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                elif isinstance(value, (datetime, date, time)):
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                elif isinstance(value, str):
                    cell.alignment = Alignment(horizontal="left", vertical="center")


def _paint_header_row(ws: Worksheet, theme: ExcelTheme, columns: list[str], row_idx: int = 1) -> None:
    fill = PatternFill(fill_type="solid", fgColor=header_fill_argb(theme))
    font = Font(
        bold=theme.header.bold,
        color=header_font_argb(theme),
    )
    for col_idx, internal in enumerate(columns, start=1):
        cell = ws.cell(row=row_idx, column=col_idx)
        cell.value = resolve_header_label(internal, theme)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _set_column_widths(ws: Worksheet, theme: ExcelTheme) -> None:
    max_row = ws.max_row or 0
    max_col = ws.max_column or 0
    if max_col < 1:
        return

    for col_idx in range(1, max_col + 1):
        letter = get_column_letter(col_idx)
        longest = 0
        for row_idx in range(1, max_row + 1):
            value = ws.cell(row=row_idx, column=col_idx).value
            if value is None:
                continue
            longest = max(longest, len(str(value)))
        width = min(
            max(theme.column_width.min_width, longest + theme.column_width.margin),
            theme.column_width.max_width,
        )
        ws.column_dimensions[letter].width = width


def _apply_table(ws: Worksheet, workbook: Workbook, theme: ExcelTheme, header_row: int = 1) -> None:
    max_row = ws.max_row or 0
    max_col = ws.max_column or 0
    if max_row < header_row + 1 or max_col < 1:
        return

    ref = f"A{header_row}:{get_column_letter(max_col)}{max_row}"
    display = _allocate_table_display_name(workbook, ws.title or "Tabla")
    table = Table(displayName=display, ref=ref)
    table.tableStyleInfo = TableStyleInfo(
        name=theme.table.style,
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=theme.table.show_row_stripes,
        showColumnStripes=theme.table.show_column_stripes,
    )
    ws.add_table(table)


def apply_sheet_theme(
    ws: Worksheet,
    workbook: Workbook,
    internal_columns: list[str],
    theme: ExcelTheme,
) -> None:
    """Aplica maquetación a una hoja ya escrita por pandas (fila 1 = encabezados internos)."""
    if not internal_columns:
        return

    max_col_ws = ws.max_column or 0
    if max_col_ws < 1:
        return

    columns = list(internal_columns)[:max_col_ws]

    _paint_header_row(ws, theme, columns)
    _apply_body_formats(ws, columns, theme, data_row_start=2)
    _set_column_widths(ws, theme)

    ws.sheet_view.showGridLines = theme.layout.show_grid_lines
    if theme.layout.freeze_panes:
        ws.freeze_panes = theme.layout.freeze_panes

    max_row = ws.max_row or 0
    max_col = ws.max_column or 0
    # Una Tabla (ListObject) ya escribe <autoFilter> en tableN.xml. Un segundo
    # autoFilter en la hoja (worksheet) con el mismo ref provoca reparación en Excel.
    will_add_table = max_row >= 2 and max_col >= 1
    if will_add_table:
        ws.auto_filter = AutoFilter()
    elif max_row >= 1 and max_col >= 1:
        ws.auto_filter.ref = f"A1:{get_column_letter(max_col)}{max_row}"

    _apply_table(ws, workbook, theme)
    _paint_header_row(ws, theme, columns)


def _apply_area_title_row(ws: Worksheet, title: str, theme: ExcelTheme, max_col: int) -> None:
    if max_col < 1:
        return
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
    cell = ws.cell(row=1, column=1)
    cell.value = title
    cell.fill = PatternFill(fill_type="solid", fgColor=title_fill_argb(theme))
    cell.font = Font(
        bold=theme.title.bold,
        color=title_font_argb(theme),
        size=12,
    )
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 24


def _paint_semantic_cells(
    ws: Worksheet,
    internal_columns: list[str],
    theme: ExcelTheme,
    data_row_start: int,
) -> None:
    max_row = ws.max_row or 0
    if max_row < data_row_start:
        return

    tendencia_idx = None
    difference_targets: set[int] = set()
    for idx, internal in enumerate(internal_columns, start=1):
        if internal == "tendencia":
            tendencia_idx = idx
        if internal in ("diferencia", "porcentaje"):
            difference_targets.add(idx)

    if tendencia_idx is None or not difference_targets:
        return

    for row_idx in range(data_row_start, max_row + 1):
        trend_raw = ws.cell(row=row_idx, column=tendencia_idx).value
        trend = "neutral" if trend_raw is None else str(trend_raw)
        color = semantic_color_argb(theme, trend)
        for col_idx in difference_targets:
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = Font(
                name=cell.font.name,
                size=cell.font.size,
                bold=cell.font.bold,
                italic=cell.font.italic,
                underline=cell.font.underline,
                strike=cell.font.strike,
                color=color,
            )


def apply_comparison_v2_sheet_theme(
    ws: Worksheet,
    workbook: Workbook,
    internal_columns: list[str],
    theme: ExcelTheme,
    area_title: str,
) -> None:
    """Aplica maquetación V2 con título de área y color semántico por tendencia."""
    if not internal_columns:
        return
    max_col_ws = ws.max_column or 0
    if max_col_ws < 1:
        return

    columns = list(internal_columns)[:max_col_ws]
    _apply_area_title_row(ws, area_title, theme, max_col_ws)
    _paint_header_row(ws, theme, columns, row_idx=2)
    _apply_body_formats(ws, columns, theme, data_row_start=3)
    _paint_semantic_cells(ws, columns, theme, data_row_start=3)
    _set_column_widths(ws, theme)

    ws.sheet_view.showGridLines = theme.layout.show_grid_lines
    ws.freeze_panes = "A3"
    _apply_table(ws, workbook, theme, header_row=2)
    _paint_header_row(ws, theme, columns, row_idx=2)
