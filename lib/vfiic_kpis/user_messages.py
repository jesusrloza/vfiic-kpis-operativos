"""Spanish strings and formatters for all operator-facing output."""

from __future__ import annotations

import errno
from pathlib import Path
from typing import Iterable

import yaml

# Internal skip-reason codes (English) used in manifest.FormResolution.skip_reason
SKIP_INCOMPLETE_YAML_CONFIG = "incomplete_yaml_config"
SKIP_FILE_NOT_FOUND_IN_INPUTS = "file_not_found_in_inputs"
SKIP_DATE_COLUMN_MISMATCH = "date_column_mismatch"
SKIP_PERSON_COLUMN_MISMATCH = "person_column_mismatch"
SKIP_KPI_COLUMN_MISMATCH = "kpi_column_mismatch"
SKIP_HEADER_READ_FAILED = "header_read_failed"
SKIP_AMBIGUOUS_INPUT_FILE = "ambiguous_input_file"
SKIP_DUPLICATE_INPUT_FILE = "duplicate_input_file"

SKIP_REASON_MESSAGES: dict[str, str] = {
    SKIP_INCOMPLETE_YAML_CONFIG: "configuración incompleta en el YAML",
    SKIP_FILE_NOT_FOUND_IN_INPUTS: "archivo no encontrado en inputs",
    SKIP_AMBIGUOUS_INPUT_FILE: "varios archivos en inputs coinciden con el mismo formulario",
    SKIP_DUPLICATE_INPUT_FILE: "varios archivos con el mismo nombre en distintas carpetas de inputs",
    SKIP_DATE_COLUMN_MISMATCH: "ninguna columna de fecha del YAML coincidió con el archivo",
    SKIP_PERSON_COLUMN_MISMATCH: "ninguna columna de persona del YAML coincidió con el archivo",
    SKIP_KPI_COLUMN_MISMATCH: "ningún KPI del YAML coincidió con columnas del archivo",
}

TAG_DATA = "datos"
TAG_PARTITIONED = "particionado"
TAG_COMPARATIVO = "comparativo"
TAG_RUN_ALL = "todos"

YAML_GUIDE_REF = "docs/guia-indicadores-yaml.md"

MSG_NO_PARSEABLE_PERIODS = "sin periodos parseables"
MSG_NO_CALCULABLE_ROWS = "sin filas calculables"


def _file_label(path: Path | None) -> str:
    if path is None:
        return "el archivo"
    return f'"{path.name}"'


def format_skip_reason(
    code: str | None,
    *,
    detail: str | None = None,
    file_path: Path | None = None,
) -> str | None:
    """Map an internal skip code to a short Spanish message for the operator."""
    del file_path  # reserved for future context-specific wording
    if code is None:
        return None
    if code == SKIP_HEADER_READ_FAILED and detail:
        return detail
    if code in (SKIP_AMBIGUOUS_INPUT_FILE, SKIP_DUPLICATE_INPUT_FILE) and detail:
        base = SKIP_REASON_MESSAGES[code]
        return f"{base}: {detail}"
    return SKIP_REASON_MESSAGES.get(code, code)


def format_user_message(
    exc: BaseException,
    *,
    context: str,
    path: Path | None = None,
) -> str:
    """Translate a common exception to a brief Spanish message."""
    del context
    if isinstance(exc, PermissionError):
        name = _file_label(path)
        if path is not None and "outputs" in path.parts:
            return (
                f"No se pudo escribir en {name}. "
                "Si el reporte está abierto en Excel, ciérrelo e intente de nuevo."
            )
        return (
            f"No se pudo leer {name}. "
            "Si está abierto en Excel u otra aplicación, ciérrelo e intente de nuevo."
        )

    if isinstance(exc, FileNotFoundError):
        if path is not None:
            return f"No se encontró el archivo: {path}"
        return str(exc) or "No se encontró un archivo necesario."

    if isinstance(exc, yaml.YAMLError):
        return f"El schema YAML no es válido: {exc}. Revise {YAML_GUIDE_REF}."

    if isinstance(exc, ValueError):
        text = str(exc).strip()
        if any(token in text.lower() for token in ("ingesta", "kpi", "yaml")):
            return f"{text} Revise {YAML_GUIDE_REF}."
        return text or "Valor inválido en los datos o la configuración."

    if isinstance(exc, OSError) and getattr(exc, "errno", None) in (
        errno.EACCES,
        errno.EPERM,
        13,
    ):
        name = _file_label(path)
        return (
            f"Acceso denegado a {name}. "
            "Cierre el archivo si está abierto e intente de nuevo."
        )

    text = str(exc).strip()
    if text:
        return text
    return f"Error inesperado ({type(exc).__name__})."


