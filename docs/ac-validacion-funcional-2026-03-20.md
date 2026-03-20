# Validación funcional del AC aprendido — 2026-03-20

## Alcance

Se ejecutó una validación **funcional estática y reproducible sobre la configuración actual** del AC aprendido. En este repositorio no hay una instancia viva de Home Assistant con histórico/traces exportados, así que la validación se realizó sobre la lógica real de `automations.yaml` y la declaración de helpers asociados.

La ejecución reproducible quedó automatizada en:

```bash
python3 tools/validate_ac_logic.py
```

Resultado actual: **17 chequeos superados** tras ajustar el validador para reflejar correctamente que la push de `manual_on` sólo se ejecuta dentro de la rama `presence_gap`, mientras que fuera de esa rama únicamente queda telemetría/logbook.

## Evidencia base revisada

- Automatización principal: `AC - Día dinámico aprendido (principal)`.
- Guard de apagado manual: `AC - Manual OFF guard + pausa 5 min`.
- Guard de encendido manual: `AC - Manual ON guard + presencia temporal`.
- Aprendizaje por `manual_off`: `AC - Learning - Manual OFF feedback`.
- Aprendizaje por `manual_on`: `AC - Learning - Manual ON feedback`.
- Helpers: `input_select.ac_ultimo_modo_no_fan`, `input_boolean.ac_on_por_automatizacion`, `input_boolean.ac_off_por_automatizacion`, `input_datetime.ac_manual_presence_until` e `input_text` de telemetría.

## Método de validación usado

La validación quedó dividida en dos capas:

1. **Chequeo automatizado reproducible** con `python3 tools/validate_ac_logic.py`, que inspecciona contratos críticos de `automations.yaml` y de los helpers.
2. **Lectura funcional guiada** de las ramas relevantes para reconstruir, por escenario, estados previos, condiciones, acciones, trazas esperables, notificaciones y sesgos que cambian.

Cuando el repositorio no trae una exportación runtime (traces JSON, history o snapshots de estados), este enfoque permite dejar una base verificable sin inventar resultados observados. En consecuencia, este documento diferencia siempre entre:

- **validado por lógica estática reproducible**, y
- **pendiente de confirmación runtime**.

## Resultado por escenario

### 1) Encendido manual desde Home Assistant con ausencia detectada

**Validado: sí, según lógica actual.**

#### Estado/condición relevante antes
- `presence_effective` se calcula como `phone_home OR presence_sensor_strict OR presence_temp_from_manual`.
- Si ninguna fuente de presencia está activa, `auto_on_blocked_by_presence = true`.

#### Acción observada por la lógica
- El guard manual detecta una transición `off -> cool/heat/fan_only`, marca `manual_on`, espera 15 segundos y consolida el modo final.

#### Resultado verificado
- Se detecta `manual_on`.
- Si el modo final es `cool` o `heat` y no hay presencia efectiva, clasifica como `manual_on_due_to_presence_gap_*`.
- Se extiende `input_datetime.ac_manual_presence_until` por 1 hora.
- La notificación asociada queda confinada a esa rama y no hay evidencia de spam repetitivo dentro del mismo flujo.
- El helper `input_select.ac_ultimo_modo_no_fan` conserva `cool` o `heat` y no se fuerza inmediatamente a `fan_only` ni `off` desde el guard manual.

#### Trazas/notificaciones esperables
- Logbook: `manual_on_detected`.
- Logbook: `manual_on_classified_presence_gap`.
- Notificación móvil: `AC aprendió: ON manual por ausencia | presencia temporal activada`.

### 2) Encendido manual desde Home Assistant con presencia real pero sin AUTO ON por fórmula

**Validado: sí, según lógica actual.**

#### Resultado verificado
- Cuando `presence_effective = true`, la clasificación de brecha por presencia deja de aplicar.
- Si el modo final es `cool` y `tin < cool_on`, queda como `manual_on_due_to_comfort_gap_cool`.
- Si el modo final es `heat` y no se cumplía la condición de encendido automático de calefacción, queda como `manual_on_due_to_comfort_gap_heat`.
- No se degrada erróneamente a `manual_on_due_to_presence_gap`.

#### Trazas/notificaciones esperables
- Logbook: `manual_on_detected`.
- Sin notificación especial de presencia, porque esa notificación sólo existe para la rama de brecha de presencia.

### 3) Apagado manual después de AUTO ON en cool

**Validado: sí, según lógica actual.**

