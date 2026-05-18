"""Actualiza bloques `ingesta` en el schema a partir de los Excel en inputs/."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUTS = PROJECT_ROOT / "inputs"
SCHEMA = PROJECT_ROOT / "schemas" / "indicadores_vfiic_v5.yaml"

sys.path.insert(0, str(PROJECT_ROOT / "src"))
from vfiic_kpis.text_match import find_first_matching_column, find_matching_column  # noqa: E402

DEFAULT_DATE_ALIASES = ("Periodo Evaluado", "Periodo a Evaluar", "Submission Date")

PERSON_GROUPS: list[list[str]] = [
    ["Perito - Nombre(s)", "Perito - Apellido Paterno", "Perito - Apellido Materno"],
    ["Agente - Nombre(s)", "Agente - Apellido Paterno", "Agente - Apellido Materno"],
    [
        "Director / Encargado - Nombre(s)",
        "Director / Encargado - Apellido Paterno",
        "Director / Encargado - Apellido Materno",
    ],
    ["Titular - Nombre(s)", "Titular - Apellido Paterno", "Titular - Apellido Materno"],
    ["Auxiliar - Nombre(s)", "Auxiliar - Apellido Paterno", "Auxiliar - Apellido Materno"],
    [
        "Personal Administrativo - Nombre(s)",
        "Personal Administrativo - Apellido Paterno",
        "Personal Administrativo - Apellido Materno",
    ],
]
EMAIL_ALIASES = (
    "Correo electrónico institucional",
    "Email",
    "Dirección de correo electrónico",
    "Correo electrónico",
)


def detect_person_columns(cols: list[str]) -> list[str] | None:
    for names in PERSON_GROUPS:
        resolved = [find_matching_column(n, cols) for n in names]
        if all(resolved):
            return [r for r in resolved if r is not None]
    for alias in EMAIL_ALIASES:
        m = find_matching_column(alias, cols)
        if m:
            return [m]
    return None


def sheet_columns(path: Path) -> tuple[str, list[str]]:
    xl = pd.ExcelFile(path)
    if "Form responses" in xl.sheet_names:
        sheet = "Form responses"
    else:
        sheet = xl.sheet_names[0]
    header = pd.read_excel(path, sheet_name=sheet, nrows=0)
    return sheet, [str(c) for c in header.columns]


def _refresh_ingesta_from_excel(display_name: str, form_raw: dict, path: Path) -> dict:
    sheet, cols = sheet_columns(path)
    persons = detect_person_columns(cols)
    if not persons:
        raise SystemExit(f"Sin columnas de persona detectadas: {display_name!r} en {path.name}")

    kpis_raw = form_raw.get("kpis", [])
    if not isinstance(kpis_raw, list):
        raise SystemExit(f"Formulario sin lista `kpis`: {display_name!r}")

    kpis_out: list[dict] = []
    for item in kpis_raw:
        if not isinstance(item, dict):
            raise SystemExit(f"KPI inválido en {display_name!r}")
        co = str(item.get("columna_origen", "")).strip()
        desc = str(item.get("descripcion", "")).strip() or co
        resolved = find_matching_column(co, cols) or co
        entry: dict = {"columna_origen": resolved, "descripcion": desc}
        for key in ("aggregation", "value_parser"):
            if key in item and item[key] is not None:
                entry[key] = item[key]
        kpis_out.append(entry)

    if find_first_matching_column(["Periodo Evaluado", "Periodo a Evaluar"], cols) is None:
        date_aliases = list(DEFAULT_DATE_ALIASES)
    else:
        date_aliases = ["Periodo Evaluado", "Periodo a Evaluar"]

    return {
        "ingesta": {
            "archivo": path.name,
            "hoja": sheet,
            "columna_fecha": date_aliases,
            "columnas_persona": persons,
        },
        "kpis": kpis_out,
    }


def main() -> None:
    with SCHEMA.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise SystemExit("YAML raíz debe ser dict")

    out: dict = {}
    for direccion, forms in data.items():
        if not isinstance(forms, dict):
            out[direccion] = forms
            continue
        new_forms: dict = {}
        for display_name, form_raw in forms.items():
            path = INPUTS / f"{display_name}.xlsx"
            if path.is_file() and isinstance(form_raw, dict) and "kpis" in form_raw:
                new_forms[display_name] = _refresh_ingesta_from_excel(display_name, form_raw, path)
            else:
                new_forms[display_name] = form_raw
        out[direccion] = new_forms

    with SCHEMA.open("w", encoding="utf-8") as f:
        yaml.dump(
            out,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=120,
        )
    print(f"Escrito {SCHEMA}")


if __name__ == "__main__":
    main()
