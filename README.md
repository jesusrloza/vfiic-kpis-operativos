# VFIIC KPIs - ETL y reportes Excel

Proyecto Python para procesar insumos de KPIs por area (Jotform/Google Sheets exportados), con estructura escalable para 60+ formatos mediante especificaciones TOML.

## Estructura del proyecto

- `inputs/raw/`: archivos fuente de entrada.
- `inputs/specs/`: archivo `*.toml` por area/formato.
- `scripts/`: puntos de entrada CLI.
- `src/vfiic_kpis/`: modulos compartidos de lectura, normalizacion, metricas y exportacion.
- `outputs/particionados/`: Excel con hoja original + hojas por mes.
- `outputs/comparativos/`: Excel con comparativo mensual.
- `logs/`: bitacoras de ejecucion.

## Requisitos

- Python 3.11+

## Setup local con venv

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
pip install -e .
```

## Configuracion por area (specs)

Cada area tiene un archivo TOML en `inputs/specs/`.

Ejemplo inicial: `inputs/specs/trabajo_social.toml`, donde se define:
- identificador y nombre de area,
- patron de archivo de entrada (`source_glob`),
- hoja Excel (`sheet_name`),
- columna de fecha (`YYYY-MM-DD` esperado en negocio; se soporta valor tipo fecha Excel),
- columnas para componer `Agente/Titular`,
- KPIs a reportar y su parser (`numeric` o `sum_cantidad`).

Plantillas incluidas para acelerar altas de nuevas areas:
- `inputs/specs/_template_area_base.toml`
- `inputs/specs/_template_agente_columna_unica.toml`
- `inputs/specs/_template_kpi_cantidad_texto.toml`

Sugerencia: copiar una plantilla y renombrarla como `nombre_area.toml`, luego ajustar columnas/KPIs.

## Script 1: workbook particionado por mes

Genera un solo Excel con:
- hoja `original` (datos completos normalizados),
- hojas por periodo `YYYY_mon` (ej: `2026_mar`, `2026_abr`),
- orden alfabetico ascendente por `Agente/Titular` con normalizacion de acentos/mayusculas.

```bash
python scripts/build_partitioned_workbook.py \
  --input-dir data \
  --specs-dir inputs/specs \
  --output outputs/particionados/particionado_kpis.xlsx
```

## Script 2: comparativo mensual

Genera un Excel con tabla comparativa por KPI:
- ultimo mes disponible vs mes anterior (diferencia numero y porcentaje),
- opcionalmente ultimo mes vs mismo mes del ano previo (si existe).

```bash
python scripts/build_monthly_comparison.py \
  --input-dir data \
  --specs-dir inputs/specs \
  --output outputs/comparativos/comparativo_kpis.xlsx
```

## Extender a nuevas areas

1. Agregar archivo fuente a `inputs/raw/` (o usar otro directorio de entrada via CLI).
2. Crear un nuevo spec TOML en `inputs/specs/`.
3. Definir mapeo de fecha, agente y KPIs.
4. Ejecutar ambos scripts.

## Nota sobre carpeta de entrada

Para mantener compatibilidad con tu estado actual, los scripts aceptan `--input-dir data`.
La recomendacion operativa es migrar gradualmente a `inputs/raw/` para separar insumos de codigo.