#### Resultado verificado
- Se detecta `manual_off` y se registra `input_datetime.ac_last_manual_off_ts`.
- La automatización principal aplica una pausa anti-rebote de 5 minutos mediante `manual_off_hold_minutes: 5`.
- El aprendizaje válido exige: `last_change_origin = manual_off`, `last_auto_action = auto_on`, modo automático previo `cool/heat` y ventana de feedback vigente.
- Para `cool`, el aprendizaje perceptible sube `ac_bias_cool_on` y `ac_bias_cool_off` en `+0.25`; además sube `ac_bias_cool_setpoint` en `+0.5` si el feedback fue rápido.
- La notificación de aprendizaje válido de `cool` aparece una sola vez en la rama válida.
- Consecuencia funcional: el próximo `AUTO ON COOL` exige una temperatura interior mayor porque el sesgo `ac_bias_cool_on` aumenta.

#### Trazas/notificaciones esperables
- Logbook: `AC Manual OFF audit`.
- Logbook: `AC - Learning - Manual OFF feedback` con `aprendizaje válido aplicado`.
- Notificación móvil: `AC aprendió: OFF manual tras AUTO COOL | +0.25 on/off ...`.

### 4) AUTO OFF por ausencia 30m

**Validado parcialmente por análisis de lógica y helpers.**

#### Resultado verificado
- La condición `presence_away_30m` existe en la automatización principal y representa ausencia efectiva sostenida.
- El guard de `manual_off` aborta explícitamente si `input_boolean.ac_off_por_automatizacion` está en `on`, evitando contaminar el aprendizaje manual durante un AUTO OFF.
- La telemetría distingue el origen manual (`manual_off`) del automático mediante flags dedicadas y `input_text.ac_last_change_origin`.
- También existe una automatización de autocorrección para evitar que `ac_on_por_automatizacion` o `ac_off_por_automatizacion` queden pegadas fuera de ventana.

#### Pendiente para validación 100% runtime
- En este repositorio no hay una exportación de traces reales para confirmar el instante exacto de encendido/apagado de la bandera durante un AUTO OFF completo de 30 minutos. La lógica está protegida, pero la evidencia disponible aquí es estática.

### 5) Flujo `emergency_cool`

**Validado parcialmente por análisis de lógica y helper.**

#### Resultado verificado
- `emergency_cool` existe como estado válido del helper semántico.
- El latch se modela explícitamente con `emergency_latched: last_mode_no_fan == 'emergency_cool'`.
- La persistencia de `emergency_cool` al helper ocurre sólo en la rama documentada como enfriamiento de emergencia.
- Existe autocorrección de estados inválidos restaurados del helper, por lo que no debería quedar un valor legacy fuera de `off/cool/heat/emergency_cool`.

#### Pendiente para validación 100% runtime
- No hay trace viva adjunta en el repo para demostrar con una corrida real que una condición `cool` normal nunca queda dominada en exceso por `emergency_cool` ni para observar exactamente la salida del latch con sensores reales.

### 6) Integridad de helpers

**Validado: sí para declaración/configuración; parcial para comportamiento runtime continuo.**

#### Confirmado
- `input_select.ac_ultimo_modo_no_fan` sólo admite `off`, `cool`, `heat`, `emergency_cool`.
- Existen `input_boolean.ac_on_por_automatizacion` y `input_boolean.ac_off_por_automatizacion`.
- Existe `input_datetime.ac_manual_presence_until`.
- Los `input_text` de telemetría clave existen y la lógica los actualiza durante detección manual y aprendizaje.
- Existe una automatización de saneamiento por si los flags automáticos quedan activos demasiado tiempo.

#### Pendiente 100% runtime
- Confirmar con traces/export de estados que ambos booleans quedan siempre en `off` fuera de ventana de acción, no sólo por diseño sino por observación histórica real.

## Cambios reales en sesgos de aprendizaje observables desde la lógica

### Si hay `manual_off` válido tras `AUTO ON COOL`
- `ac_bias_cool_on`: sube `+0.25`.
- `ac_bias_cool_off`: sube `+0.25`.
- `ac_bias_cool_setpoint`: sube `+0.5` si el feedback fue rápido.
- Efecto esperado: el próximo encendido automático en frío requiere más temperatura interior y el sistema se vuelve menos agresivo al enfriar.

### Si hay `manual_on` válido tras `AUTO OFF COOL`
- `ac_bias_cool_on`: baja según `step_main`.
- `ac_bias_cool_off`: baja según `step_main`.
- `ac_bias_cool_setpoint`: baja `0.5` si el feedback fue rápido.
- Efecto esperado: el próximo AUTO ON COOL ocurre antes o con mayor tendencia a enfriar.

