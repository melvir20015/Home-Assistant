# Hotfix: arranque limpio + ejecución robusta en `AC - Learning - Manual ON feedback`

**Fecha:** 2026-04-21

## Causa raíz del fallo de parseo (línea ~5464)

Se detectó una construcción frágil en el bloque final de notificación de `AC - Learning - Manual ON feedback`:

1. `message` y `value` incluían expresiones Jinja largas inline, con concatenaciones densas en una sola línea.
2. El bloque mezclaba patrones `service`/`action` sin una separación clara por paso funcional.
3. Había alta probabilidad de error de parseo YAML/Jinja al combinar comillas, concatenaciones y condicionales extensos en un único campo.

## Correcciones aplicadas

### 1) Reescritura del bloque de acciones final

Se reestructuró completamente el bloque alrededor de la línea reportada (~5464), separando:

- escritura de estado pendiente (`input_text.ac_dda_last_notify_status`),
- registro de intento (`logbook.log`),
- envío de notificación móvil o fallback,
- escritura de estado final de notificación.

Además, se evitó mezclar claves y se dejó cada acción como paso atómico.

### 2) Variables intermedias para reducir complejidad inline

Se movieron subexpresiones complejas a `variables:` previas:

- `pending_trace_label`
- `run_trace_label`
- `pending_ts`
- `final_channel_label`
- `notify_pending_status`
- `notify_result_status`
- `notify_mobile_message`

Con esto, los `message`/`value` quedaron con interpolaciones simples y estables.

### 3) Variables potencialmente no definidas corregidas con defaults defensivos

Se reforzaron defaults para:

- `manual_on_session_age_s`: fallback seguro cuando no existe `started_epoch` (`99999`).
- `manual_override_active`: fallback booleano defensivo con `| default(false)` tanto en su definición como en condiciones/mensajes donde se evalúa.

## Criterio de plantillas seguras adoptado

Para prevenir recurrencia:

1. **No construir mensajes complejos inline**: crear variables intermedias y reusar.
2. **Aplicar `| default(...)` antes de comparar/formatear** en flags, timestamps y labels críticos.
3. **Evitar accesos frágiles a estructuras**: usar parsing tolerante (`regex_findall_index`) y fallback explícito en ausencia de datos.
4. **Mensajes finales compactos y deterministas**: una sola plantilla base reutilizada para canal móvil y fallback.

## Validación operativa recomendada

Orden recomendado de despliegue en HA:

1. `check_config`
2. recarga de automatizaciones
3. reinicio de HA

Si alguno de esos pasos falla por entorno/herramienta ausente, dejar evidencia en bitácora de despliegue y ejecutar el siguiente paso desde la consola oficial de Home Assistant.
