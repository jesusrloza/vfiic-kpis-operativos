from __future__ import annotations

import re
import unicodedata


def fold(text: object) -> str:
    """Devuelve un texto sin acentos, en minúsculas y con espacios colapsados.

    Pensado para comparar nombres de columnas, formularios o archivos donde
    pueden variar mayúsculas, acentos o espacios duplicados.
    """
    if text is None:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(text))
    no_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    collapsed = re.sub(r"\s+", " ", no_accents).strip()
    return collapsed.casefold()


def slugify(text: object) -> str:
    """Convierte un texto a un identificador estable: ASCII, minúsculas, separadores `_`.

    Útil para derivar `area_id` desde el nombre del formulario en el YAML.
    """
    folded = fold(text)
    base = re.sub(r"[^a-z0-9]+", "_", folded)
    return base.strip("_") or "forma"


def find_matching_column(target: str, available: list[str]) -> str | None:
    """Busca un nombre exacto, luego una coincidencia tras `fold` sobre las opciones."""
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
