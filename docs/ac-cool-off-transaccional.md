# Flujo transaccional de apagado COOL

## Objetivo

Este documento describe el flujo contractual y auditable de las ramas COOL que apagan el equipo pasando por `fan_only` antes de ejecutar `off` y enviar la notificación final.

## Ramas cubiertas

- `presence_off`
- `cool_emergency_off`
- `cool_normal_off`

## Orden exacto del flujo

En las tres ramas, el flujo operativo ahora debe ocurrir en este orden:

1. **Snapshot inicial de la transacción**  
   Se construyen variables locales con:
   - snapshot contractual del ciclo (`cool_cycle_contract_*`);
   - causa real del corte;
   - detalle puntual del disparo.

2. **Logbook antes de entrar a `fan_only`**  
   Se registra `cool_off_txn_begin` con:
   - rama (`branch=*`);
   - fase `before_fan_only`;
   - causa real;
   - detalle;
   - snapshot contractual completo.

3. **Entrada a `fan_only`**
   - Se ejecuta `climate.set_hvac_mode: fan_only`.
   - Si el equipo lo soporta, se fuerza `fan_mode: Low`.

4. **Secado (`fan_dry_delay`)**
   - Se espera el delay de secado configurado.

5. **Logbook al terminar el secado**
   - Se registra `cool_off_txn_dry_done` con la misma identidad transaccional.

6. **Persistencia de auditoría en helpers**
   - `input_datetime.ac_ultimo_apagado`
   - `input_datetime.ac_last_auto_ts`
   - `input_text.ac_last_auto_branch`
   - `input_text.ac_last_auto_action`
   - `input_text.ac_last_change_origin`
   - `input_text.ac_last_auto_mode`
   - `input_text.ac_last_auto_fan`
   - `input_number.ac_last_auto_*`

7. **Logbook justo antes de apagar**
   - Se registra `cool_off_txn_before_off` con fase `before_off`.

8. **Apagado real**
   - Se ejecuta `climate.set_hvac_mode: 'off'`.
   - Cuando la rama ya lo hacía, se mantiene la espera defensiva a estado `off`.

9. **Notificación final en la misma rama**
   - La rama que apaga realmente también ejecuta `notify.mobile_app_samsung_s24`.
   - Ya no debe depender de automatizaciones separadas ni helpers temporales para “disparar” el push.

10. **Logbook inmediatamente después del push**
    - Se registra `cool_off_notify_sent` con fase `after_notify`.

## Contrato del mensaje final

La notificación final de apagado debe coincidir con lo que realmente pasó. Por eso el mensaje combina:

- **Snapshot contractual del ciclo**:
  - `cool_cycle_contract_on`
  - `cool_cycle_contract_off`
  - `cool_cycle_contract_sensor_off`
  - `cool_cycle_contract_setpoint_effective`
  - `cool_cycle_contract_bucket`
  - `cool_cycle_contract_reason`

- **Causa real del corte**, según la rama:
  - `meta_alcanzada`
  - `corte_preventivo_t1`
  - `corte_preventivo_t2`
  - `ausencia`
  - `emergencia`

## Criterios por rama

### `cool_normal_off`

- Usa el snapshot contractual del ciclo normal.
- La causa real se clasifica como:
  - `meta_alcanzada`
  - `corte_preventivo_t1`
  - `corte_preventivo_t2`
  - `no_clasificado` como fallback defensivo.

### `presence_off`

- Aunque el disparo es por ausencia, el mensaje también incluye el snapshot contractual vigente para que la salida quede trazable contra el contrato actual.
- La causa real del corte es `ausencia`.

### `cool_emergency_off`

- Conserva el snapshot contractual vigente para auditoría.
- La causa real del corte es `emergencia`.
- El detalle del disparo usa el umbral de salida de emergencia (`emergency_off_avg`) cuando está disponible.

## Resultado esperado en auditoría

Si se revisa Logbook después de un apagado COOL transaccional, deben verse en secuencia:

1. `cool_off_txn_begin`
2. `cool_off_txn_dry_done`
3. `cool_off_txn_before_off`
4. `cool_off_notify_sent`

Con esto, cualquier revisión futura puede reconstruir exactamente el flujo `fan_only -> off -> notify` sin depender de inferencias externas.
