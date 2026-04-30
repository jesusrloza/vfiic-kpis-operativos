from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vfiic_kpis.manifest import reconcile
from vfiic_kpis.yaml_loader import FormSpec, KpiSpec


def _make_spec(*, archivo: str | None, kpis: tuple[str, ...]) -> FormSpec:
    return FormSpec(
        area_id="trabajo_social",
        display_name="Trabajo Social",
        direccion="Coord Periciales",
        archivo=archivo,
        hoja="Form responses",
        columna_fecha_aliases=("Periodo Evaluado", "Periodo a Evaluar"),
        columnas_persona=("Auxiliar",),
        agent_output_column="Agente/Titular",
        kpis=tuple(KpiSpec(columna_origen=name, descripcion=name) for name in kpis),
    )


class TestManifestReconcile(unittest.TestCase):
    def test_form_without_ingesta_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            spec = FormSpec(
                area_id="x",
                display_name="X",
                direccion="D",
                archivo=None,
                hoja=None,
                columna_fecha_aliases=("Periodo Evaluado",),
                columnas_persona=(),
                agent_output_column="Agente/Titular",
                kpis=(KpiSpec(columna_origen="Col", descripcion="Col"),),
            )
            report = reconcile([spec], input_dir)
            self.assertEqual(len(report.matched), 0)
            self.assertEqual(len(report.yaml_without_ingesta), 1)

    def test_missing_file_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            spec = _make_spec(archivo="ausente.xlsx", kpis=("Col",))
            report = reconcile([spec], input_dir)
            self.assertEqual(len(report.matched), 0)
            self.assertEqual(len(report.yaml_without_file), 1)

    def test_extra_file_is_listed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            df = pd.DataFrame([{"Periodo Evaluado": "2026-04-01", "Auxiliar": "A", "Col": 1}])
            df.to_excel(input_dir / "extra.xlsx", index=False, sheet_name="Form responses")
            report = reconcile([], input_dir)
            self.assertEqual(report.files_without_yaml[0].name, "extra.xlsx")

    def test_file_with_columns_resolves_aliases_and_kpis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            df = pd.DataFrame(
                [
                    {
                        "Periodo a Evaluar": "2026-04-01",
                        "Auxiliar": "A",
                        "Col Existente": 1,
                    }
                ]
            )
            file_path = input_dir / "VFIIC KPIs Periciales - Demo.xlsx"
            df.to_excel(file_path, index=False, sheet_name="Form responses")

            spec = FormSpec(
                area_id="demo",
                display_name="VFIIC KPIs Periciales - Demo",
                direccion="Periciales",
                archivo="VFIIC KPIs Periciales - Demo.xlsx",
                hoja="Form responses",
                columna_fecha_aliases=("Periodo Evaluado", "Periodo a Evaluar"),
                columnas_persona=("Auxiliar",),
                agent_output_column="Agente/Titular",
                kpis=(
                    KpiSpec(columna_origen="Col Existente", descripcion="Existente"),
                    KpiSpec(columna_origen="Col Inexistente", descripcion="Falta"),
                ),
            )
            report = reconcile([spec], input_dir)
            self.assertEqual(len(report.matched), 1)
            resolution = report.matched[0]
            self.assertEqual(resolution.resolved_date_column, "Periodo a Evaluar")
            self.assertEqual(resolution.available_kpis, ("Col Existente",))
            self.assertEqual(resolution.missing_columns, ("Col Inexistente",))

    def test_file_matching_display_name_is_not_orphan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            df = pd.DataFrame([{"Col": 1}])
            (input_dir / "VFIIC KPIs - Demo.xlsx").write_bytes(b"")
            df.to_excel(
                input_dir / "VFIIC KPIs - Demo.xlsx",
                index=False,
                sheet_name="Form responses",
            )
            spec = FormSpec(
                area_id="demo",
                display_name="VFIIC KPIs - Demo",
                direccion="D",
                archivo=None,
                hoja=None,
                columna_fecha_aliases=("Periodo Evaluado",),
                columnas_persona=(),
                agent_output_column="Agente/Titular",
                kpis=(KpiSpec(columna_origen="Col", descripcion="Col"),),
            )
            report = reconcile([spec], input_dir)
            self.assertEqual(len(report.yaml_without_ingesta), 1)
            self.assertEqual(report.files_without_yaml, ())

    def test_form_with_no_matching_kpis_goes_to_column_issues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            df = pd.DataFrame([{"Periodo Evaluado": "2026-04-01", "Auxiliar": "A"}])
            file_path = input_dir / "demo.xlsx"
            df.to_excel(file_path, index=False, sheet_name="Form responses")
            spec = _make_spec(archivo="demo.xlsx", kpis=("Col Inexistente",))
            report = reconcile([spec], input_dir)
            self.assertEqual(len(report.matched), 0)
            self.assertEqual(len(report.yaml_with_column_issues), 1)


if __name__ == "__main__":
    unittest.main()
