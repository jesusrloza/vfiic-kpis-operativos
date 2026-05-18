from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from vfiic_kpis.text_match import (
    find_first_matching_column,
    find_matching_column,
    fold,
)
from vfiic_kpis.user_messages import (
    SKIP_DATE_COLUMN_MISMATCH,
    SKIP_FILE_NOT_FOUND_IN_INPUTS,
    SKIP_HEADER_READ_FAILED,
    SKIP_INCOMPLETE_YAML_CONFIG,
    SKIP_KPI_COLUMN_MISMATCH,
    SKIP_PERSON_COLUMN_MISMATCH,
    format_user_message,
)
from vfiic_kpis.yaml_loader import FormSpec


@dataclass(frozen=True)
class FormResolution:
    """Result of matching a `FormSpec` against files in `inputs/`.

    A form is processable when a file, sheet, date column, and at least one KPI
    column were resolved. Missing KPI columns are listed in `missing_columns`.
    """

    spec: FormSpec
    file_path: Path | None
    resolved_sheet: str | int | None
    resolved_date_column: str | None
    resolved_person_columns: tuple[str, ...]
    available_kpis: tuple[str, ...]
    missing_columns: tuple[str, ...]
    skip_reason: str | None
    skip_detail: str | None = None

    @property
    def is_processable(self) -> bool:
        return self.skip_reason is None and bool(self.available_kpis)


@dataclass(frozen=True)
class ReconciliationReport:
    matched: tuple[FormResolution, ...] = field(default_factory=tuple)
    yaml_without_file: tuple[FormResolution, ...] = field(default_factory=tuple)
    yaml_without_ingesta: tuple[FormResolution, ...] = field(default_factory=tuple)
    yaml_with_column_issues: tuple[FormResolution, ...] = field(default_factory=tuple)
    files_without_yaml: tuple[Path, ...] = field(default_factory=tuple)


def _read_excel_header(path: Path, sheet: str | int | None) -> tuple[list[str], str | int]:
    """Read only the header row from an xlsx file and return the resolved sheet."""
    sheet_arg: str | int = sheet if sheet is not None else 0
    header = pd.read_excel(path, sheet_name=sheet_arg, nrows=0)
    columns = [str(col) for col in header.columns]
    return columns, sheet_arg


def _candidate_filenames(spec: FormSpec) -> list[str]:
    """Return plausible file names for a `FormSpec`."""
    candidates: list[str] = []
    if spec.archivo:
        candidates.append(spec.archivo)
    candidates.append(f"{spec.display_name}.xlsx")
    return candidates


def _resolve_file(spec: FormSpec, input_files: list[Path]) -> Path | None:
    """Locate the form file by exact or folded name."""
    if not spec.archivo:
        return None
    candidates_by_name = {fold(p.name): p for p in input_files}
    target = fold(spec.archivo)
    return candidates_by_name.get(target)


def reconcile(
    forms: list[FormSpec],
    input_dir: Path,
) -> ReconciliationReport:
    """Match `FormSpec` entries against xlsx files in `input_dir`."""
    input_files: list[Path] = sorted(p for p in input_dir.glob("*.xlsx") if p.is_file())
    files_by_folded_name = {fold(p.name): p for p in input_files}

    matched: list[FormResolution] = []
    yaml_without_ingesta: list[FormResolution] = []
    yaml_without_file: list[FormResolution] = []
    yaml_with_column_issues: list[FormResolution] = []
    referenced_files: set[Path] = set()

    for spec in forms:
        for candidate in _candidate_filenames(spec):
            match = files_by_folded_name.get(fold(candidate))
            if match is not None:
                referenced_files.add(match)

    for spec in forms:
        if not spec.has_ingesta:
            yaml_without_ingesta.append(
                FormResolution(
                    spec=spec,
                    file_path=None,
                    resolved_sheet=None,
                    resolved_date_column=None,
                    resolved_person_columns=(),
                    available_kpis=(),
                    missing_columns=(),
                    skip_reason=SKIP_INCOMPLETE_YAML_CONFIG,
                )
            )
            continue

        file_path = _resolve_file(spec, input_files)
        if file_path is None:
            yaml_without_file.append(
                FormResolution(
                    spec=spec,
                    file_path=None,
                    resolved_sheet=None,
                    resolved_date_column=None,
                    resolved_person_columns=(),
                    available_kpis=(),
                    missing_columns=(),
                    skip_reason=SKIP_FILE_NOT_FOUND_IN_INPUTS,
                )
            )
            continue

        try:
            available_columns, resolved_sheet = _read_excel_header(file_path, spec.hoja)
        except Exception as exc:  # noqa: BLE001
            yaml_with_column_issues.append(
                FormResolution(
                    spec=spec,
                    file_path=file_path,
                    resolved_sheet=spec.hoja,
                    resolved_date_column=None,
                    resolved_person_columns=(),
                    available_kpis=(),
                    missing_columns=(),
                    skip_reason=SKIP_HEADER_READ_FAILED,
                    skip_detail=format_user_message(exc, context="read_headers", path=file_path),
                )
            )
            continue

        resolved_date_column = find_first_matching_column(
            list(spec.columna_fecha_aliases), available_columns
        )
        resolved_persons = tuple(
            match
            for match in (find_matching_column(col, available_columns) for col in spec.columnas_persona)
            if match
        )

        available_kpis: list[str] = []
        missing_kpis: list[str] = []
        for kpi in spec.kpis:
            match = find_matching_column(kpi.columna_origen, available_columns)
            if match is None:
                missing_kpis.append(kpi.columna_origen)
            else:
                available_kpis.append(kpi.columna_origen)

        skip_reason: str | None = None
        if resolved_date_column is None:
            skip_reason = SKIP_DATE_COLUMN_MISMATCH
        elif not resolved_persons:
            skip_reason = SKIP_PERSON_COLUMN_MISMATCH
        elif not available_kpis:
            skip_reason = SKIP_KPI_COLUMN_MISMATCH

        resolution = FormResolution(
            spec=spec,
            file_path=file_path,
            resolved_sheet=resolved_sheet,
            resolved_date_column=resolved_date_column,
            resolved_person_columns=resolved_persons,
            available_kpis=tuple(available_kpis),
            missing_columns=tuple(missing_kpis),
            skip_reason=skip_reason,
        )

        if skip_reason is None:
            matched.append(resolution)
        else:
            yaml_with_column_issues.append(resolution)

    files_without_yaml = tuple(p for p in input_files if p not in referenced_files)

    return ReconciliationReport(
        matched=tuple(matched),
        yaml_without_ingesta=tuple(yaml_without_ingesta),
        yaml_without_file=tuple(yaml_without_file),
        yaml_with_column_issues=tuple(yaml_with_column_issues),
        files_without_yaml=files_without_yaml,
    )
