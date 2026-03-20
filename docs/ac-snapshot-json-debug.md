# Guía de snapshot JSON para depurar el AC aprendido

## Objetivo

Esta guía define el **snapshot JSON mínimo útil** para analizar el comportamiento del AC aprendido sin depender de memoria oral ni de síntomas aislados. La meta es que otra persona, otro programador o una IA puedan repetir el análisis revisando solamente:

1. este documento,
2. el snapshot JSON exportado,
3. `automations.yaml`, y
4. los archivos de helpers (`input_*`, `timer.yaml`).

## Cuándo conviene generar un snapshot

Genera un snapshot cuando ocurra cualquiera de estos casos:

- `manual_on` que parecía justificarse pero el sistema no había hecho `AUTO ON`;
- `manual_off` después de un `AUTO ON` que debería ajustar aprendizaje;
- `AUTO OFF` por ausencia que parezca contaminar trazas manuales;
- comportamiento dudoso de `emergency_cool`;
- sospecha de helpers pegados o incoherentes.

## Contenido mínimo requerido

### 1. Entidad climate

Incluye el estado completo de:

- `climate.0200009211c7_climate`

Debe contener, como mínimo:

- `state` (`off`, `cool`, `heat`, `fan_only`);
- `attributes.temperature`;
- `attributes.fan_mode`;
- timestamp o contexto del momento exportado.

### 2. Helpers de origen y memoria operativa

Incluye estos helpers con `state`, `last_changed` y `last_updated` si están disponibles:

- `input_select.ac_ultimo_modo_no_fan`
- `input_boolean.ac_on_por_automatizacion`
- `input_boolean.ac_off_por_automatizacion`
- `input_datetime.ac_last_auto_ts`
- `input_datetime.ac_last_manual_on_ts`
- `input_datetime.ac_last_manual_final_ts`
- `input_datetime.ac_last_manual_off_ts`
- `input_datetime.ac_last_manual_feedback_ts`
- `input_datetime.ac_manual_presence_until`

### 3. Telemetría textual

Incluye:

- `input_text.ac_last_auto_branch`
- `input_text.ac_last_auto_action`
- `input_text.ac_last_auto_mode`
- `input_text.ac_last_auto_fan`
- `input_text.ac_last_change_origin`
- `input_text.ac_last_manual_event_type`
- `input_text.ac_last_manual_learning_type`
- `input_text.ac_last_manual_feedback_mode`
- `input_text.ac_last_manual_feedback_fan`
- `input_text.ac_last_manual_final_mode`
- `input_text.ac_last_manual_final_fan`

### 4. Sesgos y métricas numéricas

Incluye:

- `input_number.ac_bias_cool_on`
- `input_number.ac_bias_cool_off`
- `input_number.ac_bias_cool_setpoint`
- `input_number.ac_bias_heat_on`
- `input_number.ac_bias_heat_off`
- `input_number.ac_bias_heat_setpoint`
- `input_number.ac_last_manual_tin`
- `input_number.ac_last_manual_t1`
- `input_number.ac_last_manual_t2`
- `input_number.ac_last_manual_hin`
- `input_number.ac_last_manual_tout`
- `input_number.ac_last_manual_sensor_delta`

### 5. Presencia y contexto ambiental

Incluye:

- `binary_sensor.presencia_movimiento_estable`
- `binary_sensor.presencia_ok_estable`
- `device_tracker.samsung_s24`
- `person.ivan`
- `sensor.lumi_lumi_weather_cuarto_temperatura`
- `sensor.lumi_lumi_weather_coco_temperatura`
- `sensor.lumi_lumi_weather_cuarto_humedad`
- `sensor.lumi_lumi_weather_coco_humedad`
- `weather.openweathermap`

### 6. Trazas recomendadas

Si Home Assistant lo permite, acompaña el snapshot con:

- trace export de `AC - Día dinámico aprendido (principal)`;
- trace export de `AC - Manual ON guard + presencia temporal`;
- trace export de `AC - Manual OFF guard + pausa 5 min`;
- trace export de `AC - Learning - Manual OFF feedback`;
- trace export de `AC - Learning - Manual ON feedback`.

## Formato recomendado

Un solo JSON con esta estructura es suficiente:

```json
{
  "captured_at": "2026-03-20T19:30:00Z",
  "scenario": "manual_off_after_auto_on_cool",
  "entities": {
    "climate.0200009211c7_climate": {"state": "off", "attributes": {}},
    "input_text.ac_last_change_origin": {"state": "manual_off"}
  },
  "traces": {
    "ac_principal": "adjuntar export o referencia",
    "manual_off_guard": "adjuntar export o referencia"
  },
  "notifications": [
    "AC aprendió: OFF manual tras AUTO COOL | +0.25 on/off"
  ],
  "notes": "El usuario apagó manualmente 7 min después del AUTO ON."
}
```

## Cómo usar el snapshot para explicar cada escenario

### Escenario 1: manual_on con ausencia

Confirmar:

- `input_text.ac_last_change_origin = manual_on`;
- `input_text.ac_last_manual_event_type` en `manual_on_due_to_presence_gap*`;
- `input_datetime.ac_manual_presence_until` extendido hacia el futuro;
- `input_boolean.ac_on_por_automatizacion = off` y `input_boolean.ac_off_por_automatizacion = off` al momento del evento;
- sin notificaciones repetidas fuera de la rama de presencia.

### Escenario 2: manual_on con presencia pero sin AUTO ON

Confirmar:

- presencia efectiva derivable del snapshot;
- `input_text.ac_last_manual_event_type` en `manual_on_due_to_comfort_gap_cool` o `manual_on_due_to_comfort_gap_heat`;
- `input_text.ac_last_change_origin = manual_on`;
- `input_datetime.ac_manual_presence_until` sin cambio si no hubo `presence_gap`.

### Escenario 3: manual_off después de AUTO ON cool

Confirmar:

- `input_text.ac_last_change_origin = manual_off`;
- `input_text.ac_last_auto_action = auto_on`;
- `input_text.ac_last_auto_mode = cool`;
- diferencia temporal válida entre `ac_last_auto_ts` y `ac_last_manual_off_ts`;
- aumento real en `ac_bias_cool_on` y `ac_bias_cool_off`, y opcionalmente en `ac_bias_cool_setpoint`.

### Escenario 4: AUTO OFF por ausencia 30m

Confirmar:

- snapshot o trace con `input_boolean.ac_off_por_automatizacion = on` durante la secuencia;
- limpieza posterior del flag;
- `input_text.ac_last_change_origin` no sobrescrito como `manual_off` por ese apagado automático.

### Escenario 5: emergency_cool

Confirmar:

- entrada al latch sólo cuando el branch automático realmente fue de emergencia;
- salida del latch cuando desaparecen sus condiciones;
- `input_select.ac_ultimo_modo_no_fan` regresando a `cool` u `off` según corresponda, nunca a valores inválidos.

### Escenario 6: integridad de helpers

Confirmar:

- `input_select.ac_ultimo_modo_no_fan` siempre en `off`, `cool`, `heat` o `emergency_cool`;
- `input_boolean.ac_on_por_automatizacion` y `input_boolean.ac_off_por_automatizacion` en `off` fuera de ventanas activas;
- telemetría `input_text` poblada y coherente con el último evento observado.

## Criterio de suficiencia

Si una futura revisión tiene:

- este documento,
- `docs/ac-validacion-funcional-2026-03-20.md`,
- `docs/ac-aprendido-contexto.md`,
- el snapshot JSON,
- y `automations.yaml`,

entonces ya debería poder explicar el comportamiento sin rehacer el diagnóstico desde cero.
