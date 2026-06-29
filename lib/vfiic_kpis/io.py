from __future__ import annotations

import pandas as pd

from vfiic_kpis.manifest import FormResolution
from vfiic_kpis.normalize import prepare_common_columns


def read_form(resolution: FormResolution) -> pd.DataFrame:
    """Read a reconciled form file and add normalized period and agent columns."""
    if not resolution.is_processable or resolution.file_path is None:
        raise ValueError(
            f"FormResolution {resolution.spec.display_name!r} is not processable: "
            f"{resolution.skip_reason or 'no explicit reason'}"
        )
    if resolution.resolved_date_column is None or not resolution.resolved_person_columns:
        raise ValueError(
            f"FormResolution {resolution.spec.display_name!r} did not resolve date or person columns."
        )

    sheet = resolution.resolved_sheet if resolution.resolved_sheet is not None else 0
    df = pd.read_excel(resolution.file_path, sheet_name=sheet).copy()

    person_cols = list(resolution.resolved_person_columns)
    if len(person_cols) == 1:
        df[resolution.spec.agent_output_column] = (
            df[person_cols[0]].fillna("").astype(str).str.strip()
        )
    else:
        parts = [df[col].fillna("").astype(str).str.strip() for col in person_cols]
        # pandas>=2.4: agg(" ".join) on an empty row-wise frame returns DataFrame; use apply.
        joined = (
            pd.concat(parts, axis=1)
            .apply(lambda row: " ".join(str(x) for x in row), axis=1)
            .astype(str)
        )
        df[resolution.spec.agent_output_column] = (
            joined.str.replace(r"\s+", " ", regex=True).str.strip()
        )

    df["source_file"] = resolution.file_path.name
    df["area_id"] = resolution.spec.area_id
    df["area_nombre"] = resolution.spec.display_name

    return prepare_common_columns(
        df,
        date_column=resolution.resolved_date_column,
        agent_column=resolution.spec.agent_output_column,
    )
