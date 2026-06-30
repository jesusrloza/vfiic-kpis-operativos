from __future__ import annotations

import re
import unicodedata
from pathlib import Path

INPUT_FILE_PREFIXES: tuple[str, ...] = ("AREA - ", "PERSONA - ")

SPANISH_CONNECTORS: frozenset[str] = frozenset(
    {
        "a",
        "al",
        "con",
        "de",
        "del",
        "e",
        "en",
        "la",
        "las",
        "lo",
        "los",
        "o",
        "por",
        "sin",
        "u",
        "un",
        "una",
        "uno",
        "y",
    }
)

PERSON_ROLE_PREFIXES: tuple[str, ...] = (
    "Agente",
    "Auxiliar",
    "Perito",
    "Director / Encargado",
    "Personal Administrativo",
    "Titular",
)

PERSON_NAME_SUFFIXES: tuple[str, ...] = (
    "Nombre(s)",
    "Apellido Paterno",
    "Apellido Materno",
)


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


def _capitalize_word(word: str) -> str:
    if not word:
        return word
    return word[0].upper() + word[1:].lower()


def title_case_spanish(text: str) -> str:
    """Sentence-style label: first word capitalized, connectors lowercase, rest lowercase."""
    words = text.split()
    if not words:
        return text
    formatted: list[str] = []
    for index, word in enumerate(words):
        leading = ""
        trailing = ""
        core = word
        while core and not core[0].isalnum():
            leading += core[0]
            core = core[1:]
        while core and not core[-1].isalnum():
            trailing = core[-1] + trailing
            core = core[:-1]
        if not core:
            formatted.append(word)
            continue
        folded_core = fold(core)
        if index == 0:
            formatted.append(f"{leading}{_capitalize_word(core)}{trailing}")
        elif folded_core in SPANISH_CONNECTORS:
            formatted.append(f"{leading}{core.lower()}{trailing}")
        else:
            formatted.append(f"{leading}{core.lower()}{trailing}")
    return " ".join(formatted)


def report_label_from_column(columna_origen: str, descripcion: str | None) -> str:
    if descripcion:
        return descripcion
    return title_case_spanish(columna_origen)


def discover_date_column(aliases: list[str], available: list[str]) -> str | None:
    """Resolve a period column from declared aliases, then by ``periodo`` in the header."""
    match = find_first_matching_column(aliases, available)
    if match is not None:
        return match
    for candidate in available:
        if "periodo" in fold(candidate):
            return candidate
    return None


def discover_person_columns(available: list[str]) -> tuple[str, ...]:
    """Find the first complete name triplet (nombre + apellidos) for a known role prefix."""
    for role in PERSON_ROLE_PREFIXES:
        resolved: list[str] = []
        for suffix in PERSON_NAME_SUFFIXES:
            match = find_matching_column(f"{role} - {suffix}", available)
            if match is None:
                resolved = []
                break
            resolved.append(match)
        if len(resolved) == 3:
            return tuple(resolved)
    return ()


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
