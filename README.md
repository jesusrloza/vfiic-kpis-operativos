# VFIIC KPIs — ETL y reportes Excel

Procesa exportaciones de formularios (Jotform / Google Sheets) y genera:

1. **Comparativo apilado** — un workbook con todos los formularios, variación mes anterior y año anterior cuando hay historia.
2. **Particionados** — un Excel por formulario con hoja `original` y una hoja por mes.

La configuración vive en `schemas/indicadores_vfiic_v5.yaml`. Los insumos van en `inputs/` (archivos `.xlsx`).

## Documentación

| Guía | Para quién |
|------|------------|
| [docs/guia-instalacion.md](docs/guia-instalacion.md) | Instalar Python y dependencias (Windows primero) |
| [docs/guia-operativa.md](docs/guia-operativa.md) | Uso diario: copiar Excel, correr scripts, leer salidas |
| [docs/guia-indicadores-yaml.md](docs/guia-indicadores-yaml.md) | Editar formularios e indicadores en el YAML |
| [docs/arquitectura.md](docs/arquitectura.md) | Detalle técnico del pipeline |

## Inicio rápido

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .
python scripts/generar_todos_los_reportes.py
```

Salidas: `outputs/comparativos/comparativo_kpis.xlsx`, `outputs/particionados/`, bitácora en `logs/reconciliacion.json`.

Scripts disponibles: ver [scripts/README.md](scripts/README.md).

## Estructura del proyecto

- `inputs/` — exportaciones Excel por formulario
- `schemas/` — catálogo YAML
- `themes/` — formato visual de los reportes Excel
- `scripts/` — comandos para generar o limpiar salidas
- `outputs/` — reportes generados
- `logs/` — reconciliación JSON
- `src/vfiic_kpis/` — código del pipeline
