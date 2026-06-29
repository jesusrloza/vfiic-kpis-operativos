from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from vfiic_kpis.text_match import slugify
from vfiic_kpis.user_messages import YAML_GUIDE_REF

DEFAULT_SHEET_NAME = "Form responses"
DEFAULT_DATE_COLUMN_ALIASES: tuple[str, ...] = ("Periodo Evaluado", "Periodo a Evaluar")
DEFAULT_AGENT_OUTPUT_COLUMN = "Agente/Titular"
DEFAULT_VALUE_PARSER = "numeric"
DEFAULT_AGGREGATION = "sum"


@dataclass(frozen=True)
class KpiSpec:
    columna_origen: str
    descripcion: str
    aggregation: str = DEFAULT_AGGREGATION
    value_parser: str = DEFAULT_VALUE_PARSER


@dataclass(frozen=True)
class FormSpec:
    """Full definition of a reportable form."""

    area_id: str
    display_name: str
    direccion: str
    archivo: str | None
    hoja: str | int | None
    columna_fecha_aliases: tuple[str, ...]
    columnas_persona: tuple[str, ...]
    agent_output_column: str
    kpis: tuple[KpiSpec, ...]

    @property
    def has_ingesta(self) -> bool:
        return bool(self.archivo and self.columnas_persona and self.columna_fecha_aliases)


def _coerce_str_list(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                items.append(text)
        return tuple(items)
    raise ValueError(f"Expected string or list of strings, got: {value!r}")


def _parse_kpi_entry(entry: Any, *, form_label: str, index: int) -> KpiSpec:
    if not isinstance(entry, dict):
        raise ValueError(
            f"[{form_label}] kpi #{index}: expected a mapping with `columna_origen` and `descripcion`."
        )
    columna = str(entry.get("columna_origen", "")).strip()
    descripcion = str(entry.get("descripcion", "")).strip()
    if not columna:
        raise ValueError(f"[{form_label}] kpi #{index}: `columna_origen` is required.")
    if not descripcion:
        descripcion = columna
    aggregation = str(entry.get("aggregation", DEFAULT_AGGREGATION)).strip() or DEFAULT_AGGREGATION
    if aggregation not in ("sum", "count", "avg"):
        raise ValueError(
            f"[{form_label}] kpi `{columna}`: invalid `aggregation` {aggregation!r}; use sum, count, or avg."
        )
    value_parser = str(entry.get("value_parser", DEFAULT_VALUE_PARSER)).strip() or DEFAULT_VALUE_PARSER
    if value_parser not in ("numeric", "sum_cantidad"):
        raise ValueError(
            f"[{form_label}] kpi `{columna}`: invalid `value_parser` {value_parser!r}; "
            "use numeric or sum_cantidad."
        )
    return KpiSpec(
        columna_origen=columna,
        descripcion=descripcion,
        aggregation=aggregation,
        value_parser=value_parser,
    )


def _parse_form(direccion: str, display_name: str, raw_value: Any) -> FormSpec:
    label = f"{direccion} :: {display_name}"

    if isinstance(raw_value, list):
        raise ValueError(
            f"[{label}] invalid form: use a block with `ingesta` and `kpis`. See {YAML_GUIDE_REF}."
        )
    if not isinstance(raw_value, dict):
        raise ValueError(f"[{label}] invalid form: expected a mapping with `ingesta` and `kpis`.")

    ingesta_raw = raw_value.get("ingesta", {}) or {}
    if not isinstance(ingesta_raw, dict):
        raise ValueError(f"[{label}] `ingesta` must be a mapping.")
    kpis_raw = raw_value.get("kpis", [])

    if not isinstance(kpis_raw, list) or not kpis_raw:
        raise ValueError(f"[{label}] no KPIs defined in the YAML.")

    kpis = tuple(
        _parse_kpi_entry(item, form_label=label, index=index)
        for index, item in enumerate(kpis_raw)
    )

    explicit_id = ingesta_raw.get("id")
    area_id = str(explicit_id).strip() if explicit_id else slugify(display_name)

    archivo = ingesta_raw.get("archivo")
    archivo_str = str(archivo).strip() if archivo else None

    hoja_raw = ingesta_raw.get("hoja", DEFAULT_SHEET_NAME if archivo_str else None)
    hoja: str | int | None
    if hoja_raw is None or hoja_raw == "":
        hoja = None
    elif isinstance(hoja_raw, int) and not isinstance(hoja_raw, bool):
        hoja = hoja_raw
    else:
        hoja = str(hoja_raw).strip() or None

    columna_fecha_aliases = _coerce_str_list(ingesta_raw.get("columna_fecha"))
    if not columna_fecha_aliases:
        columna_fecha_aliases = DEFAULT_DATE_COLUMN_ALIASES

    columnas_persona = _coerce_str_list(ingesta_raw.get("columnas_persona"))

    agent_output_raw = ingesta_raw.get("agent_output_column")
    agent_output_column = (
        str(agent_output_raw).strip()
        if agent_output_raw
        else DEFAULT_AGENT_OUTPUT_COLUMN
    )

    return FormSpec(
        area_id=area_id,
        display_name=display_name,
        direccion=direccion,
        archivo=archivo_str,
        hoja=hoja,
        columna_fecha_aliases=columna_fecha_aliases,
        columnas_persona=columnas_persona,
        agent_output_column=agent_output_column,
        kpis=kpis,
    )


def load_forms_from_yaml(yaml_path: Path) -> list[FormSpec]:
    """Load the indicators YAML and return one `FormSpec` per form."""
    if not yaml_path.is_file():
        raise FileNotFoundError(f"Schema YAML file not found: {yaml_path}")
    with yaml_path.open("r", encoding="utf-8") as handle:
        try:
            raw = yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML in {yaml_path}: {exc}") from exc
    if raw is None:
        return []
    if not isinstance(raw, dict):
        raise ValueError(f"YAML root in {yaml_path} must be a mapping.")

    forms: list[FormSpec] = []
    seen_ids: set[str] = set()
    for direccion, forms_raw in raw.items():
        if forms_raw is None:
            continue
        if not isinstance(forms_raw, dict):
            raise ValueError(f"[{direccion}] expected a mapping of forms.")
        for display_name, form_raw in forms_raw.items():
            if form_raw is None:
                continue
            spec = _parse_form(str(direccion), str(display_name), form_raw)
            if spec.area_id in seen_ids:
                raise ValueError(
                    f"Duplicate `area_id`: {spec.area_id!r}. "
                    "Set an explicit `id` under `ingesta` to distinguish forms."
                )
            seen_ids.add(spec.area_id)
            forms.append(spec)
    return forms
