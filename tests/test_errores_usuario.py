from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vfiic_kpis.errores_usuario import mensaje_para_usuario


class TestErroresUsuario(unittest.TestCase):
    def test_permission_error_on_input(self) -> None:
        ruta = Path("inputs/demo.xlsx")
        msg = mensaje_para_usuario(
            PermissionError("denied"),
            contexto="leer",
            ruta=ruta,
        )
        self.assertIn("demo.xlsx", msg)
        self.assertIn("Excel", msg)

    def test_permission_error_on_output(self) -> None:
        ruta = Path("outputs/comparativos/comparativo_kpis.xlsx")
        msg = mensaje_para_usuario(
            PermissionError("denied"),
            contexto="escribir",
            ruta=ruta,
        )
        self.assertIn("comparativo_kpis.xlsx", msg)
        self.assertIn("abierto", msg.lower())

    def test_file_not_found(self) -> None:
        ruta = Path("schemas/falta.yaml")
        msg = mensaje_para_usuario(FileNotFoundError("no"), contexto="cargar", ruta=ruta)
        self.assertIn("falta.yaml", msg)

    def test_value_error_yaml_hint(self) -> None:
        msg = mensaje_para_usuario(
            ValueError("falta `ingesta`"),
            contexto="validar",
        )
        self.assertIn("guia-indicadores-yaml", msg)


if __name__ == "__main__":
    unittest.main()
