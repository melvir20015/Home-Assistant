# Nota de corrección: automatización nocturna AC

- **Fecha:** 2026-03-27
- **Alias afectado:** `AC - Noche dinámico (OpenWeather) + Presencia estable + Fan Low + Notificaciones`
- **Variable corregida:** `cool_last_useful_base_setpoint`

## Cambio aplicado
Se corrigió una expresión Jinja en `automations.yaml` eliminando un paréntesis de cierre extra en el bloque `if/else/endif` de la variable `cool_last_useful_base_setpoint`:

- Antes: `{{ [((cool_stop_threshold | float) - 1.0), cool_ramp_min_setpoint] | max | round(1)) }}`
- Después: `{{ [((cool_stop_threshold | float) - 1.0), cool_ramp_min_setpoint] | max | round(1) }}`

## Validación post-recarga
- **Comprobar configuración:** pendiente de ejecutar en Home Assistant (UI/Core).
- **Recargar automatizaciones / reiniciar Core:** pendiente de ejecutar en Home Assistant.
- **Revisión de logs (`TemplateSyntaxError: unexpected ')'`):** pendiente de confirmación posterior a la recarga.
