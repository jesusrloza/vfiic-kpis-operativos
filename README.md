# VFIIC KPIs - ETL y reportes Excel

Procesador de insumos de KPIs (Jotform/Google Sheets exportados) que genera, a partir de un único schema YAML por dirección/formulario, dos artefactos ejecutivos:

1. **Comparativo apilado** (un solo workbook, un solo sheet) con MoM y YoY condicionales por formulario.
2. **Particionado por mes**, un workbook por formulario, con hoja `original` y hojas mensuales.

Cada corrida emite además un **resumen de reconciliación** en consola y `outputs/_logs/reconciliacion.json` indicando qué formularios fueron procesados, cuáles aún no tienen `ingesta` definida, cuáles no encontraron archivo en `inputs/raw/` y qué archivos de `inputs/raw/` no están en el YAML.

## Estructura del proyecto

- `inputs/raw/`: archivos `.xlsx` exportados por formulario (gitignored).
- `inputs/themes/`: temas de presentación Excel (`excel_partitioned.toml`, `excel_comparison_v2.toml`).
- `schemas/indicadores_vfiic_v5.yaml`: catálogo único de formularios y KPIs.
- `scripts/`: puntos de entrada CLI.
- `src/vfiic_kpis/`: pipeline de carga, métricas y exportación.
- `outputs/particionados/`: un Excel por formulario con la hoja `original` y una por mes.
- `outputs/comparativos/`: workbook comparativo apilado.
- `outputs/_logs/`: bitácoras de ejecución (JSON).

## Requisitos

- Python 3.11+
- `pandas`, `openpyxl`, `PyYAML` (instalados con el paquete).

## Setup local

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
pip install -e .
```

## Configuración por formulario (YAML)

El YAML mantiene una estructura jerárquica `Dirección -> Formulario -> definición`. Cada formulario admite dos formas:

### Forma legacy (sólo KPIs)

```yaml
Dirección X:

  VFIIC KPIs Dirección X:
    - columna_origen: "Reportes operativos"
      descripcion: "Reportes operativos"
```

Sin `ingesta`, el formulario aparece en el resumen como pendiente de configuración y no se procesa.

### Forma completa (con ingesta)

```yaml
Coordinación de Servicios Periciales:

  VFIIC KPIs Periciales - Trabajo Social:
    ingesta:
      archivo: "VFIIC KPIs Periciales - Trabajo Social.xlsx"
      hoja: "Form responses"
      columna_fecha: ["Periodo Evaluado", "Periodo a Evaluar"]
      columnas_persona:
        - "Perito - Nombre(s)"
        - "Perito - Apellido Paterno"
        - "Perito - Apellido Materno"
    kpis:
      - columna_origen: "Dictámenes Realizados"
        descripcion: "Dictámenes realizados"
```

Notas:

- `archivo`: nombre exacto del archivo en `inputs/raw/`. Si se omite, se intenta `<display_name>.xlsx`.
- `hoja`: nombre de la hoja Excel; por defecto `"Form responses"`.
- `columna_fecha`: string o lista de alias; se resuelve la primera coincidencia tolerando acentos y mayúsculas.
- `columnas_persona`: una o varias columnas; si son varias se concatenan en `Agente/Titular`.
- KPI: `columna_origen` (texto exacto en el archivo) y `descripcion` (etiqueta visible en el reporte). Opcional: `aggregation` (`sum` | `count` | `avg`, por defecto `sum`) y `value_parser` (`numeric` | `sum_cantidad`).
- Si no se declara `id` en `ingesta`, se deriva automáticamente del `display_name`.

## Uso

```bash
python scripts/run_all_reports.py
```

Equivalente vía entry points:

```bash
vfiic-run-all
vfiic-partitioned
vfiic-comparativo
```

Por defecto:

- Schema: `schemas/indicadores_vfiic_v5.yaml`
- Insumos: `inputs/raw/`
- Particionados: `outputs/particionados/<area_id>.xlsx`
- Comparativo: `outputs/comparativos/comparativo_kpis.xlsx`
- Bitácora: `outputs/_logs/reconciliacion.json`

Sobreescribir rutas:

```bash
python scripts/run_all_reports.py \
  --schema schemas/indicadores_vfiic_v5.yaml \
  --input-dir inputs/raw \
  --partitioned-dir outputs/particionados \
  --comparison-output outputs/comparativos/comparativo_kpis.xlsx \
  --reconciliation-log outputs/_logs/reconciliacion.json
```

## Reglas de reporte

- **Particionado**: se genera siempre que el formulario tenga al menos un periodo parseable.
- **Comparativo**:
  - Cada formulario aporta un bloque (título + encabezado + filas + 2 filas vacías).
  - El último mes con datos define el encabezado dinámico del valor actual.
  - Si existe mes anterior, se llenan `Diferencia (mes anterior)` y `Variación % (mes anterior)`.
  - Si existe mismo mes del año previo, se llenan `Diferencia (año anterior)` y `Variación % (año anterior)`.
  - En cualquier caso las columnas se mantienen visibles; las celdas vacías indican que aún no hay historia suficiente.
- Las filas con multiple registros en un mismo mes se **suman** automáticamente (`aggregation = "sum"`).
- La convención semántica es siempre **subir es bueno**.

## Reconciliación

El resumen agrupa los formularios en cuatro categorías y lista los archivos de `inputs/raw/` que no están en el YAML:

- `procesables`
- `sin archivo en inputs/raw`
- `sin ingesta definida en el YAML`
- `con problemas de columnas`
- `archivos en inputs/raw sin entrada en el YAML`

El JSON sidecar contiene el detalle por formulario: archivo resuelto, hoja, columna de fecha resuelta, columnas de persona, KPIs disponibles y KPIs sin columna.
