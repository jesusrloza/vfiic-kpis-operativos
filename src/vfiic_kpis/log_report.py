from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from vfiic_kpis.manifest import FormResolution, ReconciliationReport


def _bullets(lines: Iterable[str]) -> str:
    rendered = "\n".join(f"  - {line}" for line in lines)
    return rendered or "  (sin incidencias en esta categoría)"


def _reconciliation_is_clean(report: ReconciliationReport) -> bool:
    return (
        not report.yaml_without_file
        and not report.yaml_without_ingesta
        and not report.yaml_with_column_issues
        and not report.files_without_yaml
    )


def _format_resolution(resolution: FormResolution) -> str:
    parts: list[str] = [resolution.spec.display_name]
    if resolution.spec.archivo:
        parts.append(f"archivo: {resolution.spec.archivo}")
    if resolution.skip_reason:
        parts.append(f"motivo: {resolution.skip_reason}")
    if resolution.missing_columns:
        parts.append(f"KPIs sin columna: {len(resolution.missing_columns)}")
    return " | ".join(parts)


def format_text_summary(report: ReconciliationReport, *, detail_json_path: Path | None = None) -> str:
    """Construye un resumen legible para imprimir al final de la corrida.

    Si no hay incidencias (archivos faltantes, ingesta, columnas, huérfanos),
    el texto de consola es breve; el JSON en `detail_json_path` conserva el detalle.
    """
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

    matched = [_format_resolution(item) for item in report.matched]
    no_file = [_format_resolution(item) for item in report.yaml_without_file]
    no_ingesta = [_format_resolution(item) for item in report.yaml_without_ingesta]
    column_issues = [_format_resolution(item) for item in report.yaml_with_column_issues]
    extra_files = [path.name for path in report.files_without_yaml]

    sections = [
        "===== Reconciliación schema YAML vs inputs =====",
        f"Formularios procesables: {len(matched)}",
        _bullets(matched),
        "",
        f"Formularios sin archivo en inputs: {len(no_file)}",
        _bullets(no_file),
        "",
        f"Formularios con configuración incompleta en el YAML: {len(no_ingesta)}",
        _bullets(no_ingesta),
        "",
        f"Formularios con problemas de columnas: {len(column_issues)}",
        _bullets(column_issues),
        "",
        f"Archivos en inputs sin entrada en el YAML: {len(extra_files)}",
        _bullets(extra_files),
        "====================================================",
    ]
    if detail_json_path is not None:
        sections.insert(-1, f"Detalle completo en: {detail_json_path}")
    return "\n".join(sections)


def _resolution_to_dict(resolution: FormResolution) -> dict:
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
        "motivo_omision": resolution.skip_reason,
    }


def report_to_dict(report: ReconciliationReport) -> dict:
    return {
        "procesables": [_resolution_to_dict(item) for item in report.matched],
        "sin_archivo": [_resolution_to_dict(item) for item in report.yaml_without_file],
        "config_incompleta": [_resolution_to_dict(item) for item in report.yaml_without_ingesta],
        "problemas_columnas": [_resolution_to_dict(item) for item in report.yaml_with_column_issues],
        "archivos_sin_schema": [str(path) for path in report.files_without_yaml],
        "totales": {
            "procesables": len(report.matched),
            "sin_archivo": len(report.yaml_without_file),
            "config_incompleta": len(report.yaml_without_ingesta),
            "problemas_columnas": len(report.yaml_with_column_issues),
            "archivos_sin_schema": len(report.files_without_yaml),
        },
    }


def write_json_sidecar(report: ReconciliationReport, output_path: Path) -> None:
    """Escribe el resumen como JSON UTF-8 indentado para auditoría posterior."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report_to_dict(report), handle, ensure_ascii=False, indent=2)


def print_and_persist(report: ReconciliationReport, json_path: Path) -> None:
    print(format_text_summary(report, detail_json_path=json_path.resolve()))
    write_json_sidecar(report, json_path)
