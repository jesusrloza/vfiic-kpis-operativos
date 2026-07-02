# Guía del schema de indicadores

Archivo: `schemas/indicadores_vfiic_v6.yaml`

Cada formulario se define con el **nombre del formulario** (debe coincidir con el `.xlsx` en `inputs/`) y una **lista de KPIs**. El sistema infiere el resto: nombre de archivo, primera hoja, columna de periodo y columnas de persona.

## Plantilla por formulario

```yaml
Nombre de la Dirección:

  VFIIC KPIs Nombre del Formulario:
    - columna_origen: "Nombre exacto de columna en Excel"
    - columna_origen: "Otra columna"
      descripcion: "Etiqueta distinta en el reporte"
    - "Columna como texto simple"
```

### Qué infiere el sistema

| Aspecto | Comportamiento |
|---------|----------------|
| Archivo Excel | `{nombre del formulario}.xlsx` |
| Hoja | Primera hoja del libro |
| Columna de periodo | Busca `Periodo Evaluado`, `Periodo a Evaluar` u otra columna cuyo nombre contenga «periodo» |
| Columnas de persona | Detecta grupos como `Agente - Nombre(s)` + apellidos, `Perito - …`, `Titular - …`, etc. |
| Etiqueta en reporte | Title case español a partir de `columna_origen` (conectores en minúscula: de, en, la, …) |

### Campos de cada KPI

| Campo | Obligatorio | Descripción |
|-------|-------------|-------------|
| `columna_origen` | Sí | Encabezado tal como viene en el Excel. También puede escribirse como texto simple: `- "Mi columna"`. |
| `descripcion` | No | Solo si la etiqueta del comparativo debe diferir de la columna. Si se omite, se genera automáticamente en title case. |
| `aggregation` | No | `sum` (predeterminado), `count` o `avg`. |
| `value_parser` | No | `numeric` (predeterminado) o `sum_cantidad`. |

## Agregar un indicador

1. Confirme que la columna existe en el Excel en `inputs/` (o en una subcarpeta de `inputs/`).
2. En la lista del formulario, agregue:

```yaml
    - columna_origen: "Nueva métrica"
```

Si el reporte debe mostrar otro texto:

```yaml
    - columna_origen: "Nueva métrica"
      descripcion: "Etiqueta corta en el reporte"
```

3. Ejecute `python scripts/generar_comparativo.py` y revise la reconciliación.

## Modificar un indicador

- Cambie `descripcion` para el texto del reporte (o elimínela para usar la etiqueta automática).
- Cambie `columna_origen` si el encabezado en el Excel cambió.

## Eliminar un indicador

Borre la entrada completa de la lista (una o dos líneas según tenga `descripcion`).

## Agregar un formulario nuevo

1. Copie el `.xlsx` a `inputs/` o a una subcarpeta. El nombre del archivo debe ser `{nombre del formulario}.xlsx`.
2. Agregue un bloque bajo la dirección correspondiente con la lista de KPIs.
3. Genere reportes y corrija lo que indique la reconciliación.

## Formato legacy (v5)

El formato anterior con bloques `ingesta` y `kpis` sigue soportado. Referencia archivada en `schemas/archive/indicadores_vfiic_v5.yaml`.

## Errores al guardar el YAML

- Use espacios (no tabuladores) para la indentación.
- Las listas llevan guión `-` al inicio de cada ítem.
- Los comentarios con `#` al inicio de línea son válidos.

Si el script reporta error de YAML, el mensaje en consola indica el formulario afectado; compare con esta guía.
