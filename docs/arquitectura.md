# Arquitectura del procesamiento de KPIs

## Objetivo

Procesar insumos heterogeneos por area y producir dos artefactos ejecutivos:
1. Workbook particionado por periodo mensual.
2. Workbook comparativo de variacion mensual y anual.
3. Workbook comparativo v2 con presentacion por area y semaforo semantico.

## Ejecucion recomendada

Comandos cortos desde la raiz del proyecto:

```bash
python scripts/build_partitioned_workbook.py
python scripts/build_monthly_comparison.py
python scripts/build_monthly_comparison_v2.py
```

Cada script acepta `--theme` con la ruta a un TOML de maquetación (por defecto `inputs/themes/excel_partitioned.toml`, `inputs/themes/excel_comparison.toml` y `inputs/themes/excel_comparison_v2.toml`). En una sola corrida, `run_all_reports.py` expone `--partitioned-theme`, `--comparison-theme` y flags opcionales de v2.

Alternativa en una sola corrida:

```bash
python scripts/run_all_reports.py
```

## Temas de presentación Excel

Los estilos (encabezado azul oscuro, tabla con bandas, formatos de porcentaje, anchos, filtros y congelado de paneles) viven en TOML versionables:

- `inputs/themes/excel_partitioned.toml` — hojas `original` y mensuales del particionado.
- `inputs/themes/excel_comparison.toml` — hoja `comparativo`.

El código los carga con `excel_theme.load_excel_theme` y los aplica tras `pandas.to_excel` mediante `excel_styling.apply_sheet_theme`, sin cambiar los nombres de columnas en los `DataFrame` de negocio.

## Flujo general

```mermaid
flowchart TD
  rawInputs["inputs/raw o directorio de entrada"] --> specs["inputs/specs/*.toml"]
  specs --> reader["io.py lectura por spec"]
  reader --> normalize["normalize.py periodo y agente"]
  normalize --> partitioned["build_partitioned_workbook.py"]
  normalize --> comparison["build_monthly_comparison.py"]
  normalize --> comparisonv2["build_monthly_comparison_v2.py"]
  partitioned --> outPart["outputs/particionados/*.xlsx"]
  comparison --> outComp["outputs/comparativos/*.xlsx"]
  comparisonv2 --> outCompV2["outputs/comparativos/comparativo_v2_kpis.xlsx"]
```

## Modulos principales

- `src/vfiic_kpis/spec_loader.py`
  - Carga los TOML y los transforma en objetos tipados (`AreaSpec`, `KpiSpec`).
- `src/vfiic_kpis/io.py`
  - Lee Excel por area en funcion de `source_glob`.
  - Compone `Agente/Titular` desde 1 o N columnas.
- `src/vfiic_kpis/normalize.py`
  - Estandariza periodo a datetime.
  - Deriva `periodo_mes_key` (`YYYY_mon`) y etiqueta de mes.
  - Crea llave de orden alfabetico normalizada (sin acentos, case-insensitive).
- `src/vfiic_kpis/metrics.py`
  - Calcula comparativo MoM y YoY por KPI.
  - Soporta parseo `numeric` y `sum_cantidad`.
  - Incluye builder v2 con tendencia semantica por KPI (`up_is_good` / `down_is_good`).
- `src/vfiic_kpis/excel_export.py`
  - Escribe salidas en formato XLSX y dispara la maquetación por tema.
- `src/vfiic_kpis/excel_theme.py`
  - Parsea TOML de tema (colores, estilo de tabla, reglas de formato y etiquetas de encabezado).
- `src/vfiic_kpis/excel_styling.py`
  - Post-proceso openpyxl: etiquetas legibles, formatos numéricos, tabla de Excel, autofiltro y anchos.

## Contrato del spec TOML

```toml
[area]
id = "trabajo_social"
display_name = "Trabajo Social"
source_glob = "*.xlsx"
sheet_name = "Form responses"
date_column = "Periodo Evaluado"
agent_columns = ["Perito - Nombre(s)", "Perito - Apellido Paterno", "Perito - Apellido Materno"]
agent_output_column = "Agente/Titular"

[[kpis]]
name = "dictamenes_trabajo_social"
source_column = "Dictámenes Realizados"
aggregation = "sum"
value_parser = "numeric"
change_direction = "up_is_good"
```

`change_direction` determina si subir es favorable (`up_is_good`) o desfavorable (`down_is_good`) para colorear diferencia y porcentaje en el comparativo v2.

## Reglas de negocio implementadas

- Periodo de entrada: base esperada `YYYY-MM-DD`; se acepta datetime de Excel.
- Particionado mensual: por clave `YYYY_mon` en espanol abreviado (`ene`, `feb`, `mar`, ...).
- Orden de agentes: ascendente usando normalizacion de acentos y mayusculas.
- Comparativo:
  - Siempre intenta ultimo mes vs mes anterior.
  - Solo agrega YoY cuando existe mismo mes del ano previo.

## Diagrama de decision para comparativo

```mermaid
flowchart TD
  startNode["Tomar ultimo mes con datos"] --> hasPrev{"Existe mes anterior?"}
  hasPrev -->|"Si"| calcMom["Calcular delta numero y delta % MoM"]
  hasPrev -->|"No"| noMom["Dejar columnas MoM vacias"]
  calcMom --> hasYoy{"Existe mismo mes del ano previo?"}
  noMom --> hasYoy
  hasYoy -->|"Si"| calcYoy["Calcular delta numero y delta % YoY"]
  hasYoy -->|"No"| noYoy["Dejar columnas YoY vacias"]
  calcYoy --> exportNode["Exportar workbook comparativo"]
  noYoy --> exportNode
```

## Escalabilidad para 60+ areas

- Un spec por area evita hardcodear columnas en codigo.
- Los scripts reutilizan pipeline comun y solo cambian las especificaciones.
- Nuevos parseadores de KPI se agregan en `metrics.py` sin modificar los scripts CLI.

