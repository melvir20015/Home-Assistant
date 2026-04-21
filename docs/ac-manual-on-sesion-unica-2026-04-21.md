# AC Manual ON — política de sesión única por encendido real (2026-04-21)

## Objetivo
Consolidar el flujo de `AC - Manual ON guard + presencia temporal` y `AC - Learning - Manual ON feedback` bajo la regla:

**1 encendido manual real = 1 sesión = 1 trace_id = 1 cadena de notificaciones sin duplicados.**

## Política aplicada

1. Se introduce sesión activa en `input_text.ac_dda_manual_on_active_session` con formato:
   - `trace_id=<id>`
   - `signature=<firma_corta>`
   - `status=detected|pending|captured|ignorado|error_controlado`
   - `started_ts=<YYYY-MM-DD HH:MM:SS>`
2. Detecciones con firma equivalente en ventana corta reutilizan sesión activa y **no crean nuevo `trace_id`**.
3. `Resultado=pendiente` pasa a ser idempotente por sesión:
   - si la sesión ya está en `status=pending`, se suprime reenvío;
   - se registra `duplicate_pending_suppressed`.
4. El gate funcional para disparar `input_datetime.ac_dda_last_manual_on_ts` queda en `stage2 && stage3` (snapshot + trace).
   - `stage1` se mantiene sólo como diagnóstico (`Stage1Diag`).
5. Concurrencia en cola controlada (`mode: queued`, `max: 2`) para cumplir esquema de Home Assistant (`queued.max >= 2`) y evitar reinicios/aborto de sesión.
6. `fan_only_bridge_fuera_ventana` sólo se evalúa para la misma sesión activa; corridas secundarias quedan bloqueadas por sesión activa ajena.
7. Learning ON exige correlación estricta con sesión activa (`active_session_trace_id == snapshot_trace_id == trace_confirmed`).
   - Si no coincide: `trace_mismatch_cross_run`.
   - No aplica ni cierra sesión ajena.
8. Cierre obligatorio:
   - Toda sesión que emitió `pendiente` termina en `capturado`, `ignorado` o `error_controlado`.
   - Al cierre terminal se limpia `input_text.ac_dda_manual_on_active_session`.

## Secuencia válida (ejemplo)

1. Trigger manual ON válido.
2. Guard crea sesión `status=detected`.
3. Guard emite `Resultado=pendiente` y actualiza sesión a `status=pending`.
4. Tras consolidación y verificación snapshot+trace, guard marca `status=captured` y dispara `input_datetime.ac_dda_last_manual_on_ts`.
5. Learning ON correlaciona `trace_id` con snapshot + sesión activa.
6. Learning ON emite resultado terminal (`aplicado` o `ignorado` o `error_controlado`) y limpia sesión activa.

## Ejemplo de supresión de duplicado

1. Llega segundo trigger con misma firma corta dentro de TTL.
2. Existe sesión activa en `status=pending` con misma firma.
3. Guard registra `duplicate_pending_suppressed`.
4. No se reenvía notificación `Resultado=pendiente`.
5. No se crea nuevo `trace_id`; continúa sólo la sesión principal.
