from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIB = PROJECT_ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from vfiic_kpis.yaml_loader import load_forms_from_yaml


def _write_yaml(body: str) -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
    handle.write(body)
    handle.close()
    return Path(handle.name)


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

    def test_rejects_list_only_form_definition(self) -> None:
        body = """
Direccion X:

  VFIIC KPIs Direccion X:
    - columna_origen: "Reportes operativos"
      descripcion: "Reportes operativos"
"""
        path = _write_yaml(body)
        try:
            with self.assertRaises(ValueError):
                load_forms_from_yaml(path)
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
