from __future__ import annotations

import re
from dataclasses import dataclass
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
class TitleTheme:
    fill_rgb: str
    font_color_rgb: str
    bold: bool = True


@dataclass(frozen=True)
class SemanticColorsTheme:
    positive_rgb: str
    negative_rgb: str
    neutral_rgb: str


@dataclass(frozen=True)
class RowStripesTheme:
    """Rayado alterno en cuerpo de datos del comparativo apilado.

    `even_rgb` aplica a la primera fila de cada bloque (offset 0, 2, …);
    `odd_rgb` a offset 1, 3, … (coincide con screenshot: blanco, azul claro, …).
    """

    enabled: bool
    even_rgb: str
    odd_rgb: str


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
    title: TitleTheme
    table: TableTheme
    layout: LayoutTheme
    column_width: ColumnWidthTheme
    semantic_colors: SemanticColorsTheme
    row_stripes: RowStripesTheme
    column_formats: tuple[ColumnFormatRule, ...]
    header_labels: dict[str, str]
    friendly_header_fallback: bool


def _normalize_rgb(value: str) -> str:
    text = value.strip().lstrip("#")
    if len(text) == 6 and all(c in "0123456789abcdefABCDEF" for c in text):
        return text.upper()
    if len(text) == 8 and text[:2].upper() == "FF" and all(c in "0123456789abcdefABCDEF" for c in text[2:]):
        return text[2:].upper()
    raise ValueError(f"Invalid RGB color: {value!r}")


def _rgb_to_argb(rgb6: str) -> str:
    return "FF" + rgb6.upper()


def _parse_match(value: object) -> MatchKind:
    if value not in ("exact", "prefix", "suffix", "regex"):
        raise ValueError(f"Invalid match kind: {value!r}")
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
        raise FileNotFoundError(f"Theme file not found: {path}")
    data = tomllib.loads(path.read_text(encoding="utf-8"))

    header_raw = data.get("header", {}) or {}
    title_raw = data.get("title", {}) or {}
    table_raw = data.get("table", {}) or {}
    layout_raw = data.get("layout", {}) or {}
    width_raw = data.get("column_width", {}) or {}
    semantic_raw = data.get("semantic_colors", {}) or {}
    row_stripes_raw = data.get("row_stripes", {}) or {}
    labels_raw = data.get("header_labels", {}) or {}
    if not isinstance(labels_raw, dict):
        raise ValueError("header_labels must be a key-value table.")

    formats_raw = data.get("column_formats", [])
    if formats_raw is None:
        formats_raw = []
    if not isinstance(formats_raw, list):
        raise ValueError("column_formats must be a list of tables.")

    rules: list[ColumnFormatRule] = []
    for idx, item in enumerate(formats_raw):
        if not isinstance(item, dict):
            raise ValueError(f"column_formats[{idx}] must be a table.")
        rule = _parse_rule(item)
        if rule.match != "regex" and not rule.pattern:
            raise ValueError(f"column_formats[{idx}] requires pattern.")
        if rule.match == "regex":
            try:
                re.compile(rule.pattern)
            except re.error as exc:
                raise ValueError(f"Invalid regex in column_formats[{idx}]: {exc}") from exc
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
    title = TitleTheme(
        fill_rgb=_normalize_rgb(str(title_raw.get("fill", header.fill_rgb))),
        font_color_rgb=_normalize_rgb(str(title_raw.get("font_color", header.font_color_rgb))),
        bold=bool(title_raw.get("bold", True)),
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
    semantic_colors = SemanticColorsTheme(
        positive_rgb=_normalize_rgb(str(semantic_raw.get("positive", "1F4E79"))),
        negative_rgb=_normalize_rgb(str(semantic_raw.get("negative", "C00000"))),
        neutral_rgb=_normalize_rgb(str(semantic_raw.get("neutral", "000000"))),
    )
    if row_stripes_raw:
        row_stripes = RowStripesTheme(
            enabled=bool(row_stripes_raw.get("enabled", False)),
            even_rgb=_normalize_rgb(str(row_stripes_raw.get("even", "FFFFFF"))),
            odd_rgb=_normalize_rgb(str(row_stripes_raw.get("odd", "D9E2F3"))),
        )
    else:
        row_stripes = RowStripesTheme(
            enabled=False,
            even_rgb="FFFFFF",
            odd_rgb="D9E2F3",
        )

    header_labels = {str(k): str(v) for k, v in labels_raw.items()}
    friendly = bool(data.get("friendly_header_fallback", True))

    return ExcelTheme(
        header=header,
        title=title,
        table=table,
        layout=layout,
        column_width=column_width,
        semantic_colors=semantic_colors,
        row_stripes=row_stripes,
        column_formats=tuple(rules),
        header_labels=header_labels,
        friendly_header_fallback=friendly,
    )


def friendly_header_label(internal: str) -> str:
    """Fallback readable label when no explicit theme mapping exists."""
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


def title_fill_argb(theme: ExcelTheme) -> str:
    return _rgb_to_argb(theme.title.fill_rgb)


def title_font_argb(theme: ExcelTheme) -> str:
    return _rgb_to_argb(theme.title.font_color_rgb)


def row_stripe_fill_argb(theme: ExcelTheme, row_offset: int) -> str:
    """Color de relleno para la fila de datos `row_offset` (0 = primera fila del bloque)."""
    rgb = theme.row_stripes.even_rgb if row_offset % 2 == 0 else theme.row_stripes.odd_rgb
    return _rgb_to_argb(rgb)


def semantic_color_argb(theme: ExcelTheme, kind: str) -> str:
    if kind == "positive":
        return _rgb_to_argb(theme.semantic_colors.positive_rgb)
    if kind == "negative":
        return _rgb_to_argb(theme.semantic_colors.negative_rgb)
    return _rgb_to_argb(theme.semantic_colors.neutral_rgb)


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
