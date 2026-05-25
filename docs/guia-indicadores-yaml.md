# Guía del schema de indicadores

Archivo: `schemas/indicadores_vfiic_v5.yaml`

Cada formulario se define con un bloque **`ingesta`** (cómo leer el Excel) y una lista **`kpis`** (qué indicadores mostrar en el comparativo).

## Plantilla por formulario

```yaml
Nombre de la Dirección:

  VFIIC KPIs Nombre del Formulario:
    ingesta:
      archivo: "VFIIC KPIs Nombre del Formulario.xlsx"
      hoja: "Form responses"
      columna_fecha:
        - "Periodo Evaluado"
        - "Periodo a Evaluar"
      columnas_persona:
        - "Agente - Nombre(s)"
        - "Agente - Apellido Paterno"
        - "Agente - Apellido Materno"
    kpis:
      - columna_origen: "Nombre exacto de columna en Excel"
        descripcion: "Etiqueta visible en el reporte"
```

### Campos de `ingesta`

| Campo | Descripción |
|-------|-------------|
| `archivo` | Nombre canónico del `.xlsx` **sin** prefijo. En `inputs/` puede copiarse así, o como `AREA - …` o `PERSONA - …` (mismo contenido de columnas; no deje dos variantes del mismo formulario a la vez). |
| `hoja` | Hoja a leer; por lo general `Form responses`. |
| `columna_fecha` | Una o varias columnas; se usa la primera que exista en el archivo. |
| `columnas_persona` | Columnas para armar el nombre del agente/titular en el reporte. |
| `id` | (Opcional) Identificador interno si el nombre del formulario no basta. |

### Campos de cada KPI

| Campo | Obligatorio | Descripción |
|-------|-------------|-------------|
| `columna_origen` | Sí | Encabezado tal como viene en el Excel. |
| `descripcion` | Sí | Texto que verá el usuario en el comparativo. |
| `aggregation` | No | `sum` (predeterminado), `count` o `avg`. |
| `value_parser` | No | `numeric` (predeterminado) o `sum_cantidad`. |

## Agregar un indicador

1. Confirme que la columna existe en el Excel en `inputs/`.
2. En el bloque `kpis` del formulario, agregue:

```yaml
      - columna_origen: "Nueva métrica"
        descripcion: "Nueva métrica (etiqueta corta)"
```

3. Ejecute `python scripts/generar_comparativo.py` (o `generar_todos_los_reportes.py`) y revise la reconciliación.

## Modificar un indicador

- Cambie `descripcion` para el texto del reporte.
- Cambie `columna_origen` si el encabezado en el Excel cambió.

## Eliminar un indicador

Borre la entrada completa de la lista `kpis` (las dos líneas `columna_origen` / `descripcion` y opcionales).

## Agregar un formulario nuevo

1. Copie el `.xlsx` a `inputs/` (con o sin prefijo `AREA - ` / `PERSONA - `).
2. Agregue un bloque bajo la dirección correspondiente siguiendo la plantilla.
3. Ajuste `archivo`, `columna_fecha`, `columnas_persona` y la lista `kpis`.
4. Genere reportes y corrija lo que indique la reconciliación.

## Errores al guardar el YAML

- Use espacios (no tabuladores) para la indentación.
- Las listas bajo `kpis` llevan guión `-` al inicio de cada ítem.
- No use una lista suelta de KPIs sin bloque `ingesta`; el sistema exige la plantilla completa.

Si el script reporta error de YAML, el mensaje en consola indica el formulario afectado; compare con esta guía.
