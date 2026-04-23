from __future__ import annotations

from pathlib import Path

import pandas as pd

from vfiic_kpis.normalize import prepare_common_columns
from vfiic_kpis.spec_loader import AreaSpec


def _validate_source_file_columns(path: Path, spec: AreaSpec) -> list[str]:
    errors: list[str] = []
    header = pd.read_excel(path, sheet_name=spec.sheet_name, nrows=0)
    available = set(header.columns)

    required_columns = {spec.date_column, *spec.agent_columns}
    required_columns.update(kpi.source_column for kpi in spec.kpis)
    missing = sorted(col for col in required_columns if col not in available)
    if missing:
        errors.append(
            f"[{spec.area_id}] {path.name}: faltan columnas requeridas: {missing}"
        )
    return errors


def _validate_spec_sources(input_dir: Path, spec: AreaSpec) -> list[Path]:
    paths = [path for path in sorted(input_dir.glob(spec.source_glob)) if path.is_file()]
    if not paths:
        raise ValueError(
            f"[{spec.area_id}] no se encontraron archivos para source_glob={spec.source_glob!r} en {input_dir}"
        )
    errors: list[str] = []
    for path in paths:
        errors.extend(_validate_source_file_columns(path, spec))
    if errors:
        raise ValueError("\n".join(errors))
    return paths


def read_area_inputs(input_dir: Path, spec: AreaSpec) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    paths = _validate_spec_sources(input_dir, spec)
    for path in paths:
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
    errors: list[str] = []
    for spec in specs:
        try:
            area_df = read_area_inputs(input_dir=input_dir, spec=spec)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not area_df.empty:
            frames.append(area_df)
    if errors:
        raise ValueError("\n".join(errors))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)

