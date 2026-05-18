# Scripts

Comandos para generar reportes (ejecutar desde la raíz del proyecto, con el entorno virtual activado).

| Script | Qué genera | Salida |
|--------|------------|--------|
| `generar_todos_los_reportes.py` | Comparativo y particionados | `outputs/comparativos/` y `outputs/particionados/` |
| `generar_comparativo.py` | Solo comparativo apilado | `outputs/comparativos/comparativo_kpis.xlsx` |
| `generar_particionado.py` | Un Excel por formulario (hojas por mes) | `outputs/particionados/` |
| `limpiar_salidas.py` | Borra Excel generados en salidas | — |
| `actualizar_ingesta_en_schema.py` | Mantenimiento: refresca `ingesta` desde Excel | `schemas/indicadores_vfiic_v5.yaml` |

Ejemplo:

```bash
python scripts/generar_todos_los_reportes.py
```

Tras `pip install -e .` también puede usar: `generar-todos`, `generar-comparativo`, `generar-particionado`.
