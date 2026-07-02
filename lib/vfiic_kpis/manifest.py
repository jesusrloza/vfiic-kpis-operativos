from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from vfiic_kpis.text_match import (
    build_input_file_index,
    discover_date_column,
    discover_person_columns,
    find_matching_column,
    fold,
)
from vfiic_kpis.user_messages import (
    SKIP_AMBIGUOUS_INPUT_FILE,
    SKIP_DATE_COLUMN_MISMATCH,
    SKIP_DUPLICATE_INPUT_FILE,
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
        if not self.available_kpis or self.file_path is None or self.resolved_date_column is None:
            return False
        if self.skip_reason is None:
            return True
        return self.skip_reason == SKIP_PERSON_COLUMN_MISMATCH


@dataclass(frozen=True)
class InputDiscovery:
    """Spreadsheet files found under ``input_dir`` and indexes for reconciliation."""

    usable_files: tuple[Path, ...]
    duplicate_groups: tuple[tuple[str, tuple[Path, ...]], ...]
    files_by_folded_name: dict[str, list[Path]]
    canonical_index: dict[str, list[Path]]
    duplicate_basenames: frozenset[str]


@dataclass(frozen=True)
class ReconciliationReport:
    matched: tuple[FormResolution, ...] = field(default_factory=tuple)
    yaml_without_file: tuple[FormResolution, ...] = field(default_factory=tuple)
    yaml_without_ingesta: tuple[FormResolution, ...] = field(default_factory=tuple)
    yaml_with_column_issues: tuple[FormResolution, ...] = field(default_factory=tuple)
    files_without_yaml: tuple[Path, ...] = field(default_factory=tuple)
    duplicate_input_files: tuple[tuple[str, tuple[Path, ...]], ...] = field(default_factory=tuple)
    input_dir: Path | None = None


def relative_input_path(path: Path, input_dir: Path) -> str:
    """Return ``path`` relative to ``input_dir`` for operator-facing messages."""
    try:
        return path.relative_to(input_dir).as_posix()
    except ValueError:
        return path.name


def discover_input_spreadsheets(input_dir: Path) -> InputDiscovery:
    """Recursively find ``.xlsx`` files under ``input_dir`` and detect duplicate basenames."""
    all_files = sorted(
        p
        for p in input_dir.rglob("*.xlsx")
        if p.is_file() and not p.name.startswith("~$")
    )
    by_basename: dict[str, list[Path]] = {}
    for path in all_files:
        by_basename.setdefault(path.name, []).append(path)

    duplicate_groups = tuple(
        (name, tuple(sorted(paths, key=str)))
        for name, paths in sorted(by_basename.items())
        if len(paths) > 1
    )
    duplicate_basenames = frozenset(name for name, _ in duplicate_groups)
    duplicate_paths = {path for _, paths in duplicate_groups for path in paths}
    usable_files = tuple(path for path in all_files if path not in duplicate_paths)

    files_by_folded_name: dict[str, list[Path]] = {}
    for path in usable_files:
        files_by_folded_name.setdefault(fold(path.name), []).append(path)

    canonical_index = build_input_file_index(list(usable_files))

    return InputDiscovery(
        usable_files=usable_files,
        duplicate_groups=duplicate_groups,
        files_by_folded_name=files_by_folded_name,
        canonical_index=canonical_index,
        duplicate_basenames=duplicate_basenames,
    )


def _duplicate_detail(
    basename: str,
    paths: tuple[Path, ...],
    *,
    input_dir: Path,
) -> str:
    rel_paths = sorted(relative_input_path(path, input_dir) for path in paths)
    return f"{basename}: {', '.join(rel_paths)}"


def _read_excel_header(path: Path, sheet: str | int | None) -> tuple[list[str], str | int]:
    """Read only the header row from an xlsx file and return the resolved sheet."""
    sheet_arg: str | int = sheet if sheet is not None else 0
    header = pd.read_excel(path, sheet_name=sheet_arg, nrows=0)
    columns = [str(col) for col in header.columns]
    return columns, sheet_arg


def _resolve_file(
    spec: FormSpec,
    *,
    files_by_folded_name: dict[str, list[Path]],
    canonical_index: dict[str, list[Path]],
    duplicate_basenames: frozenset[str],
    duplicate_groups: tuple[tuple[str, tuple[Path, ...]], ...],
    input_dir: Path,
) -> tuple[Path | None, str | None, str | None]:
    """Locate the form file: exact name, then canonical basename (prefixed inputs).

    Returns ``(path, skip_reason, skip_detail)``. On success, skip fields are ``None``.
    """
    if not spec.archivo:
        return None, None, None

    if spec.archivo in duplicate_basenames:
        for basename, paths in duplicate_groups:
            if basename == spec.archivo:
                return (
                    None,
                    SKIP_DUPLICATE_INPUT_FILE,
                    _duplicate_detail(basename, paths, input_dir=input_dir),
                )

    target_folded = fold(spec.archivo)
    candidates: list[Path] = []
    seen: set[str] = set()

    def _add(path: Path) -> None:
        key = str(path)
        if key not in seen:
            seen.add(key)
            candidates.append(path)

    for path in files_by_folded_name.get(target_folded, []):
        _add(path)
    for path in canonical_index.get(target_folded, []):
        _add(path)

    if len(candidates) == 1:
        return candidates[0], None, None
    if len(candidates) > 1:
        names = ", ".join(
            sorted(relative_input_path(path, input_dir) for path in candidates)
        )
        return None, SKIP_AMBIGUOUS_INPUT_FILE, names

    return None, None, None


def reconcile(
    forms: list[FormSpec],
    input_dir: Path,
) -> ReconciliationReport:
    """Match `FormSpec` entries against xlsx files in `input_dir` (recursive)."""
    discovery = discover_input_spreadsheets(input_dir)
    input_files = list(discovery.usable_files)
    files_by_folded_name = discovery.files_by_folded_name
    canonical_index = discovery.canonical_index

    matched: list[FormResolution] = []
    yaml_without_ingesta: list[FormResolution] = []
    yaml_without_file: list[FormResolution] = []
    yaml_with_column_issues: list[FormResolution] = []
    referenced_files: set[Path] = set()

    resolve_kwargs = {
        "files_by_folded_name": files_by_folded_name,
        "canonical_index": canonical_index,
        "duplicate_basenames": discovery.duplicate_basenames,
        "duplicate_groups": discovery.duplicate_groups,
        "input_dir": input_dir,
    }

    for spec in forms:
        if not spec.has_ingesta:
            continue
        file_path, _, _ = _resolve_file(spec, **resolve_kwargs)
        if file_path is not None:
            referenced_files.add(file_path)

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

        file_path, file_skip_reason, file_skip_detail = _resolve_file(spec, **resolve_kwargs)
        if file_path is None:
            if file_skip_reason in (SKIP_AMBIGUOUS_INPUT_FILE, SKIP_DUPLICATE_INPUT_FILE):
                yaml_with_column_issues.append(
                    FormResolution(
                        spec=spec,
                        file_path=None,
                        resolved_sheet=None,
                        resolved_date_column=None,
                        resolved_person_columns=(),
                        available_kpis=(),
                        missing_columns=(),
                        skip_reason=file_skip_reason,
                        skip_detail=file_skip_detail,
                    )
                )
            else:
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

        resolved_date_column = discover_date_column(
            list(spec.columna_fecha_aliases), available_columns
        )
        if spec.columnas_persona:
            resolved_persons = tuple(
                match
                for match in (
                    find_matching_column(col, available_columns) for col in spec.columnas_persona
                )
                if match
            )
        else:
            resolved_persons = discover_person_columns(available_columns)

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
        elif not available_kpis:
            skip_reason = SKIP_KPI_COLUMN_MISMATCH
        elif not resolved_persons:
            skip_reason = SKIP_PERSON_COLUMN_MISMATCH

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

        if skip_reason is None or skip_reason == SKIP_PERSON_COLUMN_MISMATCH:
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
        duplicate_input_files=discovery.duplicate_groups,
        input_dir=input_dir,
    )
