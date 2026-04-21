# Fix HA schema `queued.max >= 2` en Manual ON (2026-04-21)

## Incidente
Al recargar automatizaciones, Home Assistant marcaba dos reparaciones de configuración:

- `No se pudo configurar la automatización AC - Learning - Manual ON feedback`
- `No se pudo configurar la automatización AC - Manual ON guard + presencia temporal`

## Causa raíz
Ambas automatizaciones estaban en `mode: queued` pero con `max: 1`.

En Home Assistant, el esquema válido para cola requiere **`max >= 2`** cuando `mode: queued`. Con `max: 1`, la automatización falla al cargar por validación de esquema.

## Cambio aplicado
Se actualizaron ambas automatizaciones a:

- `mode: queued`
- `max: 2`

Automatizaciones ajustadas:

1. `AC - Learning - Manual ON feedback`
2. `AC - Manual ON guard + presencia temporal`

## Coherencia funcional guard + learning
Se mantuvo `queued` en ambas para preservar el contrato transaccional vigente:

- Evitar reinicios de corrida a mitad de consolidación/manual snapshot.
- Evitar abortar secuencias `pendiente -> capturado -> resultado final` por un trigger nuevo.
- Reducir colisión de trazas: con cola corta (`max: 2`) entra como máximo una corrida adicional en espera mientras la sesión activa resuelve cierre.

## Regla preventiva
Cuando una automatización use `mode: queued`, nunca configurar `max: 1`.

Checklist mínimo antes de aplicar cambios:

1. Validar `mode` y `max` en cada automatización editada.
2. Si `mode: queued`, exigir `max >= 2`.
3. Si se necesita ejecución estrictamente única, mantener `queued` con `max: 2` y resolver unicidad en lógica (session/trace locks), no por `max: 1`.
