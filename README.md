# VFIIC KPIs — ETL y reportes Excel

Procesa exportaciones de formularios (Jotform / Google Sheets) y genera:

1. **Comparativo apilado** — un workbook con todos los formularios, variación mes anterior y año anterior cuando hay historia.
2. **Particionados** — un Excel por formulario con hoja `original` y una hoja por mes.

La configuración vive en `schemas/indicadores_vfiic_v6.yaml`. Los insumos van en `inputs/` (archivos `.xlsx`, en la raíz o en subcarpetas).

## Documentación

| Guía | Para quién |
|------|------------|
| [docs/README.md](docs/README.md) | Índice de toda la documentación |
| [docs/guia-instalacion.md](docs/guia-instalacion.md) | Instalar Python y dependencias (Windows primero) |
| [docs/guia-operativa.md](docs/guia-operativa.md) | Uso diario: copiar Excel, correr scripts, leer salidas |
| [docs/errores-y-validacion.md](docs/errores-y-validacion.md) | Incidencias de captura, consola y reportes detallado/crítico |
| [docs/guia-indicadores-yaml.md](docs/guia-indicadores-yaml.md) | Editar formularios e indicadores en el YAML |
| [docs/arquitectura.md](docs/arquitectura.md) | Detalle técnico del pipeline |
| [docs/TODO.md](docs/TODO.md) | Pendientes y notas para desarrolladores |

## Inicio rápido

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .
python scripts/generar_comparativo.py
```

Salidas: `outputs/comparativos/comparativo_kpis_<timestamp>.xlsx`, `outputs/particionados/` (con `generar_particionado.py`), bitácora en `logs/reconciliacion.json`.

**Comandos para operadores:** use únicamente los scripts en [scripts/](scripts/) (véase [scripts/README.md](scripts/README.md)).

## Estructura del proyecto

| Carpeta | Quién la usa | Para qué |
|---------|--------------|----------|
| `inputs/` | Operadores | Exportaciones `.xlsx` (pueden organizarse en subcarpetas) |
| `schemas/` | Operadores / coordinadores | Catálogo YAML de formularios e indicadores |
| `scripts/` | **Operadores** | Comandos para generar o limpiar reportes |
| `outputs/` | Operadores | Reportes generados |
| `logs/` | Operadores | Reconciliación JSON |
| `themes/` | Desarrollo | Formato visual de los Excel de salida |
| `lib/vfiic_kpis/` | Desarrollo | Código interno del pipeline (no ejecutar directamente) |
| `tests/` | Desarrollo | Pruebas automatizadas |
