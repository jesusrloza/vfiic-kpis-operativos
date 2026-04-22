from __future__ import annotations

from pathlib import Path

import pandas as pd

from vfiic_kpis.normalize import prepare_common_columns
from vfiic_kpis.spec_loader import AreaSpec


def read_area_inputs(input_dir: Path, spec: AreaSpec) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in sorted(input_dir.glob(spec.source_glob)):
        if not path.is_file():
            continue
        df = pd.read_excel(path, sheet_name=spec.sheet_name)
        df = df.copy()
        # Algunas fuentes separan nombre completo en varias columnas.
        if len(spec.agent_columns) == 1:
            df[spec.agent_output_column] = df[spec.agent_columns[0]].fillna("").astype(str).str.strip()
        else:
            parts = [df[col].fillna("").astype(str).str.strip() for col in spec.agent_columns]
            df[spec.agent_output_column] = (
                pd.concat(parts, axis=1)
                .agg(" ".join, axis=1)
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
            )
        df["source_file"] = path.name
        df["area_id"] = spec.area_id
        df["area_nombre"] = spec.display_name
        frames.append(df)

    if not frames:
        return pd.DataFrame()
    merged = pd.concat(frames, ignore_index=True)
    return prepare_common_columns(
        merged,
        date_column=spec.date_column,
        agent_column=spec.agent_output_column,
    )


def read_all_inputs(input_dir: Path, specs: list[AreaSpec]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for spec in specs:
        area_df = read_area_inputs(input_dir=input_dir, spec=spec)
        if not area_df.empty:
            frames.append(area_df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)

