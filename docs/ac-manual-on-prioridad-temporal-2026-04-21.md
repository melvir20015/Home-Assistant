# Contrato de prioridad temporal Manual ON (2026-04-21)

## Objetivo
Evitar que ramas automáticas reviertan un encendido manual reciente (`cool -> fan_only/off`) durante la consolidación transaccional del evento Manual ON.

## Ventana de protección
- Se define sesión manual activa en `input_text.ac_dda_manual_on_active_session`.
- TTL operativo de protección: **110 segundos**.
- Formato mínimo de sesión: `trace_id`, `signature`, `status`, `branch`, `started_ts`.
- Estados protegidos: `detected`, `pending`, `captured` mientras el TTL siga vigente.

## Reglas de exclusión para ramas AUTO
Aplica sobre ramas que fuerzan reducción de modo (`cool_normal_off`, `cool_emergency_off`):

1. Antes de ejecutar `fan_only/off`, auditar:
   - `trace_id`
   - `origin`
   - `branch`
   - `blocked_by_manual_on_session`
   - `minutes_since_manual_on`
2. Si `manual_on_session_protected=true`, **bloquear transición** y registrar:
   - `hito=blocked_by_manual_on_session`
   - motivo técnico para auditoría.

## Carrera `off -> fan_only -> cool`
- Durante consolidación Manual ON se permite un puente único cuando el estado queda en `fan_only`.
- Si sesión activa + TTL vigente + mismo `trace_id`:
  - ejecutar `bridge_attempt=1` a `cool`,
  - esperar 12s y continuar consolidación.
- Mientras la sesión siga en TTL, no se descarta por `fan_only_bridge_fuera_ventana`.

## Secuencia obligatoria de notificaciones por sesión
1. `Resultado=pendiente` (exactamente una vez por sesión).
2. Cierre único con mismo `Trace`:
   - `Resultado=capturado`, o
   - `Resultado=ignorado`, o
   - `Resultado=error_controlado`.
3. Duplicados se suprimen por firma/contexto de sesión.

## Contrato de Learning ON
- Debe correlacionar por `trace_id` y sesión activa/capturada del mismo evento.
- Si la sesión expira y no hay `cool` estable:
  - cerrar con `Resultado=ignorado`
  - razón explícita `manual_on_session_expired_without_cool`.

## Observabilidad mínima obligatoria
Toda transición real o bloqueada hacia `fan_only/off` debe registrar:
- `trace_id`
- `origin`
- `branch`
- `blocked_by_manual_on_session`
- `minutes_since_manual_on`

Esto permite identificar con precisión qué rama intentó quitar `cool`.
