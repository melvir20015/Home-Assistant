# Retención de traces en Home Assistant

## Resultado de la revisión

Se revisaron todos los YAML versionados de esta instancia (`automations.yaml`, `input_*.yaml` y `timer.yaml`) buscando bloques `trace:` y parámetros `stored_traces:`. En el estado actual del repositorio **no existe** una configuración global `trace:` ni un `stored_traces: 50` equivalente.

## Dónde debe controlarse la retención

En la versión actual usada para esta base, la retención de traces **no debe declararse de forma global** dentro de la configuración raíz. Si en el futuro se necesita aumentar el histórico de una automatización o un script, el ajuste debe hacerse **únicamente dentro de esa automatización o script**, por ejemplo:

```yaml
- id: ejemplo_automatizacion
  alias: Ejemplo
  trace:
    stored_traces: 20
  trigger:
    ...
```

## Regla operativa para futuros cambios

- **No agregar** un bloque raíz `trace:` en archivos de configuración global.
- **No mover** `stored_traces` a `configuration.yaml` ni a otro nivel global equivalente.
- Si se requiere más historial, aplicar `trace.stored_traces` sólo en la automatización/script puntual que lo necesite y validar antes de desplegar.

## Validación incluida en el repositorio

Se agregó el script `tools/check_trace_config.py`, que falla si detecta:

1. un bloque global `trace:`, o
2. un `stored_traces:` fuera de un bloque `trace:` por automatización/script.

Esto ayuda a evitar reintroducir el error asociado a `helpers/config_validation.py` al editar la configuración más adelante.
