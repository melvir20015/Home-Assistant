# Rampa térmica nocturna de COOL y aprendizaje contextual

> Nota: este archivo conserva el nombre histórico `ac-noche-bootstrap-consumo.md`
> sólo para no romper referencias existentes. Su contenido ya no describe un
> bootstrap por consumo ni validación de condensador.

## Objetivo

La automatización `AC - Noche dinámico (OpenWeather) + Presencia estable + Fan Low + Notificaciones`
mantiene la banda de control nocturna con dos umbrales:

- `cool_on`: temperatura promedio que habilita el encendido de `cool`.
- `cool_off`: temperatura promedio que dispara el apagado por confort.

Cuando la rama nocturna entra en `cool`, el setpoint inicial normal usa contrato
entero fijo: `floor(cool_off_dinamico - 1.5)`, con límite inferior operativo en
`cool_ramp_min_setpoint`.

## Secuencia de rampa térmica

Para el contexto normal (`tout >= 17 °C`), la secuencia quedó así:

1. Enciende `cool` con fan `Low`.
2. Aplica el setpoint inicial contractual entero `floor(cool_off_dinamico - 1.5)`.
   - Ejemplos contractuales:
     - `23.3 -> 21`
     - `23.5 -> 22`
3. Espera `30` minutos (`cool_ramp_initial_wait_min`).
4. En cada iteración relee estado vivo: temperatura interior promedio actual,
   presencia efectiva actual, modo HVAC vigente, temperatura del sensor local de
   corte y razón de apagado aplicable en ese instante.
5. No se realizan ajustes intra-ciclo de setpoint (la reducción por `cool_night_ramp_step`
   quedó desactivada para mantener “setpoint fijo contractual” durante todo el loop).
6. Si la razón de apagado vigente pasa a `Promedio` o al sensor local habilitado,
   la rampa se detiene y el apagado se deja a la rama normal de confort, sin nuevos
   ajustes de setpoint.

En contexto de emergencia por exterior frío (`tout < 17 °C`) se conserva el setpoint
de emergencia existente (`cool_setpoint_emerg`), pero la telemetría y trazas también
usan la nueva semántica de rampa.

## Aprendizaje del último setpoint útil

Los helpers persistentes se reutilizan con un significado nuevo:

- `input_number.ac_night_cool_last_effective_setpoint`: guarda el último setpoint
  aplicado justo antes de que el ciclo llegue al apagado por confort.
- `input_datetime.ac_night_cool_last_effective_ts`: timestamp de ese último setpoint útil.

Ese valor ya no significa “setpoint que logró arrancar condensador”, sino
“último setpoint útil del ciclo nocturno antes del apagado confortable”.

La automatización también calcula una referencia suave (`cool_last_useful_setpoint`)
mezclando:

- `70%` del setpoint base actual (`cool_off - 0.5 °C`), y
- `30%` del último setpoint útil recordado,

si la memoria tiene menos de `72` horas.

Hoy esa referencia se usa como aprendizaje contextual y telemetría; el arranque
normal sigue partiendo explícitamente de `cool_off - 0.5 °C`.

## Regla para apagado por sensor más frío

El apagado por el sensor más frío se mantiene sólo cuando ambos sensores están
suficientemente alineados:

- `sensor_temp_delta = |t1 - t2|`
- `cool_sensor_off_enabled = sensor_temp_delta <= 1.0 °C`

Entonces:

- si `tin <= cool_off`, el motivo de apagado sigue siendo `Promedio`;
- si `tin > cool_off` pero el sensor configurado para apagado local ya cayó a su
  umbral **y** `sensor_temp_delta <= 1.0 °C`, se permite apagar por ese sensor;
- si el delta supera `1.0 °C`, se ignora el criterio del sensor más frío y sólo
  manda el promedio.

## Trazas, helpers y mensajes

La rama nocturna actualiza:

- `input_text.ac_last_auto_branch`
- `input_text.ac_last_auto_action`
- `input_number.ac_last_auto_setpoint`
- `input_datetime.ac_last_auto_ts`
- `input_datetime.ac_night_cool_last_bootstrap_ts`

Aunque algunos helpers conservan nombres legacy (`*_bootstrap_*`) por compatibilidad,
las trazas y mensajes ahora reflejan la nueva semántica:

- `cool_night_ramp_start`
- `cool_night_setpoint_fijo_contractual`
- `cool_night_ramp_ready_for_comfort_off`
- `cool_night_ramp_hold`
- `cool_night_ramp_presence_exit`
- `cool_night_ramp_hvac_exit`
- `cool_night_ramp_window_exit`
- `cool_night_ramp_timeout_exit`

La notificación móvil de arranque también cambió para describir:

- inicio con contrato entero `floor(cool_off_dinamico - 1.5)`;
- espera inicial de `30` minutos;
- monitoreo cada `10` minutos sin cambios de setpoint intra-ciclo;
- aprendizaje del último setpoint útil.

## Protecciones

- No inicia un nuevo ciclo si el AC se apagó hace menos de `8` minutos.
- No reentra si `input_boolean.ac_night_cool_bootstrap_in_progress` ya está en `on`.
- Aunque la rampa sigue siendo un loop persistente dentro de una automatización en
  `mode: single`, las decisiones críticas ya no usan snapshots del bloque inicial:
  cada paso relee sensores/estado con `states(...)` y helpers derivados locales del
  propio `repeat`.
- Se detiene si se pierde presencia.
- Se detiene si el equipo sale de `cool`.
- Se detiene en cuanto la razón de apagado vigente indique `Promedio` o el sensor
  local habilitado, usando la `tin` real de esa iteración.
- Se detiene explícitamente si el loop sale de la ventana `21:00–07:00`.
- Se detiene por timeout de seguridad tras `180` minutos para evitar ejecuciones
  eternas ante estados inconsistentes.

## Recuperación automática de flag de rampa atascado

Se agregó una compuerta de sanidad para limpiar automáticamente
`input_boolean.ac_night_cool_bootstrap_in_progress` cuando queda pegado en `on`
por reinicios o errores, pero el equipo **ya no está en `cool`**.

La limpieza se ejecuta al inicio de la evaluación nocturna cuando se cumple:

- `night_ramp_in_progress == true`
- `cur_mode != 'cool'`
- `minutes_since_last_off >= night_ramp_stale_reset_min` (umbral configurable,
  por defecto `20` minutos)

Acciones de recuperación:

- apaga `input_boolean.ac_night_cool_bootstrap_in_progress`;
- registra `input_text.ac_last_auto_branch = cool_night_ramp_stale_flag_reset`;
- registra `input_text.ac_last_auto_action = ramp_flag_auto_reset`;
- deja evidencia en `logbook.log` con `cur_mode`, minutos desde último apagado,
  umbral aplicado y timestamp.

Esta recuperación **no compromete** la protección anti-ciclo-corto:
`cool_ramp_short_cycle_guard_min` se mantiene intacto y sigue validándose al
momento de permitir un nuevo encendido en `cool`. Es decir, esta rama sólo limpia
estado inválido; no fuerza encendidos.

Ejemplo de traza esperada:

- `cool_night_ramp_stale_flag_reset | cur_mode=off | minutes_since_last_off=34.2 | threshold=20 | ts=2026-03-30 02:15:00`
