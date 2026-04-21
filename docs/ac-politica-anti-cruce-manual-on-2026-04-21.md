# Política anti-cruce Manual ON (2026-04-21)

## Objetivo
Evitar mezcla de corridas entre `AC - Manual ON guard + presencia temporal` y `AC - Learning - Manual ON feedback` cuando un mismo encendido manual dispara más de un trigger técnico.

## Regla principal
**1 evento manual ON válido = 1 `trace_id` único = 1 secuencia `pendiente -> capturado -> learning`.**

## Cambios de contrato

1. **Fuente única de `trace_id` por evento**
   - Se prioriza `trigger.to_state.context.id` como `trace_id` base del evento manual ON.
   - Si el contexto no está disponible, se usa fallback generado.
   - Ese mismo `trace_id` se reutiliza en:
     - notificación `Resultado=pendiente`,
     - persistencia de snapshot/trace,
     - notificación de cierre en guard (`capturado` o `error_controlado`),
     - cierre de Learning ON.

2. **Deduplicación fuerte por firma de evento**
   - Firma corta: `ctx=<context.id>` con ventana corta (`TTL=8s`).
   - Si existe pendiente activo para la misma firma, el disparo se descarta sin abrir nuevo evento lógico.
   - En descarte duplicado se conserva el `trace_id` pendiente previo para diagnóstico.

3. **Preservación de corrida original**
   - `AC - Manual ON guard + presencia temporal` y `AC - Learning - Manual ON feedback` pasan a `mode: queued` con `max: 10`.
   - Se evita que una corrida nueva reemplace otra en curso durante consolidación/persistencia.

4. **Validación explícita anti-cruce en Learning ON**
   - Learning exige consistencia de traza entre:
     - `input_text.ac_dda_last_manual_on_trace_confirmed`,
     - `input_text.ac_dda_last_manual_on_snapshot`,
     - `input_text.ac_dda_last_manual_event_type`.
   - Si hay desalineación, se clasifica `trace_mismatch_cross_run`.
   - En `trace_mismatch_cross_run` no se sobrescribe la firma de evento ya vigente.

5. **Diagnóstico en notificación final**
   - Notificación de Learning ON ahora expone:
     - `RunTrace=<trace_actual_snapshot>`
     - `PendingTrace=<trace_confirmado_origen>`
   - Permite identificar en móvil si hubo mezcla de corridas.

## Resultado esperado
Con esta política, cada Manual ON válido mantiene una sola identidad transaccional de punta a punta y no debe contaminar corridas vecinas, incluso cuando existan triggers técnicos múltiples cercanos en el tiempo.
