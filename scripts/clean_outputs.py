#!/usr/bin/env python3
"""Elimina los artefactos generados en outputs/particionados y outputs/comparativos."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Mismas rutas por defecto que vfiic_kpis.paths
PARTITIONED_DIR = PROJECT_ROOT / "outputs" / "particionados"
COMPARATIVOS_DIR = PROJECT_ROOT / "outputs" / "comparativos"


def _remove_path(path: Path) -> None:
    if path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _clear_directory(root: Path, *, dry_run: bool) -> list[Path]:
    if not root.is_dir():
        return []
    removed: list[Path] = []
    for item in sorted(root.iterdir(), key=lambda p: str(p).lower()):
        if item.name == ".gitkeep":
            continue
        removed.append(item)
        if not dry_run:
            _remove_path(item)
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Vacía outputs/particionados y outputs/comparativos (Excel generados)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo lista lo que se borraría, sin eliminar.",
    )
    args = parser.parse_args()

    targets = [
        ("particionados", PARTITIONED_DIR),
        ("comparativos", COMPARATIVOS_DIR),
    ]
    total = 0
    for label, directory in targets:
        items = _clear_directory(directory, dry_run=args.dry_run)
        total += len(items)
        prefix = "[dry-run] " if args.dry_run else ""
        if not items:
            print(f"{prefix}{label}: (ya vacío o carpeta inexistente) {directory}")
            continue
        print(f"{prefix}{label}: {len(items)} elemento(s) en {directory}")
        for p in items:
            print(f"  - {p.relative_to(PROJECT_ROOT)}")
    if args.dry_run:
        print(f"[dry-run] Total: {total} elemento(s); ejecutar sin --dry-run para borrar.")
    else:
        print(f"Listo. Eliminados {total} elemento(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
