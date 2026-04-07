# Política de fallback para apagado OFF efectivo (2026-04-07)

## Alcance

Aplica a la automatización **`AC - Día dinámico aprendido (principal)`**, específicamente en la rama `ac_dda_branch=cool_normal_off` de `automations.yaml`.

## Problema que resuelve

Se observó el escenario operativo: **"encendió >26 y no apagó en 23"** cuando los helpers del contrato de ciclo (`ac_dda_cool_cycle_contract_*`) estaban incompletos o desactualizados.

La causa principal era el bloqueo duro por `cool_cycle_contract_active`, que impedía evaluar apagado aunque la temperatura ya cumpliera condición térmica de corte.

## Nueva política OFF efectiva

Se introduce resolución robusta de `off_effective` en tiempo de ejecución:

1. **Prioridad 1 (`contract_helper`)**
   - Usar `cool_cycle_contract_off_validated` cuando exista valor válido.
2. **Prioridad 2 (`runtime_recalc`)**
   - Si el helper de ciclo no es válido/no está disponible, usar `cool_off_validated` recalculado en runtime.
3. **Abortar con trazabilidad explícita (`missing`)**
   - Si no hay `off_effective` usable en ninguna fuente, la rama de apagado **no ejecuta OFF a ciegas** y registra logbook de aborto.

## Política de sensor OFF efectivo

Para `t1/t2` se usa `sensor_off_effective`:

- Si la fuente es `contract_helper` y hay `cool_cycle_contract_sensor_off`, se usa ese valor.
- En fallback `runtime_recalc` (o sin sensor helper válido), se recalcula como:
  - `sensor_off_effective = clamp(off_effective - 0.3, 22.8, 24.0)`.

## Condición de apagado resultante

La rama `cool_normal_off` ahora permite apagar cuando exista `off_effective` válido y se cumpla al menos una:

- `tin <= off_effective`, o
- `t1 <= sensor_off_effective`, o
- `t2 <= sensor_off_effective`.

`cool_cycle_contract_active` se mantiene para **auditoría/trazabilidad**, pero ya no bloquea de forma dura la seguridad térmica del apagado.

## Observabilidad añadida (logbook)

Se registran dos eventos clave:

1. **Fallback aplicado**
   - `cool_off_fallback_source=contract_helper|runtime_recalc`
   - Incluye `off_effective`, `sensor_off_effective` y `contract_active_audit`.
2. **Aborto por falta de umbral**
   - `ac_dda_branch=cool_normal_off_abort | reason=missing_off_effective`
   - Incluye valores disponibles de `contract_off`, `runtime_off` y `contract_active_audit`.

## Ejemplos de helpers desactualizados

### Ejemplo A: helper de ciclo vencido/no persistido

- `cool_cycle_contract_off_validated = none`
- `cool_off_validated = 23.1`

Resultado esperado:
- Fuente: `runtime_recalc`
- `off_effective = 23.1`
- Se permite OFF si `tin <= 23.1` o si `t1/t2 <= sensor_off_effective`.

### Ejemplo B: helper con contrato válido

- `cool_cycle_contract_off_validated = 23.3`
- `cool_off_validated = 22.9`

Resultado esperado:
- Fuente: `contract_helper` (prioridad superior)
- `off_effective = 23.3`
- Se conserva continuidad del ciclo contractual.

### Ejemplo C: ambos faltan

- `cool_cycle_contract_off_validated = none`
- `cool_off_validated = none`

Resultado esperado:
- No apagar automáticamente por `cool_normal_off`.
- Registrar aborto explícito para diagnóstico y evitar decisiones térmicas ciegas.
