from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIB = PROJECT_ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from vfiic_kpis.text_match import (
    discover_date_column,
    discover_person_columns,
    report_label_from_column,
    title_case_spanish,
)
from vfiic_kpis.yaml_loader import load_forms_from_yaml


def _write_yaml(body: str) -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
    handle.write(body)
    handle.close()
    return Path(handle.name)


class TestTextMatch(unittest.TestCase):
    def test_title_case_spanish_lowercases_non_first_words(self) -> None:
        self.assertEqual(title_case_spanish("Presentaciones Realizadas"), "Presentaciones realizadas")

    def test_title_case_spanish_keeps_connectors_lowercase(self) -> None:
        self.assertEqual(
            title_case_spanish("Gestión de Recursos Financieros"),
            "Gestión de recursos financieros",
        )

    def test_report_label_uses_explicit_descripcion(self) -> None:
        self.assertEqual(
            report_label_from_column("Personas Puestas a Disposición", "Personas detenidas"),
            "Personas detenidas",
        )

    def test_report_label_applies_title_case_when_missing(self) -> None:
        self.assertEqual(
            report_label_from_column("Solicitudes de Información Atendidas", None),
            "Solicitudes de información atendidas",
        )

    def test_discover_date_column_from_aliases(self) -> None:
        columns = ["Periodo a Evaluar", "Visitas"]
        self.assertEqual(
            discover_date_column(["Periodo Evaluado", "Periodo a Evaluar"], columns),
            "Periodo a Evaluar",
        )

    def test_discover_date_column_falls_back_to_periodo(self) -> None:
        columns = ["Periodo reportado", "Visitas"]
        self.assertEqual(
            discover_date_column(["Periodo Evaluado"], columns),
            "Periodo reportado",
        )

    def test_discover_person_columns_finds_agent_triplet(self) -> None:
        columns = [
            "Agente - Nombre(s)",
            "Agente - Apellido Paterno",
            "Agente - Apellido Materno",
            "Visitas",
        ]
        self.assertEqual(
            discover_person_columns(columns),
            (
                "Agente - Nombre(s)",
                "Agente - Apellido Paterno",
                "Agente - Apellido Materno",
            ),
        )


class TestYamlLoader(unittest.TestCase):
    def test_form_with_full_ingesta(self) -> None:
        body = """
Coordinacion Periciales:

  VFIIC KPIs Periciales - Trabajo Social:
    ingesta:
      archivo: "VFIIC KPIs Periciales - Trabajo Social.xlsx"
      hoja: "Form responses"
      columna_fecha: ["Periodo Evaluado", "Periodo a Evaluar"]
      columnas_persona:
        - "Perito - Nombre(s)"
        - "Perito - Apellido Paterno"
    kpis:
      - columna_origen: "Dictámenes Realizados"
        descripcion: "Dictámenes realizados"
"""
        path = _write_yaml(body)
        try:
            forms = load_forms_from_yaml(path)
            self.assertEqual(len(forms), 1)
            spec = forms[0]
            self.assertEqual(spec.display_name, "VFIIC KPIs Periciales - Trabajo Social")
            self.assertEqual(spec.archivo, "VFIIC KPIs Periciales - Trabajo Social.xlsx")
            self.assertEqual(spec.columna_fecha_aliases, ("Periodo Evaluado", "Periodo a Evaluar"))
            self.assertEqual(len(spec.columnas_persona), 2)
            self.assertTrue(spec.has_ingesta)
            self.assertEqual(spec.kpis[0].columna_origen, "Dictámenes Realizados")
            self.assertEqual(spec.kpis[0].descripcion, "Dictámenes realizados")
            self.assertEqual(spec.kpis[0].aggregation, "sum")
            self.assertEqual(spec.kpis[0].value_parser, "numeric")
        finally:
            path.unlink(missing_ok=True)

    def test_v6_list_form_infers_archivo_and_sheet(self) -> None:
        body = """
Direccion X:

  VFIIC KPIs Direccion X:
    - columna_origen: "Reportes operativos"
    - "Visitas realizadas"
"""
        path = _write_yaml(body)
        try:
            forms = load_forms_from_yaml(path)
            spec = forms[0]
            self.assertEqual(spec.archivo, "VFIIC KPIs Direccion X.xlsx")
            self.assertEqual(spec.hoja, 0)
            self.assertEqual(spec.columnas_persona, ())
            self.assertTrue(spec.has_ingesta)
            self.assertEqual(spec.kpis[0].descripcion, "Reportes operativos")
            self.assertEqual(spec.kpis[1].columna_origen, "Visitas realizadas")
            self.assertEqual(spec.kpis[1].descripcion, "Visitas realizadas")
        finally:
            path.unlink(missing_ok=True)

    def test_v6_applies_title_case_when_descripcion_omitted(self) -> None:
        body = """
Direccion X:

  VFIIC KPIs Direccion X:
    - columna_origen: "Presentaciones Realizadas"
"""
        path = _write_yaml(body)
        try:
            forms = load_forms_from_yaml(path)
            self.assertEqual(forms[0].kpis[0].descripcion, "Presentaciones realizadas")
        finally:
            path.unlink(missing_ok=True)

    def test_area_id_is_slugified_from_display_name(self) -> None:
        body = """
Direccion Y:

  VFIIC KPIs Periciales - Análisis de Contexto:
    ingesta:
      archivo: "contexto.xlsx"
      columnas_persona: ["Auxiliar"]
    kpis:
      - columna_origen: "Informes"
        descripcion: "Informes"
"""
        path = _write_yaml(body)
        try:
            forms = load_forms_from_yaml(path)
            slug = forms[0].area_id
            self.assertEqual(slug, "vfiic_kpis_periciales_analisis_de_contexto")
        finally:
            path.unlink(missing_ok=True)

    def test_rejects_invalid_aggregation(self) -> None:
        body = """
Direccion Z:

  VFIIC KPIs Z:
    ingesta:
      archivo: "z.xlsx"
      columnas_persona: ["Auxiliar"]
    kpis:
      - columna_origen: "metric"
        descripcion: "Metric"
        aggregation: "median"
"""
        path = _write_yaml(body)
        try:
            with self.assertRaises(ValueError):
                load_forms_from_yaml(path)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
