from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

DEFAULT_INPUT_DIR = Path("inputs")
DEFAULT_SCHEMA_PATH = Path("schemas/indicadores_vfiic_v6.yaml")

DEFAULT_PARTITIONED_DIR = Path("outputs/particionados")
DEFAULT_COMPARISON_OUTPUT_DIR = Path("outputs/comparativos")
DEFAULT_ERRORS_DIR = Path("outputs/errors")
DEFAULT_RECONCILIATION_LOG = Path("logs/reconciliacion.json")

DEFAULT_COMPARISON_THEME = Path("themes/excel_comparison.toml")
DEFAULT_PARTITIONED_THEME = Path("themes/excel_partitioned.toml")

_CAPTURE_DIR_TIMESTAMP = re.compile(
    r"(?i)Captura\s+de\s+Datos-(\d{8}T\d{6}Z)",
)
_CAPTURE_DIR_TIMESTAMP_FALLBACK = re.compile(r"(\d{8}T\d{6}Z)")


def _parse_capture_timestamp(raw: str) -> datetime:
    return datetime.strptime(raw, "%Y%m%dT%H%M%SZ")


def discover_input_capture_timestamp(input_dir: Path) -> datetime | None:
    """Return the newest capture-folder timestamp found directly under `input_dir`."""
    if not input_dir.is_dir():
        return None

    candidates: list[datetime] = []
    for child in input_dir.iterdir():
        if not child.is_dir():
            continue
        match = _CAPTURE_DIR_TIMESTAMP.search(child.name)
        if match is None:
            match = _CAPTURE_DIR_TIMESTAMP_FALLBACK.search(child.name)
        if match is None:
            continue
        try:
            candidates.append(_parse_capture_timestamp(match.group(1)))
        except ValueError:
            continue

    if not candidates:
        return None
    return max(candidates)


def comparison_output_path(
    *,
    input_dir: Path | None = None,
    now: datetime | None = None,
) -> Path:
    """Return a timestamped comparativo workbook path under `outputs/comparativos/`.

    Prefers the timestamp embedded in a capture folder under `input_dir`
    (for example ``Captura de Datos-20260702T193848Z-3-001``). Falls back
    to ``now`` or the current local time when no such folder exists.
    """
    stamp_dt = discover_input_capture_timestamp(input_dir) if input_dir is not None else None
    if stamp_dt is None:
        stamp_dt = now or datetime.now()
    stamp = stamp_dt.strftime("%Y%m%d_%H%M%S")
    return DEFAULT_COMPARISON_OUTPUT_DIR / f"comparativo_kpis_{stamp}.xlsx"


def errors_report_paths(
    *,
    input_dir: Path | None = None,
    now: datetime | None = None,
    errors_dir: Path | None = None,
) -> tuple[Path, Path, Path, Path]:
    """Return timestamped capture-error report paths under ``outputs/errors/``.

    Returns ``(detailed_md, detailed_json, critical_md, critical_json)``.
    """
    stamp_dt = discover_input_capture_timestamp(input_dir) if input_dir is not None else None
    if stamp_dt is None:
        stamp_dt = now or datetime.now()
    stamp = stamp_dt.strftime("%Y%m%d_%H%M%S")
    root = errors_dir or DEFAULT_ERRORS_DIR
    base = root / f"errores_captura_{stamp}"
    critical_base = root / f"errores_captura_{stamp}_criticos"
    return (
        base.with_suffix(".md"),
        base.with_suffix(".json"),
        critical_base.with_suffix(".md"),
        critical_base.with_suffix(".json"),
    )
