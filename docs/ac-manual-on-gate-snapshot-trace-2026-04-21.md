# AC Manual ON — Ajuste de gate por snapshot+trace (2026-04-21)

## Resumen
Se ajustó la automatización **`AC - Manual ON guard + presencia temporal`** para que la compuerta funcional de disparo hacia Learning ON use únicamente correlación transaccional robusta (**snapshot + trace**) y deje `last_manual_event_type` como señal de telemetría diagnóstica.

## Cambios aplicados

1. **Cambio de gate funcional (`persistence_ready_for_trigger`)**
   - Antes: `stage1 && stage2 && stage3`.
   - Ahora: `stage2 && stage3`.
   - Impacto: `stage1` (event type global) ya no bloquea el trigger; queda solo para observabilidad.

2. **Post-repair readback + recálculo efectivo**
   - Se conserva la reparación controlada cuando snapshot/trace no verifican.
   - Luego se vuelve a leer estado y se recalculan banderas de persistencia para decidir el trigger con el estado real posterior a reparación.

3. **Telemetría explícita de desalineación de `event_type`**
   - Se agregó `persistence_stage_1_diag`:
     - `ok` cuando `stage1` alinea,
     - `telemetria_event_type_desalineada` cuando no alinea.
   - Esto evita tratar como error funcional una desalineación que no rompe correlación snapshot+trace.

4. **Mensajería y trazabilidad de razón de gate**
   - Se agregó `persistence_gate_reason` con dos resultados:
     - `capturado_por_snapshot_trace` (cuando gate funcional abre),
     - `persistencia_pre_learning_incompleta` (cuando gate funcional no abre).
   - Se propaga a logbook y notificación de captura para separar claramente estado funcional vs telemetría.

## Contrato observable esperado (sin corte en segunda notificación)
Con este ajuste, cuando snapshot+trace están correctos, el flujo debe sostener:

1. `Resultado=pendiente`
2. `Resultado=capturado`
3. `AC Learning ON` con resultado terminal (`aplicado`, `ignorado` o `error_controlado`).

Incluso si `last_manual_event_type` queda desalineado, no debe abortarse el disparo cuando `stage2` y `stage3` son válidos.

## Notas de compatibilidad
- `input_text.ac_dda_last_manual_event_type` permanece útil para diagnóstico y auditoría, pero no define por sí solo confirmación transaccional.
- La validación funcional principal queda anclada a:
  - `input_text.ac_dda_last_manual_on_trace_confirmed`
  - `input_text.ac_dda_last_manual_on_snapshot`
