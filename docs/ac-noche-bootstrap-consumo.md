# Bootstrap nocturno de COOL basado en consumo real

## Objetivo

La automatización `AC - Noche dinámico (OpenWeather) + Presencia estable + Fan Low + Notificaciones` ahora separa dos conceptos distintos:

- `cool_stop_threshold`: umbral térmico de confort usado para apagar `cool`.
- `cool_bootstrap_*`: setpoints temporales usados sólo para conseguir que el condensador realmente arranque cuando el equipo queda en una zona donde sólo ventila.

El objetivo de confort **no cambia**. El bootstrap sólo baja el setpoint de arranque en escalones controlados mientras el compresor todavía no muestra consumo suficiente.

## Telemetría y helpers nuevos

Se agregaron estos helpers persistentes:

- `input_boolean.ac_night_cool_bootstrap_in_progress`: evita reentradas y reintentos simultáneos.
- `input_number.ac_night_cool_last_effective_setpoint`: guarda el último setpoint nocturno que sí logró encender el condensador.
- `input_datetime.ac_night_cool_last_effective_ts`: timestamp del setpoint efectivo guardado.
- `input_datetime.ac_night_cool_last_bootstrap_ts`: timestamp del último inicio de bootstrap nocturno.

Además, la automatización actualiza la telemetría existente:

- `input_number.ac_last_auto_setpoint`
- `input_text.ac_last_auto_branch`
- `input_text.ac_last_auto_action`
- `input_text.ac_last_change_origin`
- `input_text.ac_last_auto_mode`
- `input_text.ac_last_auto_fan`

También deja trazas con `logbook.log` y la notificación móvil cuando el bootstrap tiene éxito, aborta o agota el número de escalones.

## Detección de condensador

En el repositorio **no se encontró** una entidad de potencia/energía ya declarada para el aire acondicionado. Las búsquedas por `consumo`, `energia`, `energy`, `power`, `potencia` y `kwh` sólo devolvieron `input_number.tarifa_kwh_usd` y no aparecieron sensores de consumo del AC.

Por eso la automatización quedó parametrizada con:

- `ac_power_entity: sensor.ac_power`
- `ac_power_condenser_on_threshold: 250`
- `ac_power_fan_only_max: 120`

Antes de depender operativamente del bootstrap, hay que reemplazar `sensor.ac_power` por la entidad real de potencia del equipo en tu instalación y ajustar los umbrales según la telemetría histórica.

### Criterio operativo sugerido

- `fan_only` debería quedar por debajo de `ac_power_fan_only_max`.
- `condensador encendido` debería detectarse cuando la potencia supere `ac_power_condenser_on_threshold` después de la espera inicial de 5 minutos o en las verificaciones posteriores de 1 minuto.

## Reglas de aprendizaje / memoria

El bootstrap reutiliza el helper `input_number.ac_night_cool_last_effective_setpoint` como memoria suave:

- si el último valor efectivo tiene menos de `72` horas, se mezcla con el setpoint base en una proporción `60/40`;
- si ya expiró, se vuelve al cálculo base de la noche;
- la automatización principal diurna y sus sesgos `ac_bias_cool_on`, `ac_bias_cool_off` y `ac_bias_cool_setpoint` no se modifican desde esta lógica nocturna.

## Protecciones contra microciclos

- No inicia bootstrap si el AC se apagó hace menos de `8` minutos.
- No reentra si `input_boolean.ac_night_cool_bootstrap_in_progress` ya está en `on`.
- Aborta si se pierde presencia.
- Aborta si la temperatura interior ya cayó al `cool_stop_threshold`.
- Limita la búsqueda a `4` reducciones de `0.5 °C` con un mínimo nocturno de `20 °C`.
