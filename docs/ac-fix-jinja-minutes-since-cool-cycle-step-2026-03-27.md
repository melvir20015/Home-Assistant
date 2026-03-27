# 2026-03-27 — Corrección de sintaxis Jinja en automatización de AC

## Contexto
En la automatización con alias **`AC - Día dinámico aprendido (principal)`** se detectó un error de plantilla Jinja que dejaba la automatización en estado `unavailable`.

## Causa raíz
En la variable `minutes_since_cool_cycle_step`, dentro del bloque `variables`, la expresión del `else` tenía un paréntesis de cierre faltante antes de `}}`.

- Línea previa (incorrecta):
  `{{ 99999 if ts is none else (((as_timestamp(now()) - ts) / 60) | round(1) }}`
- Línea corregida:
  `{{ 99999 if ts is none else (((as_timestamp(now()) - ts) / 60) | round(1)) }}`

## Archivo y línea corregida
- `automations.yaml` (bloque de `variables`, variable `minutes_since_cool_cycle_step`).

## Validación
- Se confirmó en el archivo que la expresión quedó con el cierre correcto `| round(1)) }}`.
- En este entorno no fue posible ejecutar `Comprobar configuración` ni `Recargar automatizaciones` porque no están disponibles los binarios de Home Assistant CLI/Core (`ha`/`hass`).
- Validación pendiente en instancia de Home Assistant:
  1. Ejecutar **Comprobar configuración**.
  2. Ejecutar **Recargar automatizaciones** (o reiniciar Core).
  3. Confirmar en **Ajustes → Sistema → Registros** que no aparece `unexpected '}', expected ')'`.
  4. Confirmar que la automatización cambia de `unavailable` a `off/on` y admite activación manual.