def print_user_error(context: str, exc: BaseException, *, path: Path | None = None) -> None:
    reason = format_user_message(exc, context=context, path=path)
    print(f"[ERROR] No se pudo completar: {context}.")
    print(f"Motivo: {reason}")


def print_status(tag: str, message: str) -> None:
    print(f"[{tag}] {message}")


def print_skipped_form(tag: str, display_name: str, reason: str) -> None:
    print_status(tag, f"omitido {display_name!r}: {reason}")


def print_future_rows_dropped(display_name: str, archivo: str, count: int) -> None:
    print_status(
        TAG_DATA,
        f"omitidas {count} fila(s) con periodo futuro: {display_name} (archivo: {archivo})",
    )


def print_partitioned_written(display_name: str, out_path: Path) -> None:
    print_status(TAG_PARTITIONED, f"{display_name} -> {out_path}")


def print_partitioned_count(count: int, output_dir: Path) -> None:
    print_status(TAG_PARTITIONED, f"{count} workbook(s) en {output_dir}")


def print_partitioned_none() -> None:
    print_status(TAG_PARTITIONED, "ningún workbook generado")


def print_comparativo_blocks(count: int, output_path: Path) -> None:
    print_status(TAG_COMPARATIVO, f"{count} bloque(s) -> {output_path}")


def print_comparativo_workbook(output_path: Path) -> None:
    print_status(TAG_COMPARATIVO, f"workbook: {output_path}")


def print_comparativo_insufficient_data() -> None:
    print_status(TAG_COMPARATIVO, "no hay formularios con datos suficientes; no se generó workbook")


def _bullets(lines: Iterable[str]) -> str:
    rendered = "\n".join(f"  - {line}" for line in lines)
    return rendered or "  (sin incidencias en esta categoría)"


def _format_resolution_line(resolution) -> str:
    parts: list[str] = [resolution.spec.display_name]
    if resolution.spec.archivo:
        parts.append(f"archivo: {resolution.spec.archivo}")
    reason = format_skip_reason(
        resolution.skip_reason,
        detail=resolution.skip_detail,
        file_path=resolution.file_path,
    )
    if reason:
        parts.append(f"motivo: {reason}")
    if resolution.missing_columns:
        parts.append(f"KPIs sin columna: {len(resolution.missing_columns)}")
    return " | ".join(parts)


def _relative_input_path(path: Path, input_dir: Path | None) -> str:
    if input_dir is None:
        return path.name
    try:
        return path.relative_to(input_dir).as_posix()
    except ValueError:
        return path.name


def _format_duplicate_group_line(basename: str, paths: tuple[Path, ...], input_dir: Path | None) -> str:
    rel_paths = sorted(_relative_input_path(path, input_dir) for path in paths)
    return f"{basename} -> {', '.join(rel_paths)}"


def _reconciliation_is_clean(report) -> bool:
    return (
        not report.yaml_without_file
        and not report.yaml_without_ingesta
        and not report.yaml_with_column_issues
        and not report.files_without_yaml
        and not report.duplicate_input_files
    )


