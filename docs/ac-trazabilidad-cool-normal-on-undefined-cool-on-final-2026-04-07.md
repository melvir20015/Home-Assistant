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