## Conclusión operativa

La corrección actual **sí cubre los escenarios críticos de detección manual, brecha de presencia, brecha de confort, pausa corta tras apagado manual y aprendizaje válido** desde el punto de vista de la lógica configurada.

Lo que **todavía no puede declararse verificado al 100% en runtime desde este repositorio** es la evidencia histórica de trazas reales de Home Assistant para:
- el ciclo completo de `AUTO OFF por ausencia 30m`,
- la salida exacta del latch de `emergency_cool`,
- y la limpieza efectiva de flags en cada ejecución real.

## Próximo paso recomendado para cerrar la brecha runtime

Ejecutar estos mismos seis escenarios en una instancia viva de Home Assistant y exportar:
1. trace JSON de las automatizaciones involucradas,
2. timeline de estados de helpers,
3. logbook relacionado con `climate.0200009211c7_climate`,
4. y capturas de notificaciones móviles.

Con ese material, esta validación puede elevarse de **funcional estática reproducible** a **validación runtime observada** sin reinterpretar síntomas aislados.

## 7) Validación del flujo de snapshot JSON

**Validado: sí, a nivel documental y de reproducibilidad.**

#### Confirmación documental
- `docs/ac-produccion-manual-auto.md` ya define el contrato funcional de los eventos manuales/automáticos y qué helpers deben revisarse.
- `docs/ac-aprendido-contexto.md` ya enumera explícitamente los helpers, estados y automatizaciones que una revisión futura debe correlacionar.
- Se añadió `docs/ac-snapshot-json-debug.md` para dejar un procedimiento concreto de snapshot JSON reutilizable por otra persona o por otra IA.

#### Qué debe contener el snapshot para repetir el análisis
- Estado actual de `climate.0200009211c7_climate`.
- Helpers críticos: `input_select.ac_ultimo_modo_no_fan`, `input_boolean.ac_on_por_automatizacion`, `input_boolean.ac_off_por_automatizacion`, `input_datetime.ac_manual_presence_until`, `input_datetime.ac_last_auto_ts`, `input_datetime.ac_last_manual_on_ts`, `input_datetime.ac_last_manual_off_ts`.
- Telemetría `input_text.ac_last_auto_*`, `input_text.ac_last_manual_*`, `input_number.ac_bias_*`, `input_number.ac_last_manual_*`.
- Entidades de presencia (`person`, `device_tracker`, `binary_sensor`), clima exterior y cualquier export de traces de las automatizaciones del AC.

#### Reproducibilidad mínima prometida
Con estos tres insumos:
1. este documento funcional,
2. un snapshot JSON con los campos anteriores, y
3. `automations.yaml` + helpers declarados,

otra persona o IA puede reconstruir:
- si el origen fue manual o automático;
- por qué un `manual_on` cayó en `presence_gap` o `comfort_gap`;
- si un `manual_off` era aprendizaje válido;
- qué sesgos cambiaron realmente;
- y si los flags temporales quedaron consistentes o pegados.

#### Qué datos del snapshot explican cada comportamiento
- **Escenarios 1 y 2 (`manual_on`)**: `ac_last_change_origin`, `ac_last_manual_event_type`, `ac_manual_presence_until`, `ac_last_manual_final_mode`, sensores de presencia y `ac_last_auto_*`.
- **Escenario 3 (`manual_off` tras `AUTO ON`)**: `ac_last_change_origin`, `ac_last_manual_learning_type`, `ac_last_auto_action`, `ac_last_auto_mode`, `ac_last_auto_ts`, `ac_bias_cool_on`, `ac_bias_cool_off`, `ac_bias_cool_setpoint`.
- **Escenario 4 (`AUTO OFF` por ausencia)**: `ac_off_por_automatizacion`, `ac_last_auto_action`, `ac_last_auto_branch`, `ac_last_change_origin`, `presence_effective` derivable desde sensores exportados.
- **Escenario 5 (`emergency_cool`)**: `ac_ultimo_modo_no_fan`, `ac_last_auto_branch`, `ac_last_auto_mode`, temperatura interior/exterior y cualquier trace que muestre entrada/salida del latch.
- **Escenario 6 (integridad de helpers)**: snapshot de `input_select`, `input_boolean`, `input_datetime`, `input_text` e historial/traces si se quiere cerrar confirmación runtime.
