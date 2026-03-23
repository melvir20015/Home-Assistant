# Flujo transaccional de apagado COOL

## Objetivo

Este documento describe el flujo contractual y auditable de las ramas COOL que apagan el equipo pasando por `fan_only` antes de ejecutar `off` y enviar la notificación final.

## Ramas cubiertas

- `presence_off`
- `cool_emergency_off`
- `cool_normal_off`

## Orden exacto del flujo

En las tres ramas, el flujo operativo ahora ocurre en este orden lineal y dentro de la misma secuencia que hace el apagado final:

1. **Snapshot inicial de la transacción**  
   Se construyen variables locales con:
   - snapshot contractual del ciclo (`cool_cycle_contract_on`, `cool_cycle_contract_off`, `cool_cycle_contract_sensor_off`, `cool_cycle_contract_setpoint_effective`, `cool_cycle_contract_bucket`, `cool_cycle_contract_reason`);
   - causa real del corte;
   - detalle puntual del disparo.

2. **Marca `fan_only_start`**  
   Se registra un `logbook.log` inmediatamente antes de entrar a `fan_only`.

3. **Entrada a `fan_only`**
   - Se ejecuta `climate.set_hvac_mode: fan_only`.
   - Si el equipo lo soporta, se fuerza `fan_mode: Low`.

4. **Espera de secado (`fan_dry_delay`)**
   - Se espera el delay configurado.

5. **Marca `fan_only_done`**  
   Se registra un `logbook.log` al terminar `fan_dry_delay`.

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

8. **Marca `hvac_off_sent`**  
   Se registra inmediatamente otro `logbook.log` para confirmar que la orden de apagado ya fue enviada.

9. **Push en la misma secuencia lineal**
   - La misma rama ejecuta `notify.mobile_app_samsung_s24`.
   - No depende de automatizaciones externas, helpers temporales ni esperas implícitas para poder notificar.

10. **Marca `push_sent`**  
    Se registra otro `logbook.log` inmediatamente después del `notify`.

## Contrato del mensaje final

La notificación final de apagado combina dos grupos de datos:

### 1) Valores contractuales del ciclo

- `cool_cycle_contract_on`
- `cool_cycle_contract_off`
- `cool_cycle_contract_sensor_off`
- `cool_cycle_contract_setpoint_effective`
- `cool_cycle_contract_bucket`
- `cool_cycle_contract_reason`

### 2) Causa real del apagado

Según la rama, la causa real puede ser:

- `meta_alcanzada`
- `corte_preventivo_t1`
- `corte_preventivo_t2`
- `ausencia`
- `emergencia`

El mensaje push debe ser coherente con ambos planos: lo que el contrato esperaba y lo que efectivamente disparó el corte.

## Cómo leer los hitos del Logbook

### Secuencia esperada sana

Si todo el flujo se ejecutó bien, en Logbook deben verse estos hitos en este orden:

1. `fan_only_start`
2. `fan_only_done`
3. `hvac_off_sent`
4. `push_sent`

### Diagnóstico rápido por tipo de fallo

#### Fallo de lógica

Puede sospecharse un fallo de lógica cuando:

- no aparece `fan_only_start`; o
- aparece `fan_only_start` pero no aparece `fan_only_done`; o
- los campos `branch=`, `cause=` o `detail=` no coinciden con la rama/corte esperado.

Interpretación: la rama no entró donde debía, el delay no terminó, o la condición que eligió la causa real no coincide con el evento observado.

#### Fallo de despliegue

Puede sospecharse un fallo de despliegue cuando:

- el YAML esperado contiene estas marcas, pero en producción siguen apareciendo hitos antiguos; o
- una rama muestra los marcadores nuevos y otra sigue con mensajes previos.

Interpretación: el archivo editado no fue recargado, se desplegó una versión distinta o Home Assistant sigue ejecutando una automatización anterior.

#### Fallo del servicio de notificación

Puede sospecharse un fallo del servicio de notificación cuando:

- aparecen `fan_only_start`, `fan_only_done` y `hvac_off_sent`; y
- también aparece `push_sent`; pero
- el móvil no recibe la notificación.

Interpretación: la lógica sí envió el `notify`, pero el problema está aguas abajo del automation engine: servicio móvil, app, conectividad, permisos o entrega del proveedor.

## Sobre `push_skipped`

La marca `push_skipped` sólo debe existir cuando haya una condición explícita que impida notificar. En el flujo actual no se conserva ninguna condición de bypass: las tres ramas ejecutan el push en línea, así que el caso normal es `push_sent`.

## Resultado esperado en auditoría

Con esta instrumentación, cualquier revisión futura puede reconstruir el flujo exacto `fan_only -> espera -> off -> notify` y determinar si un problema fue de lógica, de despliegue o del servicio de notificación sin depender de automatizaciones externas ni de inferencias implícitas.
