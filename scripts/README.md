# Scripts

**Estos son los únicos comandos que debe ejecutar el operador** para generar o limpiar reportes. Ejecute siempre desde la raíz del proyecto, con el entorno virtual activado (véase [docs/guia-instalacion.md](../docs/guia-instalacion.md)).

| Script | Qué genera | Salida |
|--------|------------|--------|
| `generar_todos_los_reportes.py` | Comparativo y particionados | `outputs/comparativos/` y `outputs/particionados/` |
| `generar_comparativo.py` | Solo comparativo apilado | `outputs/comparativos/comparativo_kpis.xlsx` |
| `generar_particionado.py` | Un Excel por formulario (hojas por mes) | `outputs/particionados/` |
| `limpiar_salidas.py` | Borra Excel generados en salidas | — |

Ejemplo:

```bash
python scripts/generar_todos_los_reportes.py
```

Tras `pip install -e .` también puede usar los comandos de consola `generar-todos`, `generar-comparativo` y `generar-particionado`; el flujo recomendado sigue siendo `python scripts/...`.

El código que implementa el pipeline vive en `lib/vfiic_kpis/` y no debe ejecutarse directamente.