def format_reconciliation_summary(report, *, detail_json_path: Path | None = None) -> str:
    """Build a human-readable reconciliation summary in Spanish."""
    if _reconciliation_is_clean(report):
        n = len(report.matched)
        lines = [
            "===== Reconciliación schema YAML vs inputs =====",
            f"{n} formulario(s) procesable(s); sin incidencias.",
            "====================================================",
        ]
        if detail_json_path is not None:
            lines.insert(-1, f"Detalle completo en: {detail_json_path}")
        return "\n".join(lines)

    matched = [_format_resolution_line(item) for item in report.matched]
    no_file = [_format_resolution_line(item) for item in report.yaml_without_file]
    no_config = [_format_resolution_line(item) for item in report.yaml_without_ingesta]
    column_issues = [_format_resolution_line(item) for item in report.yaml_with_column_issues]
    input_dir = report.input_dir
    duplicate_files = [
        _format_duplicate_group_line(basename, paths, input_dir)
        for basename, paths in report.duplicate_input_files
    ]
    extra_files = [
        _relative_input_path(path, input_dir) for path in report.files_without_yaml
    ]

    sections = [
        "===== Reconciliación schema YAML vs inputs =====",
        f"Formularios procesables: {len(matched)}",
        _bullets(matched),
        "",
        f"Formularios sin archivo en inputs: {len(no_file)}",
        _bullets(no_file),
        "",
        f"Formularios con configuración incompleta en el YAML: {len(no_config)}",
        _bullets(no_config),
        "",
        f"Formularios con problemas de columnas: {len(column_issues)}",
        _bullets(column_issues),
        "",
        f"Archivos con nombre duplicado en inputs: {len(duplicate_files)}",
        _bullets(duplicate_files),
        "",
        f"Archivos en inputs sin entrada en el YAML: {len(extra_files)}",
        _bullets(extra_files),
        "====================================================",
    ]
    if detail_json_path is not None:
        sections.insert(-1, f"Detalle completo en: {detail_json_path}")
    return "\n".join(sections)


def resolution_to_user_dict(resolution) -> dict:
    reason = format_skip_reason(
        resolution.skip_reason,
        detail=resolution.skip_detail,
        file_path=resolution.file_path,
    )
    return {
        "area_id": resolution.spec.area_id,
        "display_name": resolution.spec.display_name,
        "direccion": resolution.spec.direccion,
        "archivo_yaml": resolution.spec.archivo,
        "archivo_resuelto": str(resolution.file_path) if resolution.file_path else None,
        "hoja_resuelta": resolution.resolved_sheet,
        "columna_fecha_resuelta": resolution.resolved_date_column,
        "columnas_persona_resueltas": list(resolution.resolved_person_columns),
        "kpis_disponibles": list(resolution.available_kpis),
        "kpis_sin_columna": list(resolution.missing_columns),
        "motivo_omision": reason,
    }


def reconciliation_report_to_user_dict(report) -> dict:
    input_dir = report.input_dir
    return {
        "procesables": [resolution_to_user_dict(item) for item in report.matched],
        "sin_archivo": [resolution_to_user_dict(item) for item in report.yaml_without_file],
        "config_incompleta": [resolution_to_user_dict(item) for item in report.yaml_without_ingesta],
        "problemas_columnas": [resolution_to_user_dict(item) for item in report.yaml_with_column_issues],
        "archivos_duplicados": [
            {
                "nombre": basename,
                "rutas": [
                    _relative_input_path(path, input_dir) for path in paths
                ],
            }
            for basename, paths in report.duplicate_input_files
        ],
        "archivos_sin_schema": [
            _relative_input_path(path, input_dir) for path in report.files_without_yaml
        ],
        "totales": {
            "procesables": len(report.matched),
            "sin_archivo": len(report.yaml_without_file),
            "config_incompleta": len(report.yaml_without_ingesta),
            "problemas_columnas": len(report.yaml_with_column_issues),
            "archivos_duplicados": len(report.duplicate_input_files),
            "archivos_sin_schema": len(report.files_without_yaml),
        },
    }
