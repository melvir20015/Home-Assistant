# Flujo transaccional de apagado COOL

## Objetivo

Este documento describe el flujo contractual y auditable de las ramas COOL que apagan el equipo pasando por `fan_only` antes de ejecutar `off` y enviar la notificación final.

## Ramas cubiertas

- `presence_off`
- `cool_emergency_off`
- `cool_normal_off`

## Orden exacto del flujo

En las tres ramas, el flujo operativo ocurre en este orden lineal y dentro de la misma secuencia que hace el apagado real:

1. **Snapshot inicial de la transacción**  
   La rama construye una sola vez el mensaje final reusable (`cool_cycle_final_message`) con:
   - rama (`cool_cycle_branch`);
   - contrato del ciclo (`cool_cycle_contract_on`, `cool_cycle_contract_off`, `cool_cycle_contract_sensor_off`, `cool_cycle_contract_setpoint_effective`);
   - causa y detalle del apagado;
   - hora exacta (`now().isoformat()`).

2. **Hito `entrada_fan_only`**  
   `logbook.log` justo antes de mandar `climate.set_hvac_mode: fan_only`.

3. **Entrada a `fan_only`**
   - Se ejecuta `climate.set_hvac_mode: fan_only`.
   - Si el equipo lo soporta, se fuerza `fan_mode: Low`.

4. **Espera de secado (`fan_dry_delay`)**
   - Se espera el delay configurado.

5. **Hito `fan_dry_delay_finalizado`**  
   `logbook.log` al terminar `fan_dry_delay`.

6. **Persistencia de auditoría en helpers**
   - `input_datetime.ac_ultimo_apagado`
   - `input_datetime.ac_last_auto_ts`
   - `input_text.ac_last_auto_branch`
   - `input_text.ac_last_auto_action`
   - `input_text.ac_last_change_origin`
   - `input_text.ac_last_auto_mode`
   - `input_text.ac_last_auto_fan`
   - `input_number.ac_last_auto_*`

7. **Orden de apagado final**
   - Se ejecuta `climate.set_hvac_mode: 'off'`.

8. **Hito `off_enviado`**  
   `logbook.log` inmediatamente después del `off`.

9. **Hito `mensaje_preparado`**  
   `logbook.log` justo antes del push. Este punto prueba que el texto final ya quedó construido dentro de la misma rama.

10. **Push en la misma secuencia lineal**
    - La misma rama ejecuta `notify.mobile_app_samsung_s24`.
    - No depende de automatizaciones externas, helpers temporales ni compuertas separadas para completar el aviso de apagado.

11. **Hito `notify_ejecutado`**  
    `logbook.log` inmediatamente después del `notify`.

12. **Hito `rama_completada`**  
    `logbook.log` final antes del delay de limpieza de `input_boolean.ac_off_por_automatizacion`.

## Qué contiene cada hito

Todos los hitos comparten el mismo mensaje base reusable. Eso permite comparar Logbook y push sin ambigüedad.

Formato lógico del mensaje:

- `Rama=<branch>`
- `Contrato(On=<cool_cycle_contract_on>, Off=<cool_cycle_contract_off>, OffSensor=<cool_cycle_contract_sensor_off>, SP=<cool_cycle_contract_setpoint_effective>)`
- `Causa=<causa real del apagado>`
- `Detalle=<detalle puntual del disparo>`
- `Hora=<timestamp exacto ISO8601>`

## Cómo diagnosticar dónde se rompió el flujo

### Caso 1: se rompió **antes** del `off`

Señales típicas:

- aparece `entrada_fan_only`, pero no aparece `fan_dry_delay_finalizado`; o
- aparece `fan_dry_delay_finalizado`, pero no aparece `off_enviado`.

Interpretación:

- el flujo entró a secado, pero no terminó el delay; o
- terminó el delay, pero no llegó a ejecutar el `climate.set_hvac_mode: 'off'`.

### Caso 2: se rompió **entre** `off` y `notify`

Señales típicas:

- aparece `off_enviado`; pero
- no aparece `mensaje_preparado`, o no aparece `notify_ejecutado`.

Interpretación:

- si falta `mensaje_preparado`, la rama se interrumpió antes de construir/reusar el mensaje final;
- si aparece `mensaje_preparado` pero falta `notify_ejecutado`, la interrupción ocurrió en el tramo exacto entre preparar el mensaje y ejecutar el servicio de notificación.

### Caso 3: se rompió **después** del `notify`

Señales típicas:

- aparece `notify_ejecutado`; pero
- no aparece `rama_completada`.

Interpretación:

- la lógica alcanzó a ejecutar `notify.mobile_app_samsung_s24`, pero la rama no terminó completamente su secuencia posterior.

### Caso 4: el Logbook muestra el mensaje pero el móvil no recibe push

Señales típicas:

- aparece `mensaje_preparado` con el texto esperado;
- aparece `notify_ejecutado`; y
- el contenido coincide con el push esperado;
- pero el teléfono no muestra la notificación.

Interpretación:

- el problema ya no está en la lógica del ciclo ni en la construcción del mensaje;
- el fallo está aguas abajo del servicio `notify.mobile_app_samsung_s24` (app móvil, permisos, conectividad o entrega del proveedor).

## Resultado esperado en auditoría

Con estos hitos, cualquier revisión futura puede reconstruir el flujo exacto `fan_only -> fan_dry_delay -> off -> preparar mensaje -> notify -> rama completada` y ubicar con precisión si el problema ocurrió antes del `off`, entre `off` y `notify`, o después del `notify`.
