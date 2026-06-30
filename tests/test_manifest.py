from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIB = PROJECT_ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from vfiic_kpis.manifest import reconcile
from vfiic_kpis.user_messages import SKIP_AMBIGUOUS_INPUT_FILE, SKIP_DUPLICATE_INPUT_FILE
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

    def test_file_without_ingesta_archivo_is_orphan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            df = pd.DataFrame([{"Col": 1}])
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
            self.assertEqual(len(report.files_without_yaml), 1)

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

    def _write_demo_workbook(self, directory: Path, filename: str) -> None:
        df = pd.DataFrame(
            [{"Periodo Evaluado": "2026-04-01", "Auxiliar": "A", "Col": 1}]
        )
        df.to_excel(directory / filename, index=False, sheet_name="Form responses")

    def test_area_prefixed_file_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            self._write_demo_workbook(input_dir, "AREA - demo.xlsx")
            spec = _make_spec(archivo="demo.xlsx", kpis=("Col",))
            report = reconcile([spec], input_dir)
            self.assertEqual(len(report.matched), 1)
            self.assertEqual(report.matched[0].file_path.name, "AREA - demo.xlsx")
            self.assertEqual(report.files_without_yaml, ())

    def test_persona_prefixed_file_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            self._write_demo_workbook(input_dir, "PERSONA - demo.xlsx")
            spec = _make_spec(archivo="demo.xlsx", kpis=("Col",))
            report = reconcile([spec], input_dir)
            self.assertEqual(len(report.matched), 1)
            self.assertEqual(report.matched[0].file_path.name, "PERSONA - demo.xlsx")

    def test_unprefixed_file_still_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            self._write_demo_workbook(input_dir, "demo.xlsx")
            spec = _make_spec(archivo="demo.xlsx", kpis=("Col",))
            report = reconcile([spec], input_dir)
            self.assertEqual(len(report.matched), 1)
            self.assertEqual(report.matched[0].file_path.name, "demo.xlsx")

    def test_area_and_persona_same_form_is_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            self._write_demo_workbook(input_dir, "AREA - demo.xlsx")
            self._write_demo_workbook(input_dir, "PERSONA - demo.xlsx")
            spec = _make_spec(archivo="demo.xlsx", kpis=("Col",))
            report = reconcile([spec], input_dir)
            self.assertEqual(len(report.matched), 0)
            self.assertEqual(len(report.yaml_with_column_issues), 1)
            self.assertEqual(
                report.yaml_with_column_issues[0].skip_reason,
                SKIP_AMBIGUOUS_INPUT_FILE,
            )

    def test_unprefixed_and_area_same_form_is_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            self._write_demo_workbook(input_dir, "demo.xlsx")
            self._write_demo_workbook(input_dir, "AREA - demo.xlsx")
            spec = _make_spec(archivo="demo.xlsx", kpis=("Col",))
            report = reconcile([spec], input_dir)
            self.assertEqual(len(report.matched), 0)
            self.assertEqual(len(report.yaml_with_column_issues), 1)
            self.assertEqual(
                report.yaml_with_column_issues[0].skip_reason,
                SKIP_AMBIGUOUS_INPUT_FILE,
            )

    def test_prefixed_file_without_yaml_is_orphan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            self._write_demo_workbook(input_dir, "AREA - orphan.xlsx")
            report = reconcile([], input_dir)
            self.assertEqual(len(report.files_without_yaml), 1)
            self.assertEqual(report.files_without_yaml[0].name, "AREA - orphan.xlsx")

    def test_subdirectory_file_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            subdir = input_dir / "area_x"
            subdir.mkdir()
            self._write_demo_workbook(subdir, "demo.xlsx")
            spec = _make_spec(archivo="demo.xlsx", kpis=("Col",))
            report = reconcile([spec], input_dir)
            self.assertEqual(len(report.matched), 1)
            self.assertIn("area_x", report.matched[0].file_path.as_posix())

    def test_duplicate_basename_blocks_matching(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            area_a = input_dir / "area_a"
            area_b = input_dir / "area_b"
            area_a.mkdir()
            area_b.mkdir()
            self._write_demo_workbook(area_a, "demo.xlsx")
            self._write_demo_workbook(area_b, "demo.xlsx")
            spec = _make_spec(archivo="demo.xlsx", kpis=("Col",))
            report = reconcile([spec], input_dir)
            self.assertEqual(len(report.matched), 0)
            self.assertEqual(len(report.duplicate_input_files), 1)
            self.assertEqual(report.duplicate_input_files[0][0], "demo.xlsx")
            self.assertEqual(len(report.yaml_with_column_issues), 1)
            self.assertEqual(
                report.yaml_with_column_issues[0].skip_reason,
                SKIP_DUPLICATE_INPUT_FILE,
            )

    def test_duplicate_paths_listed_in_detail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            area_a = input_dir / "area_a"
            area_b = input_dir / "area_b"
            area_a.mkdir()
            area_b.mkdir()
            self._write_demo_workbook(area_a, "demo.xlsx")
            self._write_demo_workbook(area_b, "demo.xlsx")
            spec = _make_spec(archivo="demo.xlsx", kpis=("Col",))
            report = reconcile([spec], input_dir)
            detail = report.yaml_with_column_issues[0].skip_detail or ""
            self.assertIn("area_a/demo.xlsx", detail)
            self.assertIn("area_b/demo.xlsx", detail)

    def test_non_duplicate_files_still_process(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            area_a = input_dir / "area_a"
            area_b = input_dir / "area_b"
            area_a.mkdir()
            area_b.mkdir()
            self._write_demo_workbook(area_a, "dup.xlsx")
            self._write_demo_workbook(area_b, "dup.xlsx")
            self._write_demo_workbook(input_dir, "ok.xlsx")
            dup_spec = _make_spec(archivo="dup.xlsx", kpis=("Col",))
            ok_spec = _make_spec(archivo="ok.xlsx", kpis=("Col",))
            report = reconcile([dup_spec, ok_spec], input_dir)
            self.assertEqual(len(report.matched), 1)
            self.assertEqual(report.matched[0].spec.archivo, "ok.xlsx")
            self.assertEqual(len(report.duplicate_input_files), 1)

    def test_auto_detects_person_columns_when_yaml_omits_them(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            df = pd.DataFrame(
                [
                    {
                        "Periodo Evaluado": "2026-04-01",
                        "Agente - Nombre(s)": "Ana",
                        "Agente - Apellido Paterno": "Lopez",
                        "Agente - Apellido Materno": "Perez",
                        "Col": 1,
                    }
                ]
            )
            df.to_excel(input_dir / "demo.xlsx", index=False)
            spec = FormSpec(
                area_id="demo",
                display_name="Demo",
                direccion="D",
                archivo="demo.xlsx",
                hoja=0,
                columna_fecha_aliases=("Periodo Evaluado", "Periodo a Evaluar"),
                columnas_persona=(),
                agent_output_column="Agente/Titular",
                kpis=(KpiSpec(columna_origen="Col", descripcion="Col"),),
            )
            report = reconcile([spec], input_dir)
            self.assertEqual(len(report.matched), 1)
            resolution = report.matched[0]
            self.assertEqual(len(resolution.resolved_person_columns), 3)
            self.assertEqual(resolution.resolved_sheet, 0)


if __name__ == "__main__":
    unittest.main()
