from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import tomllib

MatchKind = Literal["exact", "prefix", "suffix", "regex"]


@dataclass(frozen=True)
class HeaderTheme:
    fill_rgb: str
    font_color_rgb: str
    bold: bool = True


@dataclass(frozen=True)
class TableTheme:
    style: str
    show_row_stripes: bool = True
    show_column_stripes: bool = False


@dataclass(frozen=True)
class LayoutTheme:
    freeze_panes: str | None
    show_grid_lines: bool = True


@dataclass(frozen=True)
class ColumnWidthTheme:
    min_width: float
    max_width: float
    margin: float


@dataclass(frozen=True)
class ColumnFormatRule:
    match: MatchKind
    pattern: str
    number_format: str
    align: str = "general"
    coerce_large_number_to_text: bool = False

    def compiled_regex(self) -> re.Pattern[str] | None:
        if self.match != "regex":
            return None
        return re.compile(self.pattern)


@dataclass(frozen=True)
class ExcelTheme:
    header: HeaderTheme
    table: TableTheme
    layout: LayoutTheme
    column_width: ColumnWidthTheme
    column_formats: tuple[ColumnFormatRule, ...]
    header_labels: dict[str, str]
    friendly_header_fallback: bool


def _normalize_rgb(value: str) -> str:
    text = value.strip().lstrip("#")
    if len(text) == 6 and all(c in "0123456789abcdefABCDEF" for c in text):
        return text.upper()
    if len(text) == 8 and text[:2].upper() == "FF" and all(c in "0123456789abcdefABCDEF" for c in text[2:]):
        return text[2:].upper()
    raise ValueError(f"Color RGB invalido: {value!r}")


def _rgb_to_argb(rgb6: str) -> str:
    return "FF" + rgb6.upper()


def _parse_match(value: object) -> MatchKind:
    if value not in ("exact", "prefix", "suffix", "regex"):
        raise ValueError(f"match invalido: {value!r}")
    return value  # type: ignore[return-value]


def _parse_rule(raw: dict[str, Any]) -> ColumnFormatRule:
    return ColumnFormatRule(
        match=_parse_match(raw.get("match")),
        pattern=str(raw.get("pattern", "")),
        number_format=str(raw.get("number_format", "General")),
        align=str(raw.get("align", "general")).lower(),
        coerce_large_number_to_text=bool(raw.get("coerce_large_number_to_text", False)),
    )


def load_excel_theme(path: Path) -> ExcelTheme:
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo de tema: {path}")
    data = tomllib.loads(path.read_text(encoding="utf-8"))

    header_raw = data.get("header", {}) or {}
    table_raw = data.get("table", {}) or {}
    layout_raw = data.get("layout", {}) or {}
    width_raw = data.get("column_width", {}) or {}
    labels_raw = data.get("header_labels", {}) or {}
    if not isinstance(labels_raw, dict):
        raise ValueError("header_labels debe ser una tabla clave-valor.")

    formats_raw = data.get("column_formats", [])
    if formats_raw is None:
        formats_raw = []
    if not isinstance(formats_raw, list):
        raise ValueError("column_formats debe ser una lista de tablas.")

    rules: list[ColumnFormatRule] = []
    for idx, item in enumerate(formats_raw):
        if not isinstance(item, dict):
            raise ValueError(f"column_formats[{idx}] debe ser una tabla.")
        rule = _parse_rule(item)
        if rule.match != "regex" and not rule.pattern:
            raise ValueError(f"column_formats[{idx}] requiere pattern.")
        if rule.match == "regex":
            try:
                re.compile(rule.pattern)
            except re.error as exc:
                raise ValueError(f"Regex invalido en column_formats[{idx}]: {exc}") from exc
        rules.append(rule)

    header = HeaderTheme(
        fill_rgb=_normalize_rgb(str(header_raw.get("fill", "1F4E79"))),
        font_color_rgb=_normalize_rgb(str(header_raw.get("font_color", "FFFFFF"))),
        bold=bool(header_raw.get("bold", True)),
    )
    table = TableTheme(
        style=str(table_raw.get("style", "TableStyleMedium2")),
        show_row_stripes=bool(table_raw.get("show_row_stripes", True)),
        show_column_stripes=bool(table_raw.get("show_column_stripes", False)),
    )
    freeze = layout_raw.get("freeze_panes")
    layout = LayoutTheme(
        freeze_panes=None if freeze in (None, "") else str(freeze),
        show_grid_lines=bool(layout_raw.get("show_grid_lines", True)),
    )
    column_width = ColumnWidthTheme(
        min_width=float(width_raw.get("min", 10)),
        max_width=float(width_raw.get("max", 50)),
        margin=float(width_raw.get("margin", 1.5)),
    )

    header_labels = {str(k): str(v) for k, v in labels_raw.items()}
    friendly = bool(data.get("friendly_header_fallback", True))

    return ExcelTheme(
        header=header,
        table=table,
        layout=layout,
        column_width=column_width,
        column_formats=tuple(rules),
        header_labels=header_labels,
        friendly_header_fallback=friendly,
    )


def friendly_header_label(internal: str) -> str:
    """Etiqueta legible cuando no hay mapa explícito: guiones bajo a espacios y capitalización simple."""
    base = internal.replace("_", " ").strip()
    if not base:
        return internal
    parts = base.split()
    return " ".join(p[:1].upper() + p[1:].lower() if p else p for p in parts)


def resolve_header_label(internal: str, theme: ExcelTheme) -> str:
    if internal in theme.header_labels:
        return theme.header_labels[internal]
    if theme.friendly_header_fallback:
        return friendly_header_label(internal)
    return internal


def header_fill_argb(theme: ExcelTheme) -> str:
    return _rgb_to_argb(theme.header.fill_rgb)


def header_font_argb(theme: ExcelTheme) -> str:
    return _rgb_to_argb(theme.header.font_color_rgb)


def match_column_rule(column: str, rule: ColumnFormatRule) -> bool:
    if rule.match == "exact":
        return column == rule.pattern
    if rule.match == "prefix":
        return column.startswith(rule.pattern)
    if rule.match == "suffix":
        return column.endswith(rule.pattern)
    if rule.match == "regex":
        rx = rule.compiled_regex()
        assert rx is not None
        return bool(rx.search(column))
    return False


def first_matching_rule(column: str, rules: tuple[ColumnFormatRule, ...]) -> ColumnFormatRule | None:
    for rule in rules:
        if match_column_rule(column, rule):
            return rule
    return None
