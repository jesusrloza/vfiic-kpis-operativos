from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class KpiSpec:
    name: str
    source_column: str
    aggregation: str = "sum"
    value_parser: str = "numeric"


@dataclass(frozen=True)
class AreaSpec:
    area_id: str
    display_name: str
    source_glob: str
    sheet_name: str | int | None
    date_column: str
    agent_columns: tuple[str, ...]
    agent_output_column: str
    kpis: tuple[KpiSpec, ...]


def load_area_spec(spec_path: Path) -> AreaSpec:
    with spec_path.open("rb") as fh:
        raw = tomllib.load(fh)

    area_raw = raw["area"]
    kpis_raw = raw.get("kpis", [])
    if not kpis_raw:
        raise ValueError(f"El spec {spec_path} no contiene KPIs.")

    kpis = tuple(
        KpiSpec(
            name=item["name"],
            source_column=item["source_column"],
            aggregation=item.get("aggregation", "sum"),
            value_parser=item.get("value_parser", "numeric"),
        )
        for item in kpis_raw
    )

    return AreaSpec(
        area_id=area_raw["id"],
        display_name=area_raw["display_name"],
        source_glob=area_raw.get("source_glob", "*.xlsx"),
        sheet_name=area_raw.get("sheet_name"),
        date_column=area_raw["date_column"],
        agent_columns=tuple(area_raw.get("agent_columns", [area_raw.get("agent_column", "Agente/Titular")])),
        agent_output_column=area_raw.get("agent_output_column", "Agente/Titular"),
        kpis=kpis,
    )


def load_all_specs(specs_dir: Path) -> list[AreaSpec]:
    return [
        load_area_spec(path)
        for path in sorted(specs_dir.glob("*.toml"))
        if not path.name.startswith("_")
    ]

