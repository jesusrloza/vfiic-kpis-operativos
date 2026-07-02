# Scripts

**Estos son los únicos comandos que debe ejecutar el operador** para generar o limpiar reportes. Ejecute siempre desde la raíz del proyecto, con el entorno virtual activado (véase [docs/guia-instalacion.md](../docs/guia-instalacion.md)).

| Script | Qué genera | Salida |
|--------|------------|--------|
| `generar_comparativo.py` | Comparativo apilado (principal) | `outputs/comparativos/` |
| `generar_particionado.py` | Un Excel por formulario (hojas por mes) | `outputs/particionados/` |
| `limpiar_salidas.py` | Borra Excel generados en salidas | — |

Ejemplo:

```bash
python scripts/generar_comparativo.py
```

Tras `pip install -e .` también puede usar los comandos de consola `generar-comparativo` y `generar-particionado`; el flujo recomendado sigue siendo `python scripts/...`.

El código que implementa el pipeline vive en `lib/vfiic_kpis/` y no debe ejecutarse directamente.
