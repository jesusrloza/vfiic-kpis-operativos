from __future__ import annotations

import errno
from pathlib import Path

import yaml


def _nombre_archivo(ruta: Path | None) -> str:
    if ruta is None:
        return "el archivo"
    return f'"{ruta.name}"'


def mensaje_para_usuario(
    exc: BaseException,
    *,
    contexto: str,
    ruta: Path | None = None,
) -> str:
    """Traduce excepciones frecuentes a un mensaje breve en español."""
    if isinstance(exc, PermissionError):
        nombre = _nombre_archivo(ruta)
        if ruta is not None and "outputs" in ruta.parts:
            return (
                f"No se pudo escribir en {nombre}. "
                "Si el reporte está abierto en Excel, ciérrelo e intente de nuevo."
            )
        return (
            f"No se pudo leer {nombre}. "
            "Si está abierto en Excel u otra aplicación, ciérrelo e intente de nuevo."
        )

    if isinstance(exc, FileNotFoundError):
        if ruta is not None:
            return f"No se encontró el archivo: {ruta}"
        return str(exc) or "No se encontró un archivo necesario."

    if isinstance(exc, yaml.YAMLError):
        return (
            f"El schema YAML no es válido: {exc}. "
            "Revise docs/guia-indicadores-yaml.md."
        )

    if isinstance(exc, ValueError):
        texto = str(exc).strip()
        if "ingesta" in texto.lower() or "kpi" in texto.lower() or "yaml" in texto.lower():
            return f"{texto} Revise docs/guia-indicadores-yaml.md."
        return texto or "Valor inválido en los datos o la configuración."

    if isinstance(exc, OSError) and getattr(exc, "errno", None) in (
        errno.EACCES,
        errno.EPERM,
        13,
    ):
        nombre = _nombre_archivo(ruta)
        return (
            f"Acceso denegado a {nombre}. "
            "Cierre el archivo si está abierto e intente de nuevo."
        )

    texto = str(exc).strip()
    if texto:
        return texto
    return f"Error inesperado ({type(exc).__name__})."


def imprimir_error(contexto: str, exc: BaseException, *, ruta: Path | None = None) -> None:
    """Imprime un bloque [ERROR] estándar en consola."""
    motivo = mensaje_para_usuario(exc, contexto=contexto, ruta=ruta)
    print(f"[ERROR] No se pudo completar: {contexto}.")
    print(f"Motivo: {motivo}")
