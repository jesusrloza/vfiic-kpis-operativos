from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from vfiic_kpis.text_match import (
    find_first_matching_column,
    find_matching_column,
    fold,
)
from vfiic_kpis.errores_usuario import mensaje_para_usuario
from vfiic_kpis.yaml_loader import FormSpec


@dataclass(frozen=True)
class FormResolution:
    """Resultado de cruzar un `FormSpec` con los archivos en `inputs/`.

    Se considera "matched" cuando se localizó archivo, hoja, columna de fecha
    y al menos una columna de KPI utilizable. KPIs faltantes se reportan en
    `missing_columns` para que el usuario actualice el schema.
    """

    spec: FormSpec
    file_path: Path | None
    resolved_sheet: str | int | None
    resolved_date_column: str | None
    resolved_person_columns: tuple[str, ...]
    available_kpis: tuple[str, ...]
    missing_columns: tuple[str, ...]
    skip_reason: str | None

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
    """Lee únicamente la fila de encabezados de un xlsx y devuelve la hoja resuelta."""
    sheet_arg: str | int = sheet if sheet is not None else 0
    header = pd.read_excel(path, sheet_name=sheet_arg, nrows=0)
    columns = [str(col) for col in header.columns]
    return columns, sheet_arg


def _candidate_filenames(spec: FormSpec) -> list[str]:
    """Devuelve los nombres de archivo plausibles para un `FormSpec`.

    Cubre el caso en que el YAML aún no define `archivo` pero el nombre del
    archivo en disco coincide con el `display_name` del formulario.
    """
    candidates: list[str] = []
    if spec.archivo:
        candidates.append(spec.archivo)
    candidates.append(f"{spec.display_name}.xlsx")
    return candidates


def _resolve_file(spec: FormSpec, raw_files: list[Path]) -> Path | None:
    """Localiza el archivo del formulario por nombre exacto o equivalencia plegada."""
    if not spec.archivo:
        return None
    candidates_by_name = {fold(p.name): p for p in raw_files}
    target = fold(spec.archivo)
    return candidates_by_name.get(target)


def reconcile(
    forms: list[FormSpec],
    input_dir: Path,
) -> ReconciliationReport:
    """Cruza la lista de `FormSpec` con los archivos disponibles en `input_dir`.

    Reporta cada formulario en una de cuatro categorías:
      - matched: hay archivo y al menos un KPI lee columnas válidas.
      - yaml_without_ingesta: configuración incompleta en el YAML (`ingesta`).
      - yaml_without_file: hay `ingesta`, pero no encontramos el archivo.
      - yaml_with_column_issues: el archivo existe pero no tiene la fecha o
        ningún KPI mapea a sus columnas.
    Además lista `files_without_yaml` para visibilidad operativa.
    """
    raw_files: list[Path] = sorted(p for p in input_dir.glob("*.xlsx") if p.is_file())
    files_by_folded_name = {fold(p.name): p for p in raw_files}

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
                    skip_reason="configuración incompleta en el YAML",
                )
            )
            continue

        file_path = _resolve_file(spec, raw_files)
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
                    skip_reason="archivo no encontrado en inputs",
                )
            )
            continue

        try:
            available_columns, resolved_sheet = _read_excel_header(file_path, spec.hoja)
        except Exception as exc:  # noqa: BLE001
            motivo = mensaje_para_usuario(exc, contexto="leer encabezados", ruta=file_path)
            yaml_with_column_issues.append(
                FormResolution(
                    spec=spec,
                    file_path=file_path,
                    resolved_sheet=spec.hoja,
                    resolved_date_column=None,
                    resolved_person_columns=(),
                    available_kpis=(),
                    missing_columns=(),
                    skip_reason=motivo,
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
            skip_reason = "ninguna columna de fecha del YAML coincidió con el archivo"
        elif not resolved_persons:
            skip_reason = "ninguna columna de persona del YAML coincidió con el archivo"
        elif not available_kpis:
            skip_reason = "ningún KPI del YAML coincidió con columnas del archivo"

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

    files_without_yaml = tuple(p for p in raw_files if p not in referenced_files)

    return ReconciliationReport(
        matched=tuple(matched),
        yaml_without_ingesta=tuple(yaml_without_ingesta),
        yaml_without_file=tuple(yaml_without_file),
        yaml_with_column_issues=tuple(yaml_with_column_issues),
        files_without_yaml=files_without_yaml,
    )
