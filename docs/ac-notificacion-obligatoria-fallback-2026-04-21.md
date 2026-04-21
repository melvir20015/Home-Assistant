# AC Manual ON — Contrato de notificación obligatoria con fallback (2026-04-21)

## Objetivo
Evitar pérdida de visibilidad operativa del flujo **Manual ON / Learning ON** cuando el canal móvil no esté disponible.

## Alcance
- `AC - Manual ON guard + presencia temporal`
- `AC - Learning - Manual ON feedback`
- Helper de auditoría de sesión: `input_text.ac_dda_last_notify_status`

## Contrato operativo

### 1) Política transaccional de notificación (obligatoria)
Antes de cada intento de push móvil se debe registrar:
- `notify_stage=send_attempt`
- `trace_id=<...>`
- `notify_channel=mobile`

Después del intento se debe registrar:
- `notify_stage=send_result`
- resultado por canal:
  - `notify_result=mobile_sent`, o
  - `notify_result=mobile_failed_fallback_persistent`

### 2) Fallback inmediato de canal
Cuando el canal móvil no está disponible (`device_tracker.samsung_s24` en `unknown|unavailable`),
la automatización debe:
1. crear `persistent_notification.create` con el mismo contenido funcional,
2. registrar resultado `mobile_failed_fallback_persistent` en `logbook.log`.

### 3) Auditoría unificada por sesión
`input_text.ac_dda_last_notify_status` guarda el último estado en formato:

`trace_id|stage|channel|result|ts`

Estados mínimos esperados por sesión:
- inicio: `stage=pendiente` + `result=pendiente`
- cierre guard: `stage=capturado|cierre` + `result=capturado|ignorado|error_controlado`
- cierre learning: `stage=learning_final` + resultado final contractual

## Garantías de visibilidad

1. **Mínimo por sesión:** una salida de inicio (`pendiente`) y una de cierre (`aplicado|ignorado|error_controlado`).
2. Si hay descarte temprano y no aplica `pendiente`, igualmente debe existir cierre explícito (`ignorado` con razón).
3. Se evita `stop` silencioso para rutas con notificación contractual: siempre hay evidencia en logbook y/o fallback persistente.

## Trazabilidad de “sí aprendió aunque no notificó móvil”

En Learning ON:
- se registra `hito=learning_on_applied` con valores escritos (`off`, `on`, `helper`),
- si falla móvil (canal no disponible), queda evidencia dual:
  - `logbook.log` con `notify_result=mobile_failed_fallback_persistent`,
  - `persistent_notification.create` con `trace_id`.

## Validación rápida por `trace_id`

1. Buscar en logbook `trace_id=<valor>`.
2. Confirmar secuencia:
   - `notify_stage=send_attempt`
   - `notify_stage=send_result`
3. Revisar el helper:
   - `input_text.ac_dda_last_notify_status`
   - formato `trace_id|stage|channel|result|ts`
4. Si `result=aplicado` en `stage=learning_final`, el aprendizaje ocurrió.
5. Si además aparece `mobile_failed_fallback_persistent`, validar evidencia en notificación persistente con el mismo `trace_id`.
