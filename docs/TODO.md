# Pendientes y notas para desarrolladores

Este archivo recoge mejoras planificadas y convenciones que **no** forman parte de la guía operativa para quienes generan reportes.

## Resuelto recientemente

- Clasificación de incidencias (breaking / advertencia / informativo), reportes detallado y crítico, y consola `omitido` vs `advertencia`: documentado en [errores-y-validacion.md](errores-y-validacion.md).
- Validación relajada de agente para el comparativo (periodo + KPIs suficientes).
- Orden de hojas mensuales en particionado (más reciente primero).

## Flujo AREA vs PERSONA (iteración futura)

Hoy la operación espera **llenado por áreas**. El código tolera archivos con prefijo `AREA - ` en el nombre, y también reconoce `PERSONA - ` por compatibilidad, pero el flujo operativo completo para captura por persona queda para una iteración posterior.

Hasta entonces:

- Use un solo criterio de nombres por corrida (recomendado: sin prefijo o con `AREA - `).
- Evite mezclar variantes del mismo formulario en `inputs/` (el pipeline marca ambigüedad).

## Escenarios demo comprimidos (solo desarrollo)

Los archivos comprimidos (`.zip`, `.7z`, `.rar`, `.tar`, `.tar.gz`, `.gz`, etc.) dentro de `inputs/`:

- Están **ignorados por git** (véase `.gitignore`).
- **No** los lee el pipeline (solo busca `.xlsx` de forma recursiva).
- Sirven para que desarrolladores guarden colecciones de insumos de prueba en el árbol local sin versionar cada Excel.

Para usar un escenario demo: descomprima los `.xlsx` en `inputs/` (o subcarpetas) antes de ejecutar los scripts de reporte.

## Organización de `inputs/`

- Los `.xlsx` pueden estar en `inputs/` o en **subcarpetas** (cualquier profundidad).
- El YAML sigue referenciando solo el **nombre de archivo** (`ingesta.archivo`), no la ruta.
- Dos archivos con el **mismo nombre** en carpetas distintas se reportan como duplicado y no se procesan hasta resolver el conflicto.
