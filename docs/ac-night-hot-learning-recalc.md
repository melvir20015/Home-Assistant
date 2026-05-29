# AC Night — aprendizaje manual en caliente

## Contrato operativo

La automatización `AC Night - Aprendizaje manual por columna` aprende únicamente transiciones nocturnas válidas clasificadas como `manual_externo`:

- `off->cool`
- `cool->off`
- `off->heat`
- `heat->off`

Cuando una transición válida modifica el offset de la columna activa, el aprendizaje actualiza `input_text.ac_night_hot_learning_recalc_payload`. Ese helper funciona como disparador interno de `AC Night Matriz Contextual`, por lo que la matriz se reevalúa inmediatamente sin esperar al siguiente ciclo `/5`.

## Payload diagnóstico

El helper de disparo conserva un payload compacto con:

- modo (`cool` o `heat`),
- transición manual,
- columna activa,
- offset anterior,
- offset nuevo,
- delta aplicado,
- trace id,
- timestamp del evento.

Además, los logs incluyen los hitos `night_hot_learning_recalc_requested` y `night_hot_learning_recalc_triggered` para auditar el flujo desde el aprendizaje hasta la reevaluación de matriz.

## Recalculo centralizado

La reevaluación inmediata no duplica decisiones fuera de `AC Night Matriz Contextual`. La matriz vuelve a calcular con sus fórmulas existentes:

- `off_cool`
- `on_cool`
- `sp_cool_target`
- `off_heat`
- `on_heat`
- `sp_heat_target`

Si los umbrales recalculados indican apagado, la matriz puede apagar inmediatamente. Esta ausencia de protección anti-apagado posterior a un encendido manual es intencional para permitir convergencia rápida del aprendizaje: si el usuario vuelve a encender manualmente, el offset seguirá ajustándose.

Si el equipo permanece activo, la matriz reaplica el setpoint objetivo recalculado: `sp_cool_target` en frío y `sp_heat_target` en calor.

## Exclusiones

Las transiciones clasificadas como `automatico_night` por `input_text.ac_night_auto_origin_payload` no aprenden offset y no disparan el recálculo caliente como evento manual.
