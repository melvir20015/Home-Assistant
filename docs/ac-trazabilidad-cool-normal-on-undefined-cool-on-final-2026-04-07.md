# Trazabilidad: corrección de payload notify en `cool_normal_on` (2026-04-07)

## Fecha

- **2026-04-07**

## Error observado

- **`UndefinedError: 'cool_on_final' is undefined`**

## Archivo y rama afectada

- Archivo: **`automations.yaml`**
- Automatización: **`AC - Día dinámico aprendido (principal)`**
- Rama: **`ac_dda_branch=cool_normal_on`**
- Bloque: variables previo al notify (traza `action/0/choose/12/sequence/39`)

## Ajuste aplicado

Se corrigió `cool_mobile_message_local` para usar variables disponibles en ese scope de ejecución y plantillas con fallback seguro.

### Sustituciones de variables

- `cool_on_final` ➜ `cool_on_validated`
- `cool_off_final` ➜ `cool_off_validated`

Además, se introdujeron aliases locales explícitos:

- `cool_on_local`
- `cool_off_local`
- `tin_local`
- `tout_local`
- `hout_local`
- `sp_local`

## Endurecimiento de plantilla (fallback seguro)

- Se usa `| default(none)` al resolver variables de runtime.
- Si falta dato, se renderiza **`n/a`** en el mensaje final.

## Observabilidad agregada

Antes del `notify.mobile_app_samsung_s24` se registra un hito explícito:

- `hito=notify_payload_ready`

Este marcador permite confirmar en `logbook` que el payload quedó construido sin error antes del envío.

## Actualización de regresión mínima (2026-04-08)

### Objetivo

Dejar checklist mínimo de validación para no reintroducir regresiones en ON transaccional, clasificación manual ON y alcance de aprendizaje.

### Casos obligatorios

1. **`cool_normal_on` con confirmación HVAC tardía**
   - Deben observarse hitos:
     - `notify_on_preparado`
     - `notify_on_intentado`
     - (`notify_on_enviado` o `notify_on_fallido` con fallback)
   - El envío ON no depende del cierre `transition_closed=ok`; si hay timeout de confirmación HVAC, el push ON igual debe intentarse.

2. **Manual ON real luego de largo tiempo sin AUTO**
   - No debe descartarse por origen histórico.
   - Debe verse clasificación manual válida (`manual_on_final_valid_*`) y aprendizaje `-0.25` aplicado.

3. **Evento fuera de ámbito diurno principal**
   - Si ocurre fuera de `07:01–21:59` o fuera de rama `cool_normal_on`, debe marcar:
     - `ignored_reason_code=out_of_scope_daytime_main`
   - No deben escribirse buckets/sesgos del aprendizaje diurno principal.

4. **Descarte con trazabilidad extremo a extremo**
   - Todo descarte Manual ON debe incluir:
     - razón explícita de descarte,
     - `trace_id` consistente entre guard/log/notify/learning.
