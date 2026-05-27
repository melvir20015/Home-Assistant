# AC-Matriz 160 — Reconciliación encapsulada para caso manual `off -> fan_only` atascado (2026-05-27)

## Alcance
- Automatización: `ac_matriz_160_learning_manual_v1` en `automations.yaml`.
- Helper dedicado efímero: `input_text.ac_matriz_160_manual_fan_stuck_marker`.
- Sin cambios a la clasificación base `origen_clasificacion`, deduplicación global, ni aprendizaje existente fuera del caso puntual.

## Problema cubierto
Cuando un encendido manual queda en `fan_only` (o `auto`) y no cierra térmicamente dentro de la ventana de consolidación, antes terminaba como `ignorado` con razón `fan_only_sin_cierre_termico_10s` sin reconciliación confirmada.

## Rama nueva (encapsulada)
Se añade una rama puntual para:
1. Detectar exclusivamente `off -> fan_only` manual externo atascado.
2. Registrar marker efímero con `trace_id`, timestamp origen y modo observado.
3. Revalidar guardas de seguridad antes de actuar:
   - horario habilitado,
   - presencia manual override vigente + presencia efectiva,
   - no `manual_hold`,
   - no dedup de reconciliación.
4. Aplicar reconciliación demandante (cool/heat) con setpoint/fan contractuales.
5. Confirmar estado final de modo + setpoint.
6. Notificar solo resultado **confirmado** (sin estado pendiente).
7. Cancelar silenciosamente si falla confirmación o si alguna guarda no permite reconciliar (solo logbook técnico).

## Guardas de no regresión
- No altera la fuente de verdad de origen (`automatico_ac_matriz_160` vs `manual_externo`).
- No cambia la lógica de aprendizaje por columnas ni deltas de COOL/HEAT.
- No modifica el marker transaccional automático existente ni su precedencia.
- Mantiene terminalidad explícita por razones para casos ignorados.

## Matriz de casos
- **Manual puro (off->cool/heat):** sin cambios, flujo actual.
- **Auto puro (marker compatible):** sin cambios, `ignorado` por origen automático.
- **Manual asistido (`off->fan_only` atascado y guardas OK):** reconciliación + confirmación notificada.
- **Cancelado por intervención/guardas:** cancelación técnica en logbook, sin notificación pendiente al usuario.
