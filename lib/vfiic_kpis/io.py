from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from vfiic_kpis.manifest import FormResolution
from vfiic_kpis.row_validation import RowIssue, validate_and_prepare


@dataclass(frozen=True)
class FormReadResult:
    df: pd.DataFrame
    issues: tuple[RowIssue, ...] = field(default_factory=tuple)


def read_form(resolution: FormResolution) -> FormReadResult:
    """Read a reconciled form file, validate rows, and add normalized columns."""
    if not resolution.is_processable or resolution.file_path is None:
        raise ValueError(
            f"FormResolution {resolution.spec.display_name!r} is not processable: "
            f"{resolution.skip_reason or 'no explicit reason'}"
        )
    if resolution.resolved_date_column is None:
        raise ValueError(
            f"FormResolution {resolution.spec.display_name!r} did not resolve date column."
        )

    sheet = resolution.resolved_sheet if resolution.resolved_sheet is not None else 0
    df = pd.read_excel(resolution.file_path, sheet_name=sheet).copy()

    person_cols = list(resolution.resolved_person_columns)
    agent_column = resolution.spec.agent_output_column
    if not person_cols:
        df[agent_column] = ""
    elif len(person_cols) == 1:
        df[agent_column] = df[person_cols[0]].fillna("").astype(str).str.strip()
    else:
        parts = [df[col].fillna("").astype(str).str.strip() for col in person_cols]
        joined = (
            pd.concat(parts, axis=1)
            .apply(lambda row: " ".join(str(x) for x in row), axis=1)
            .astype(str)
        )
        df[agent_column] = joined.str.replace(r"\s+", " ", regex=True).str.strip()

    df["source_file"] = resolution.file_path.name
    df["area_id"] = resolution.spec.area_id
    df["area_nombre"] = resolution.spec.display_name

    validated, issues = validate_and_prepare(
        df,
        resolution,
        date_column=resolution.resolved_date_column,
        agent_column=agent_column,
    )
    return FormReadResult(df=validated, issues=tuple(issues))
