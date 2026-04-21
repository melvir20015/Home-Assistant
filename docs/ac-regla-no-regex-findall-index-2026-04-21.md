# Regla de plantillas HA: parseo seguro de regex

Fecha: 2026-04-21

## Regla obligatoria

No usar `regex_findall_index` sin validar previamente que exista un match.

## Patrón recomendado (opción A)

1. Usar `regex_findall('patron')`.
2. Tomar `matches[0]` únicamente cuando `matches | count > 0`.
3. Definir fallback explícito para cada campo parseado.

Ejemplo:

```jinja
{% set matches = raw | regex_findall('trace_id=([^|]+)') %}
{{ matches[0] if (matches | count) > 0 else 'trace_missing' }}
```

## Fallbacks mínimos sugeridos

- `trace_id`: `trace_missing`
- `status`: `closed`
- `started_ts_raw`: `''`
- `started_epoch`: `none`
- `age_s`: `99999`

## Motivo

Evitar fallos por indexación fuera de rango cuando helpers `input_text` vienen vacíos, incompletos o malformados.
