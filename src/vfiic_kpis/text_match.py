from __future__ import annotations

import re
import unicodedata
from pathlib import Path

INPUT_FILE_PREFIXES: tuple[str, ...] = ("AREA - ", "PERSONA - ")


def fold(text: object) -> str:
    """Normalize text for comparison: no accents, lowercase, collapsed spaces."""
    if text is None:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(text))
    no_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    collapsed = re.sub(r"\s+", " ", no_accents).strip()
    return collapsed.casefold()


def slugify(text: object) -> str:
    """Convert text to a stable ASCII identifier with `_` separators."""
    folded = fold(text)
    base = re.sub(r"[^a-z0-9]+", "_", folded)
    return base.strip("_") or "forma"


def find_matching_column(target: str, available: list[str]) -> str | None:
    """Find an exact match, then a folded match among available column names."""
    if target in available:
        return target
    target_folded = fold(target)
    for candidate in available:
        if fold(candidate) == target_folded:
            return candidate
    return None


def find_first_matching_column(targets: list[str], available: list[str]) -> str | None:
    """Devuelve el primer alias que resuelva contra las columnas disponibles."""
    for target in targets:
        match = find_matching_column(target, available)
        if match is not None:
            return match
    return None


def canonical_input_basename(filename: str) -> str:
    """Strip a known AREA/PERSONA prefix; otherwise return the filename unchanged."""
    for prefix in INPUT_FILE_PREFIXES:
        if filename.startswith(prefix):
            return filename[len(prefix) :]
    return filename


def build_input_file_index(input_files: list[Path]) -> dict[str, list[Path]]:
    """Map folded canonical basenames to all input paths that resolve to them."""
    index: dict[str, list[Path]] = {}
    for path in input_files:
        key = fold(canonical_input_basename(path.name))
        index.setdefault(key, []).append(path)
    return index
