# Fix: scope base de sesión manual en automatización principal AC (2026-04-21)

## Contexto
Se corrigió la automatización `AC - Día dinámico aprendido (principal)` (`id: '1768159303322'`) para asegurar que las variables de sesión manual existan desde el inicio de ejecución y estén disponibles en todas las ramas.

## Causa raíz
**Variables definidas fuera del scope de la automatización principal.**

## Cambios aplicados
- Se consolidó al inicio del `action` un bloque `variables` con símbolos base de sesión manual:
  - `manual_on_active_session_raw`
  - `manual_on_session_trace_id`
  - `manual_on_session_status`
  - `manual_on_session_started_ts_raw`
  - `manual_on_session_started_epoch`
  - `manual_on_session_age_s`
  - `manual_on_session_ttl_s`
  - `manual_on_session_ttl_valid`
  - `manual_on_session_active`
  - `manual_on_session_protected`
- Se definió `manual_override_active` en ese mismo scope con fallback seguro a `false` cuando no hay datos válidos.
- Se endurecieron plantillas críticas con defaults defensivos:
  - `manual_on_session_age_s | default(99999) | float(99999)`
  - `manual_on_session_protected | default(false)`
  - `manual_override_active | default(false)`
- Se agregó traza diagnóstica de arranque:
  - `hito=manual_session_scope_ok`
  - Incluye `trace_id`, `session_status`, `session_age_s` y `manual_override_active`.

## Resultado esperado
- No hay referencias a `manual_on_session_*` ni `manual_override_active` antes de definición dentro de la automatización principal.
- Todas las ramas críticas comparten el mismo scope base y toleran datos faltantes sin romper evaluación de plantillas.
