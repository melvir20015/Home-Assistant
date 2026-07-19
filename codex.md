# Documento fuente de verdad: Diseño y operación de la automatización HVAC

## 1. Propósito y alcance

### Objetivo general
Definir el contrato operativo de una automatización de confort térmico para un apartamento de **800 ft²**, priorizando estabilidad, eficiencia y claridad de comportamiento para ocupación humana real.

### Cobertura temporal
- La automatización cubre como franja principal el **horario diurno** (periodo de uso más frecuente).
- Fuera de la franja diurna, el sistema puede operar con reglas complementarias de menor agresividad para evitar oscilaciones innecesarias.

### Relación con control nocturno
- Si existe control nocturno separado, este documento actúa como contrato de referencia para evitar contradicciones.
- El modo nocturno debe:
  - respetar límites de seguridad térmica,
  - no sobrescribir aprendizaje contextual fuera de su ámbito,
  - devolver el control al contrato diurno sin discontinuidades al inicio del siguiente periodo.

---

## 2. Definiciones y entidades

### Climate principal
- Entidad principal de climatización (ejemplo: `climate.sala`).
- Modos esperados para este contrato: `off`, `fan_only`, `cool`.
- Cambios a `heat` son tratados como intervención explícita del usuario y bloquean automatismos incompatibles.

### Sensores internos (temperatura/humedad)
- Fuente primaria para decisión térmica:
  - temperatura interior (`sensor.temp_interior`),
  - humedad interior (`sensor.humedad_interior`).
- Deben ser estables y con actualización periódica confiable.

### Fuente exterior OpenWeather
- Fuente auxiliar para contexto ambiental externo:
  - temperatura exterior,
  - humedad exterior (si está disponible),
  - condición climática resumida.
- Se usa para modular umbrales y aprendizaje contextual.

### Presencia
La presencia válida se considera **activa** cuando se cumple:
1. detección de movimiento estable durante **3 minutos**, y
2. confirmación de presencia del dispositivo **S24/home**.

### Helpers exclusivos de esta automatización
Todos los helpers listados aquí son de uso exclusivo y no deben compartirse con otras automatizaciones.

- `input_boolean.hvac_auto_gate` — compuerta maestro AUTO ON/OFF.
- `input_boolean.hvac_manual_override` — marca intervención manual temporal.
- `input_boolean.hvac_emergency_mode` — estado de rama de emergencia.
- `input_number.hvac_context_setpoint` — setpoint aprendido por contexto.
- `input_text.hvac_context_key` — clave de contexto activa.
- `input_datetime.hvac_last_manual_action` — trazabilidad de última acción manual.
- `timer.hvac_post_cool_dry` — secado post-cool (2 min).

---

## 3. Reglas de presencia y seguridad

### Compuerta de AUTO ON/OFF
- Si `hvac_auto_gate = ON`, la automatización puede actuar según el contrato.
- Si `hvac_auto_gate = OFF`, la automatización no debe cambiar modo ni setpoint (excepto protecciones de seguridad definidas).

### Excepción por encendido manual con botón físico
- Cuando el usuario enciende manualmente desde botón físico, el evento se respeta como intención prioritaria.
- Se habilita `hvac_manual_override` durante la ventana de transición/confirmación.
- No se debe apagar ni revertir de inmediato por falta temporal de condiciones automáticas.

### Comportamiento ante pérdida de presencia
- Si se pierde presencia válida:
  - se inicia ventana de gracia corta para evitar apagados por ruido,
  - tras confirmarse ausencia sostenida, se permite transición a estado de ahorro (`off` o `fan_only` según reglas activas),
  - se preserva contexto para reanudación rápida cuando vuelva presencia.

---

## 4. Contrato térmico

### Fórmulas base
Se define el umbral de apagado de frío (`cool_off`) y encendido (`cool_on`) con histéresis positiva:

- `cool_off = T_objetivo_contexto + ajuste_estacional + ajuste_franja + ajuste_clima`
- `cool_on = cool_off + h`

Donde:
- `h` = histéresis (valor recomendado: `0.6 °C`, ajustable entre `0.4` y `0.8`).
- Encender frío cuando `T_interior >= cool_on`.
- Apagar frío cuando `T_interior <= cool_off`.

### Tablas por estación / franja / clima

#### Ajuste estacional (`ajuste_estacional`)
- Verano: `+0.3`
- Entretiempo: `0.0`
- Invierno cálido interior: `-0.2`

#### Ajuste por franja (`ajuste_franja`)
- Diurna principal: `0.0`
- Pre-nocturna (si aplica): `-0.2`

#### Ajuste por clima exterior (`ajuste_clima`)
- Exterior muy cálido/húmedo: `+0.2`
- Exterior templado: `0.0`
- Exterior fresco: `-0.2`

### Límites de seguridad
- Nunca forzar setpoint automático fuera de rangos de seguridad.
- Evitar ciclos cortos mediante histéresis y ventanas mínimas de permanencia.

### Setpoint contractual
El setpoint objetivo de operación en `cool` debe cumplir:

- `setpoint_contractual = floor(cool_off) - 1`
- Rango obligatorio: **`[17, 23]`**

Aplicación:
- `setpoint_final = clamp(setpoint_contractual, 17, 23)`

---

## 5. Rama de emergencia

### Criterios de entrada
Se entra a emergencia cuando ocurra cualquiera de las siguientes condiciones críticas:
- temperatura interior por encima de umbral extremo definido,
- inconsistencia severa de sensores principales,
- comportamiento anómalo del climate (sin respuesta en ventana operativa),
- regla explícita de seguridad activada por el usuario.

### Criterios de salida
- Se recuperan sensores confiables y estado normal del equipo por una ventana estable.
- Se desactiva condición crítica que originó el estado.
- Se registra evento de salida y se reengancha al contrato estándar de forma progresiva.

### Prioridades y bloqueos
- En emergencia, las reglas normales quedan subordinadas.
- Se bloquean automatismos no críticos (aprendizaje y microajustes) hasta estabilizar.
- La seguridad del equipo y del confort básico prevalece sobre optimización energética.

---

## 6. Aprendizaje contextual

### Clave de contexto
- La clave contextual (`hvac_context_key`) debe componerse con variables estables, por ejemplo:
  - estación,
  - franja horaria,
  - estado exterior resumido,
  - presencia válida.

### Reglas de ajuste por interacción manual
- **Manual OFF**: ajustar contexto con `+0.25`.
- **Manual ON**: ajustar contexto con `-0.25`.

Interpretación: reflejar preferencia del usuario en la dirección esperada para reducir fricción futura.

### Espera de 60 s para captura final en manual ON
- Ante encendido manual con intención de uso térmico, esperar **60 s** antes de capturar valor final para aprendizaje.
- Evita registrar valores transitorios durante cambios de modo.

### Setpoint por contexto sin regresión
- El setpoint aprendido por contexto no debe retroceder por ruido o eventos ambiguos.
- Si el usuario define un nuevo valor manual válido, este **reemplaza de inmediato** al valor contextual previo.

### Correlación por trace_id en Manual ON

Para evitar cruces entre corridas concurrentes de `Manual ON`, la confirmación del evento final debe quedar **atada al mismo `trace_id`** que dispara el aprendizaje.

#### Helpers de correlación
- `input_text.ac_dda_last_manual_on_trace_confirmed`: guarda `trace_id=<id>` del último `Manual ON` **final validado**.
- `input_text.ac_dda_last_manual_on_pending_signature`: firma corta de deduplicación temprana (`timestamp_evento|modo|origen`), usada antes de emitir notificación pendiente.

#### Orden transaccional obligatorio (Manual ON)
1. Detectar evento y aplicar deduplicación temprana por firma corta.
2. Emitir **un solo** `Resultado=pendiente` por traza válida.
3. Tras consolidación, escribir primero `manual_on_final_valid_*|trace_id=...` en `input_text.ac_dda_last_manual_event_type`.
4. Escribir luego `input_text.ac_dda_last_manual_on_trace_confirmed` con el mismo `trace_id`.
5. Persistir snapshot inmutable en `input_text.ac_dda_last_manual_on_snapshot` con formato `trace_id=...|event_type=...|final_mode=...|ts=...`.
6. Si `snapshot_verified=false`, ejecutar reparación controlada (write-back de `trace_confirmed` + `snapshot`) y luego **readback post-repair** de `event_type`, `trace_confirmed` y `snapshot`.
7. Recalcular con ese readback post-repair los flags `persistence_stage_1_ok`, `persistence_stage_2_ok`, `persistence_stage_3_ok` y `persistence_ready_for_trigger`.
8. Solo si `persistence_ready_for_trigger=true`, escribir `input_datetime.ac_dda_last_manual_on_ts` para disparar el learning, usando el `ts` final consolidado (cierre validado del evento, no `detected_ts`).

#### Regla transaccional de validación en Learning ON
- **Learning ON confirma por snapshot correlacionado por `trace_id`, no por estado global mutable**.
- `manual_event_confirmed` solo es verdadero si el snapshot dedicado `input_text.ac_dda_last_manual_on_snapshot`:
  - trae `trace_id` y coincide exactamente con `input_text.ac_dda_last_manual_on_trace_confirmed`,
  - trae `event_type` permitido (`manual_on_final_valid_contract_v1` o `manual_on_final_valid_presence_gap_contract_v1`).
- `input_text.ac_dda_last_manual_event_type` se conserva únicamente como telemetría auxiliar y no define confirmación transaccional.
- **La notificación de aprendizaje es obligatoria y no depende de éxito de escrituras de aprendizaje** (incluyendo fallos controlados en helpers dinámicos).

#### Política fuerte: aprendizaje forzado diurno con guardas suaves
- Se agrega bandera `manual_on_force_learn` para priorizar aprendizaje cuando exista evidencia manual reciente.
- `manual_on_force_learn = true` si:
  - hay evidencia reciente por snapshot o por timestamp de `Manual ON`,
  - la corrida está dentro de `07:01–21:59`,
  - el modo final termina en `cool`.
- Bajo `manual_on_force_learn=true`, señales de traza/snapshot (`manual_trace_mismatch`, `manual_event_not_confirmed`, `duplicate_event`) se tratan como **warning diagnóstico** (no descarte duro).
- El aprendizaje forzado mantiene clamps de contrato térmico: `off` en `[22.0, 25.7]`, `on <= 26.2` y siempre `on > off`.
- Si `manual_on_force_learn=false`, se mantiene la política estricta transaccional.

#### Reglas anti-colisión
- Si una segunda corrida detecta la misma firma corta, se descarta como duplicado antes de `Resultado=pendiente`.
- El aprendizaje ignora eventos con `trace_id` ausente o desalineado (`manual_trace_not_confirmed` / `manual_trace_mismatch`).
- Política diurna vigente: dentro de `07:01–21:59` aprende; fuera de ese rango clasifica `out_of_scope_daytime_main`.

#### Secuencia esperada (ejemplo)
- `AC - Manual ON guard`: detecta `trace_id=20260412101530-321`, valida guardas diurnas, emite pendiente único.
- Consolidación final: escribe `manual_on_final_valid_contract_v1|trace_id=20260412101530-321`.
- Confirma correlación: escribe `input_text.ac_dda_last_manual_on_trace_confirmed = trace_id=20260412101530-321`.
- Persiste snapshot inmutable: `input_text.ac_dda_last_manual_on_snapshot = trace_id=20260412101530-321|event_type=manual_on_final_valid_contract_v1|final_mode=cool|ts=2026-04-12 10:16:01`.
- Dispara learning: actualiza `input_datetime.ac_dda_last_manual_on_ts`.
- `AC - Learning - Manual ON feedback`: aplica `Resultado=aplicado` o `Resultado=ignorado` con razón justificada, sin usar estados globales no correlacionados.

#### Matriz mínima de decisión (Manual ON Learning)

| Política | Resultado | Condición mínima | Comportamiento |
|---|---|---|---|
| `force_learn` | `aplicado` | evidencia manual reciente + diurno + `final_mode=cool` | aplica `-0.25` o hard-anchor con clamps |
| `strict` | `aplicado` | snapshot confirmado por `trace_id` y guardas estrictas válidas | aplica aprendizaje normal/anchor |
| `strict` | `ignorado` | no cumple guardas de alcance/modo/confirmación | emite razón explícita de descarte |
| `force_learn` o `strict` | `error_controlado` | fallo interno controlado en pipeline | notificación final obligatoria |

#### Ejemplos de trazabilidad esperada
- Flujo aplicado:
  1. `Resultado=pendiente`
  2. `Resultado=capturado`
  3. `AC Learning ON` con `Resultado=aplicado` y `policy=force_learn|strict`.
- Flujo ignorado:
  1. `Resultado=pendiente`
  2. `Resultado=capturado`
  3. `AC Learning ON` con `Resultado=ignorado`, razón y `policy=strict`.
- Flujo con error controlado:
  1. `Resultado=pendiente`
  2. `Resultado=capturado`
  3. `AC Learning ON` con `Resultado=error_controlado` y `policy=force_learn|strict`.

#### Política final de cierre obligatorio (Manual ON diurno)
- **Regla operativa**: `Manual ON diurno válido cierra siempre en tercera notificación`.
- La tercera notificación (`AC Learning ON`) debe emitirse siempre con un único resultado terminal:
  - `aplicado`
  - `ignorado`
  - `error_controlado`
- La notificación final debe incluir obligatoriamente: `Trace`, `Policy` y `Reason`.
- Snapshot/trace de correlación se conserva como telemetría diagnóstica y no puede provocar cierre silencioso cuando existe política `force`.

#### Tabla de decisión final (cierre)

| Política | Resultado | Condición | Razón típica |
|---|---|---|---|
| `force` | `aplicado` | `last_change_origin=manual_on` + diurno + `final_mode=cool` + gate abierto | `manual_on_normal_applied_force_learn` |
| `strict` | `aplicado` | snapshot/trace/evento confirmados + diurno + `final_mode=cool` | `manual_on_normal_applied` |
| `force` o `strict` | `ignorado` | gate cerrado o evento ya procesado | `final_mode_not_cool`, `out_of_scope_daytime_main`, `event_already_processed` |
| `force` o `strict` | `error_controlado` | fallo controlado en persistencia/escrituras/contrato | `learning_on_internal_error`, `persistencia_pre_learning_incompleta` |

#### Checklist de depuración por trace
1. Verificar secuencia completa: `pendiente -> capturado -> AC Learning ON`.
2. Confirmar `Trace` idéntico entre guard y learning.
3. Revisar `policy` reportada (`force` o `strict`) y estado del `learning_gate_ok`.
4. Auditar cierre en logbook con: `hito=learning_on_closed`, `resultado`, `razon`, `policy`, `trace_id`.

### AC-Matriz 160 — Política de aprendizaje manual por columna (actualización operativa)

- **Clasificación de origen explícita**:
  - `automatico_ac_matriz_160`: cambios trazables al propio controlador AC-Matriz 160.
  - `automatico_recovery`: cambios por recuperación/reconexión o sin transición HVAC real.
  - `manual_externo`: cambios ON/OFF externos (app fabricante, IR bridge, escenas, voz, app HA o control físico), incluso con `user_id=null`.
- **Marcador transaccional automático con TTL**:
  - todo encendido/apagado originado por AC-Matriz 160 debe escribir marcador de origen automático transaccional con **TTL de 30 s**.
  - el aprendizaje manual debe validar ese marcador antes de clasificar un evento como manual.
- **Criterio base de aprendizaje**: solo cuando hay transición HVAC real (`off<->cool` o `off<->heat`) y el origen no coincide con firma automática de AC-Matriz 160.
- **Separación explícita entre seguridad y aprendizaje**:
  - **seguridad**: el bloqueo por apagado manual se aplica siempre (sin depender de ambigüedad de origen).
  - **aprendizaje**: solo se aplica cuando la clasificación no es ambigua; ante ambigüedad, registrar `ignorado` con razón terminal explícita.
- **Contrato de aprendizaje por modo/columna**:
  - COOL: `off->cool` manual = `-0.25`, `cool->off` manual = `+0.25`.
  - HEAT espejo: `off->heat` manual = `+0.25`, `heat->off` manual = `-0.25`.
  - Clamp acumulado obligatorio: `[-3.0, +3.0]`.
- **Resultado terminal obligatorio**:
  - `aplicado`, `ignorado`, `error_controlado`.
  - Con `razon` explícita (`manual_externo_aplicado`, `evento_no_transicion`, `origen_automatico_ac_matriz`, `estado_recovery`, `dedup`, `helper_invalido`, etc.).
- **Bloqueo global post-apagado manual**:
  - tras `apagado_manual` válido se fija `input_datetime.ac_matriz_160_manual_off_block_until = now + 5 min`.
  - precedencia obligatoria: el bloqueo manual de **5 min** prevalece sobre cualquier auto-encendido (incluyendo encendidos con marcador automático válido).
  - en la automatización principal AC-Matriz 160, cualquier `turn_on_cool/turn_on_heat` se bloquea si `now < manual_off_block_until`.
  - se registra `hito=auto_on_bloqueado_post_manual_off`.
- **Comportamiento ante reinicio de Home Assistant**:
  - `manual_off_block_until` persiste y debe respetarse hasta su expiración natural tras reinicio.
  - ningún reinicio de HA puede limpiar ni reducir la ventana de bloqueo manual activa.
- **Regla de notificación para aprendizaje normal**:
  - eliminar `persistent_notification` en aprendizaje normal.
  - mantener solo push móvil al usuario (`notify.mobile_app_samsung_s24`) y registro técnico en `logbook.log`.
  - estado de envío en helper: `input_text.ac_matriz_160_ultimo_estado_notificacion` con `emitida|error_controlado`.
- **Ejemplos de traza esperada**:
  - aplicado: `hito=learning_manual_columna | resultado_terminal=aplicado | razon=manual_externo_aplicado`.
  - ignorado: `hito=learning_manual_ignorado | resultado_terminal=ignorado | razon=evento_no_transicion`.
  - error controlado: `resultado_terminal=error_controlado | razon=helper_invalido`.
5. Si hay persistencia incompleta previa al trigger, validar que exista `Resultado=error_controlado` (sin cierre silencioso).

#### Checklist de validación posterior al cambio
1. El auto-ON no dispara clasificación ni aprendizaje de tipo “manual”.
2. `manual-OFF` bloquea auto-ON durante 5 min en todos los casos.
3. No aparecen tarjetas `persistent_notification` para aprendizaje normal.
4. Los logs incluyen `trace_id`, `origen` y `razón terminal` en el cierre del aprendizaje.

---

## 7. Flujo manual power (`off -> fan_only`)

### Secuencia base
1. Detectar transición manual `off -> fan_only`.
2. Esperar **30 s**.
3. Ejecutar auto-cambio a `cool` cuando se mantengan condiciones del contrato.

### Excepciones
- Si durante la espera o inmediatamente después el usuario cambia explícitamente a `heat`,
  - cancelar auto-cambio a `cool`,
  - registrar excepción,
  - respetar preferencia manual.

### Aprendizaje asociado
- Registrar la secuencia como señal contextual de intención de enfriamiento asistido.
- Integrar al aprendizaje sólo si no hubo conflicto de modo.

---

## 8. Secado post-cool

Al terminar ciclo de `cool`, activar `fan_only` por **2 minutos** para secado post-cool y reducción de humedad residual del sistema.

- Inicio: transición de salida de `cool`.
- Fin: expiración de `timer.hvac_post_cool_dry`.
- Cancelación: intervención manual incompatible o entrada de emergencia.

---

## 9. Notificaciones

### Tipos
- **ON**: activación de enfriamiento o transición relevante de encendido.
- **OFF**: apagado o paso a estado de ahorro.
- **Aprendizaje**: actualización contextual por acciones manuales.

### Formato compacto con decimales
- Mensajes deben incluir valores clave (temperatura interior, `cool_on`, `cool_off`, setpoint) con **1 decimal** cuando aplique.
- Priorizar estructura breve y consistente.

### Abreviaturas oficiales
- `Tin`: temperatura interior.
- `Tout`: temperatura exterior.
- `Hin`: humedad interior.
- `SP`: setpoint.
- `Ctx`: contexto.
- `Emg`: emergencia.

### Política de recorte para S24
- Limitar longitud para garantizar lectura en notificación móvil S24.
- Priorizar: acción + motivo + valor crítico.
- Mover detalles extendidos al logbook.

### Confiabilidad de umbrales contractuales On/Off
- Cualquier valor `On/Off` fuera del rango contractual (`off` en `[22.0, 25.7]`, `on` en `<= 26.2` y `on > off`) se considera **dato no confiable**.
- Si el dato es no confiable, no debe publicarse en notificaciones y se debe conservar el último contrato válido en helpers.
- Registrar razón explícita de descarte para trazabilidad (`reject_invalid_contract_values`).

---

## 10. Observabilidad y mantenimiento

### Eventos de logbook requeridos
Registrar como mínimo:
- cambios de modo automáticos y manuales detectados,
- entrada/salida de emergencia,
- aplicación de setpoint contractual,
- ajustes de aprendizaje contextual,
- bloqueos por presencia o por compuerta AUTO.

### Checklist para futuras modificaciones
Antes de cambiar reglas:
1. Validar impacto en histéresis y ciclos cortos.
2. Verificar compatibilidad con presencia y seguridad.
3. Confirmar que no rompe flujo manual `off -> fan_only`.
4. Revisar notificaciones compactas para S24.
5. Documentar decisión en sección de trazabilidad.

### Criterios para no mezclar helpers
- Cada helper de este contrato debe tener prefijo `hvac_` y propósito único.
- Prohibido reutilizar estos helpers en otras automatizaciones.
- Si se requiere dato compartido, crear helper neutro separado y documentarlo explícitamente.

---

## Decisiones tomadas (fecha y motivo)

- **2026-04-05** — Se crea `codex.md` como fuente de verdad inicial del contrato HVAC para centralizar diseño, operación, seguridad, aprendizaje y mantenibilidad en un único documento trazable.

---

## 11. Migración de helpers a namespace exclusivo `ac_dda_*` (2026-04-06)

### Automatizaciones incluidas en esta migración (5)
1. `AC - Día dinámico aprendido (principal)`
2. `AC - Learning - Manual OFF feedback`
3. `AC - Learning - Manual ON feedback`
4. `AC - Manual OFF guard + pausa 5 min`
5. `AC - Manual ON guard + presencia temporal`

### Inventario consolidado de helpers consumidos (principal + auxiliares)
- **Banderas de origen automático:** `input_boolean.ac_dda_on_por_automatizacion`, `input_boolean.ac_dda_off_por_automatizacion`.
- **Trazabilidad de eventos manuales:**
  - `input_datetime.ac_dda_last_manual_on_ts`
  - `input_datetime.ac_dda_last_manual_off_ts`
  - `input_datetime.ac_dda_last_manual_final_ts`
  - `input_datetime.ac_dda_last_manual_feedback_ts`
  - `input_text.ac_dda_last_manual_event_type`
  - `input_text.ac_dda_last_manual_learning_type`
  - `input_text.ac_dda_last_manual_final_mode`
  - `input_text.ac_dda_last_manual_final_fan`
  - `input_number.ac_dda_last_manual_setpoint`
- **Contexto + contratos del ciclo cool:**
  - `input_text.ac_dda_last_context_bucket`
  - `input_text.ac_dda_last_change_origin`
  - `input_text.ac_dda_cool_contextual_learning_map`
  - `input_text.ac_dda_cool_effective_setpoint_map`
  - `input_text.ac_dda_cool_cycle_contract_bucket`
  - `input_text.ac_dda_cool_cycle_contract_reason`
  - `input_datetime.ac_dda_cool_cycle_contract_started_at`
  - `input_number.ac_dda_cool_cycle_contract_on`
  - `input_number.ac_dda_cool_cycle_contract_off`
  - `input_number.ac_dda_cool_cycle_contract_sensor_off`
  - `input_number.ac_dda_cool_cycle_contract_setpoint`
  - `input_number.ac_dda_cool_cycle_contract_setpoint_effective`
- **Aprendizaje/ventanas de feedback:**
  - `input_number.ac_dda_feedback_window_minutes`
  - `input_number.ac_dda_cool_off_learned`
  - `input_number.ac_dda_manual_on_min_off_window_minutes`
  - `input_text.ac_dda_learning_last_manual_off_signature`
  - `input_text.ac_dda_learning_last_manual_on_signature`
- **Presencia temporal manual:** `input_datetime.ac_dda_manual_presence_until`.
- **Compatibilidad de transición:** `input_text.ac_dda_legacy_helper_map`.

### Mapa temporal de compatibilidad (`legacy` → `ac_dda_*`)
- `input_boolean.ac_on_por_automatizacion` → `input_boolean.ac_dda_on_por_automatizacion`
- `input_boolean.ac_off_por_automatizacion` → `input_boolean.ac_dda_off_por_automatizacion`
- `input_datetime.ac_last_manual_on_ts` → `input_datetime.ac_dda_last_manual_on_ts`
- `input_datetime.ac_last_manual_off_ts` → `input_datetime.ac_dda_last_manual_off_ts`
- `input_datetime.ac_last_manual_final_ts` → `input_datetime.ac_dda_last_manual_final_ts`
- `input_datetime.ac_last_manual_feedback_ts` → `input_datetime.ac_dda_last_manual_feedback_ts`
- `input_datetime.ac_manual_presence_until` → `input_datetime.ac_dda_manual_presence_until`
- `input_text.ac_last_change_origin` → `input_text.ac_dda_last_change_origin`
- `input_text.ac_last_auto_context_bucket` → `input_text.ac_dda_last_context_bucket`
- `input_text.ac_last_manual_event_type` → `input_text.ac_dda_last_manual_event_type`
- `input_text.ac_last_manual_learning_type` → `input_text.ac_dda_last_manual_learning_type`
- `input_text.ac_last_manual_final_mode` → `input_text.ac_dda_last_manual_final_mode`
- `input_text.ac_last_manual_final_fan` → `input_text.ac_dda_last_manual_final_fan`
- `input_text.ac_learning_last_manual_off_signature` → `input_text.ac_dda_learning_last_manual_off_signature`
- `input_text.ac_learning_last_manual_on_signature` → `input_text.ac_dda_learning_last_manual_on_signature`
- `input_number.ac_last_manual_setpoint` → `input_number.ac_dda_last_manual_setpoint`
- `input_number.ac_feedback_window_minutes` → `input_number.ac_dda_feedback_window_minutes`
- `input_number.ac_cool_off_learned` → `input_number.ac_dda_cool_off_learned`
- `input_number.ac_manual_on_min_off_window_minutes` → `input_number.ac_dda_manual_on_min_off_window_minutes`

### Política de retiro de dependencias legacy
1. Mantener lectura/escritura funcional únicamente en `ac_dda_*` para estas 5 automatizaciones.
2. Validar en trazas que no haya lecturas activas de helpers legacy dentro de estas 5 automatizaciones.
3. Retirar helpers legacy sólo cuando el resto de automatizaciones externas deje de consumirlos.

---

## 12. Intervención única en `automations.yaml` para reinicio limpio (2026-04-06)

### Resumen aplicado
- Se repararon bloques YAML de la automatización **`AC - Día dinámico aprendido (principal)`** en ramas:
  - `presence_off`
  - `emergency_off`
  - `cool_normal_off`
- Se reescribieron plantillas largas (`cool_cycle_contract_snapshot`, `cool_cycle_final_message` y detalle de causa) con bloque seguro `>-` para eliminar riesgo de comillas/Jinja mal cerradas.
- Se normalizó el uso de umbrales mostrados en notificaciones OFF/ManualSP para usar valores contractuales validados y mostrar `n/a` cuando no existan datos válidos.
- Se confirmó que no hay referencias a `person.alberto`; la presencia telefónica queda acotada a:
  - `person.ivan`
  - `device_tracker.samsung_s24`
  - `binary_sensor.presencia_ok_estable`

### Reglas finales vigentes de notificación compacta
- Formato de campos requerido y consistente:
  - `Tin=...`
  - `Tout=...`
  - `H=...`
  - `On=...`
  - `Off=...`
  - `SP=...`
  - `Fan=...`
  - `Src=...`
  - `Delta=...`
- Hora en formato de 12 horas AM/PM sin cero a la izquierda (ej.: `2:22 PM`).
- Para aprendizaje/manual feedback se conserva salida en ambos casos:
  - `Resultado=aplicado`
  - `Resultado=ignorado`
  - con `Razón=...` breve.

### Checklist operativo de mantenimiento futuro
1. **Sintaxis segura**: todo template largo de mensaje/snapshot debe ir en `>-`.
2. **Umbrales visibles**: `On/Off` siempre desde fuente contractual validada; si no, `n/a`.
3. **Presencia**: no introducir nuevas entidades `person.*` fuera de `person.ivan` en estas 5 automatizaciones.
4. **Setpoint manual**: mantener detección con delta real, persistencia por contexto en rango `[17,23]`, y bloqueo de rollback durante ventana de override.
5. **Validación previa a reinicio**:
   - ejecutar validación YAML,
   - ejecutar `check_config` de Home Assistant en el runtime real donde exista `homeassistant`,
   - confirmar ausencia de errores de `annotatedyaml.loader` en logs de arranque.

### Trazabilidad de mantenimiento (2026-04-06)
- **Fuente externa única (sin fallback):** `weather.openweathermap`.
- **Atributos OWM usados en contrato y notificaciones:**
  1. Temperatura exterior: `state_attr('weather.openweathermap','temperature')` → `tout_owm`
  2. Humedad exterior: `state_attr('weather.openweathermap','humidity')` → `hout_owm`
  3. Condición climática: `states('weather.openweathermap') | lower` → `cond_owm`
- **Política contractual vigente:** si OWM no entrega dato válido (`unknown/unavailable/none`) en ese instante, se mantiene la notificación y se muestra `n/a` sin fallback.
- **Impacto operativo:**
  - `Tout` y `H` en notificaciones compactas OFF/ON se construyen desde OWM.
  - El componente climático del contexto/bucket y la razón de contrato se deriva de `cond_owm` para evitar mezcla de fuentes exteriores legacy.

---

## 13. Política final de visualización para notificaciones `Src=ManualSP` (2026-04-06)

### Variables contractuales normalizadas obligatorias
En la automatización **`AC - Feedback manual de setpoint en cool activo`** se define la cadena local:
- `contract_on_raw`, `contract_off_raw` (lectura cruda de helpers),
- `contract_on`, `contract_off` (parseo numérico seguro),
- `contract_valid` (validez contractual).

La validez contractual sigue exactamente el mismo criterio operativo de `Learning ON/OFF`:
- `on > off`,
- `off ∈ [22.0, 25.7]`,
- `on <= 26.2`.

### Prioridad de fuentes para `On/Off` en `Src=ManualSP`
Orden estricto de resolución:
1. **Fuente primaria validada localmente** (`cool_on_validated/cool_off_validated` calculadas desde `contract_on/contract_off` cuando `contract_valid=true`).
2. **Último snapshot válido** persistido en helpers contractuales del ciclo (`input_number.ac_dda_cool_cycle_contract_on/off`) cuando la lectura primaria no resulte válida en ese instante.
3. **`n/a`** únicamente si también falla la fuente de snapshot válido (sin dato numérico usable o fuera de contrato).

### Política de persistencia contractual en la automatización principal
En la automatización principal (rama de escritura contractual):
- `input_number.ac_dda_cool_cycle_contract_on/off` **solo se actualizan cuando el contrato es válido**.
- Si el contrato no valida, **no se escribe `0`** ni se pisa el último valor bueno.
- La trazabilidad del descarte se guarda en `input_text.ac_dda_cool_cycle_contract_reason` con prefijo `contract_invalid:` y sufijo `|keep_last_valid`.

---

## 14. Protocolo de transición AUTO (`ac_dda_transition_*`) — trazabilidad (2026-04-07)

### Objetivo
Evitar reclasificaciones ambiguas entre eventos **AUTO** y **manuales** durante cambios de modo HVAC, incluyendo ramas diurnas, de emergencia y puentes (`fan_only -> off` / `fan_only -> cool`).

### Helpers del protocolo
- `input_boolean.ac_dda_on_por_automatizacion`
- `input_boolean.ac_dda_off_por_automatizacion`
- `input_text.ac_dda_transition_token`
- `input_datetime.ac_dda_transition_ts`
- `input_text.ac_dda_last_change_origin`

### Estados operativos
1. **idle (sin transición abierta)**
   - banderas AUTO en `off`.
   - sin token reciente utilizable para bloqueo de guard manual.
2. **auto_transition_open:on**
   - `ac_dda_on_por_automatizacion=on`.
   - token/ts nuevo escrito justo antes de `climate.set_hvac_mode` automático ON.
   - `ac_dda_last_change_origin=auto_on`.
3. **auto_transition_open:off**
   - `ac_dda_off_por_automatizacion=on`.
   - token/ts nuevo escrito justo antes de `climate.set_hvac_mode` automático OFF.
   - `ac_dda_last_change_origin=auto_off`.
4. **auto_transition_closed:ok**
   - `wait_template` confirma estado final esperado.
   - se apaga bandera AUTO correspondiente.
   - se registra `transition_closed=ok` en trazas/logbook.
5. **auto_transition_closed:timeout**
   - `wait_template` agota timeout sin confirmación.
   - **no** se reclasifica como manual.
   - se mantiene evidencia (flag o token reciente + traza `transition_closed=timeout`).

### Ventanas recomendadas para guards/manual feedback
- Ventana de guard por transición abierta/reciente: **180 s** (`token + timestamp`).
- Si dentro de la ventana hay token reciente o bandera AUTO activa, los guards manuales deben descartar el evento con:
  - `manual_guard_discard=auto_transition_active`
  - `hito=notify_omitido_por_auto`

### Lectura de logs para depuración
1. Buscar `hito=notify_payload_ready` para validar payload generado.
2. Confirmar envío con `hito=notify_enviado`.
3. Si manual guard descarta: verificar `hito=notify_omitido_por_auto` + `manual_guard_discard=auto_transition_active`.
4. Si hubo cambio AUTO:
   - revisar token/ts y `ac_dda_last_change_origin`.
   - validar cierre con `transition_closed=ok` o `transition_closed=timeout`.
5. Si `timeout`: tratar evento como transición AUTO no confirmada aún (no manual), hasta que expire ventana de guard y desaparezcan evidencias.

---

## 15. Trazabilidad consolidada ON/OFF y clasificación manual (2026-04-07)

### Cobertura aplicada
- `AC - Día dinámico aprendido (principal)`:
  - Rama `cool_normal_on` con hitos explícitos de push ON:
    - `hito=notify_on_preparado`
    - `hito=notify_on_intentado`
    - `hito=notify_on_fallido`
    - `hito=notify_on_enviado`
  - Ramas AUTO OFF con protocolo estricto previo a `climate.set_hvac_mode: off`:
    - `input_boolean.ac_dda_off_por_automatizacion=on`
    - `input_text.ac_dda_last_change_origin=auto_off`
    - `input_datetime.ac_last_auto_off_marker_ts=now()`
    - `input_text.ac_last_auto_off_marker_nonce=<nonce nuevo por intento>`
- `AC - Manual OFF guard + pausa 5 min`:
  - Bloqueo fuerte ante evidencia AUTO (flag ON, nonce reciente, origen AUTO reciente).
  - Revalidación corta adicional (2 s) antes de grabar `last_manual_off_ts`.
- `AC - Learning - Manual OFF feedback`:
  - Solo aplica aprendizaje si existe evidencia manual explícita y ausencia de señales AUTO recientes.
  - En descarte, conserva `Resultado=ignorado` y razón explícita.

### Claves de log estandarizadas
- `off_classification=auto|manual`
- `classification_reason=<causa>`
- `off_nonce=<nonce o n/a>`
- `manual_guard_discard_reason=<causa o none>`

### Regla operativa de depuración
1. Verificar primero clasificación (`off_classification`) y causa (`classification_reason`).
2. Confirmar nonce (`off_nonce`) y edad del marcador en guard/learning.
3. Si guard descarta, revisar `manual_guard_discard_reason`.
4. Si Learning OFF ignora, revisar `ignored_reason_code` y validar que no haya escritura de aprendizaje.

---

## 16. Robustez de notificación ON + detección manual ON (2026-04-08)

### Problema observado
- En ciertos ciclos `cool_normal_on`, la notificación ON no se emitía cuando la confirmación HVAC (`wait_template`) expiraba antes de reflejar `cool`, aunque el encendido sí era intentado por la rama AUTO.
- Encendidos manuales reales (botón físico/control remoto) quedaban descartados como `evidencia_manual_insuficiente` cuando el último evento AUTO superaba la ventana máxima previa (120 min), impidiendo aprendizaje `Manual ON (-0.25)`.

### Ajuste aplicado en automatizaciones
1. **Notificación ON en rama `cool_normal_on`**
   - Se desacopló la condición de envío del push ON respecto a `hvac_cool_confirmed`.
   - Ahora el envío depende de `cool_push_kind`, preservando trazas de fallo (`notify_on_fallido`) y fallback local (`persistent_notification`) si el canal móvil falla.

2. **Guard y learning de `Manual ON`**
   - Se eliminó el límite superior de la ventana (`<= 120 min`) en:
     - `AC - Manual ON guard + presencia temporal`
     - `AC - Learning - Manual ON feedback`
   - La validación temporal queda en:
     - bloquear sólo AUTO reciente (`< 3 min`),
     - permitir manual válido para cualquier antigüedad `>= 3 min`.

### Efecto esperado
- La notificación ON se vuelve consistente ante transiciones relevantes de encendido AUTO, incluso con confirmación tardía del `climate`.
- Encendidos manuales legítimos vuelven a trazarse como manuales y alimentan aprendizaje contextual `-0.25` como exige el contrato.

## 17. Corrección de trazabilidad `Manual ON` y guard anti-falsos positivos (2026-04-08)

### Causa raíz confirmada
- Se detectó descarte de encendidos manuales legítimos por una condición `auto_transition_active` demasiado permisiva: bastaba token de transición reciente, incluso con rastro residual sin evidencia AUTO actual.
- Esto provocaba dos efectos:
  1. `AC - Manual ON guard + presencia temporal` descartaba eventos manuales como `auto_transition_active`.
  2. `AC - Learning - Manual ON feedback` no aplicaba aprendizaje por la misma clasificación, quedando sin correlación explícita extremo a extremo.

### Reglas nuevas de clasificación manual vs auto
1. `auto_transition_active` ahora exige evidencia fuerte:
   - **verdadero** si hay `auto_flags_active`, o
   - **verdadero** si hay token reciente **y además** evidencia de origen AUTO reciente (`last_change_origin` AUTO y/o auto reciente por tiempo).
2. Se instrumenta `trace_id` único por evento manual ON detectado y se propaga al feedback de learning mediante `input_text.ac_dda_last_manual_event_type`.
3. Si el guard descarta (pre-guard o post-60s), siempre se emite salida observable:
   - logbook con razón + variables de diagnóstico,
   - notificación móvil compacta S24 con `Src=ManualON Resultado=ignorado Razón=<...> Trace=<trace_id>`.
4. Se retiró el bloqueo horario estricto `07:01-21:59` en:
   - `AC - Manual ON guard + presencia temporal`
   - `AC - Learning - Manual ON feedback`
   para no perder pruebas/manual ON nocturnas.

### Variables de diagnóstico obligatorias registradas
- **Pre-guard:** `auto_transition_recent`, `transition_age_s`, `last_change_origin_raw`, `auto_flags_active`, `minutes_since_last_auto`, `manual_on_guard_discard_reason`.
- **Post-60s:** `auto_transition_recent`, `transition_age_s`, `last_change_origin_raw`, `auto_flags_active`, `minutes_since_last_auto`, `post60_guard_discard_reason`.

### Tabla corta de resultados esperados
| Evento manual ON | Estado final | Notificación esperada |
|---|---|---|
| Manual ON válido (sin evidencia AUTO reciente) | `manual_on_final_valid_*` + learning ON aplicado | `Src=ManualON Resultado=aplicado` (guard/pendiente + learning) con `Trace` |
| Manual ON descartado en pre-guard | `stop` por `manual_on_guard_discard_reason` | `Src=ManualON Resultado=ignorado Razón=<reason> Trace=<trace_id>` |
| Manual ON descartado en post-60s | `stop` por `post60_guard_discard_reason` | `Src=ManualON Resultado=ignorado Razón=<reason> Trace=<trace_id>` |
| Cambio AUTO dentro de ventana de seguridad | clasificado como AUTO (no manual) | No debe convertirse a aprendizaje manual ON |

## 18. Latencia objetivo y garantías de robustez en `Manual ON` (2026-04-08)

### Objetivo operativo de latencia percibida
- Reducir el tiempo percibido del flujo de aprendizaje por encendido manual desde ~2–2.5 min a una ventana típica de **45–75 s**.
- Mantener separación robusta entre eventos manuales y automáticos (sin degradar guardas de transición AUTO).

### Tiempos nuevos aplicados
1. **`AC - Manual ON guard + presencia temporal`**
   - Consolidación principal de encendido manual: **30 s** (antes 60 s).
   - Puente `off -> fan_only -> cool`: **12 s** (antes 30 s).
2. **`AC - Learning - Manual ON feedback`**
   - Delay inicial de feedback/aprendizaje: **25 s** (antes 60 s).

### Garantías de robustez que se mantienen
- Se conservan los bloqueos por:
  - transición automática activa o reciente (`auto_transition_active`),
  - evidencia de origen AUTO (`last_change_origin` AUTO),
  - autoacción reciente por ventana mínima (3 min),
  - lock de ciclo (`ac_dda_cycle_lock`).
- Se conserva la protección anti-duplicado en learning ON por firma de evento (`duplicate_event`).
- El descarte por evidencia AUTO reciente sigue devolviendo salida observable con razón explícita.

### Observabilidad reforzada (hitos de logbook)
Se consolidan hitos con mensajes cortos y consistentes:
- `hito=manual_on_detected`
- `hito=manual_on_validating`
- `hito=manual_on_final`
- `hito=learning_on_applied` / `hito=learning_on_ignored`

### Secuencias esperadas
1. **Caso aplicado**
   - Se detecta ON manual válido.
   - Se emite push temprano: `Src=ManualON Resultado=pendiente Razón=validando`.
   - Tras consolidación + feedback se emite `AC Learning ON` con:
     - `Resultado=aplicado`
     - `Razón=manual_on`
2. **Caso ignorado**
   - Se detecta evidencia de autoacción/lock/origen no manual.
   - Se emite `AC Learning ON` con:
     - `Resultado=ignorado`
     - `Razón=<ignored_reason_code>`
   - La razón debe coincidir con los hitos de logbook (`learning_on_ignored` + código).

## 19. Hardening transaccional ON + alcance de aprendizaje diurno (2026-04-08)

### Ajustes aplicados
1. **Sub-flujo transaccional de notificación ON (`Cool↑`)**
   - Se introdujo el script `ac_dda_notify_on_transaccional` para centralizar envío móvil ON.
   - El script exige payload previamente validado y conserva hitos obligatorios:
     - `hito=notify_on_preparado`
     - `hito=notify_on_intentado`
     - `hito=notify_on_fallido`
     - `hito=notify_on_enviado`
   - Se mantiene fallback consistente a `persistent_notification.create`.
   - El flujo se reutiliza en:
     - `cool_normal_on`
     - `cool_emergency_on`
     - transición manual asistida `off -> fan_only -> cool` (cuando aplica).

2. **Formato contractual ON unificado**
   - Todas las ramas ON anteriores usan contrato compacto consistente:
     - `Tin/Tout/H/On/Off/SP/Fan/Src`
   - Si un dato no está disponible, se publica `n/a` sin abortar trazabilidad.

3. **Clasificación `Manual ON` basada en evidencia AUTO reciente**
   - Guard y Learning ON usan ahora criterio temporal compuesto común:
     - flags AUTO activos, o
     - token de transición dentro de ventana, o
     - timestamp AUTO reciente.
   - Se evita bloqueo por `input_text.ac_dda_last_change_origin` histórico sin evidencia temporal vigente.
   - Se preserva `trace_id` y motivo explícito en descarte.

4. **Alcance del aprendizaje restringido a diurno principal**
   - El `Manual ON feedback` sólo aplica aprendizaje cuando:
     - rama principal `cool_normal_on`,
     - franja contractual diurna (`07:01–21:59`),
     - contexto bucket válido del flujo principal.
   - Fuera de ámbito se descarta con:
     - `ignored_reason_code=out_of_scope_daytime_main`
   - En ese caso no se escriben sesgos/buckets de aprendizaje diurno.

5. **Consistencia Learning ON**
   - Se mantiene `learning_step=-0.25`.
   - Cuando aplica, además del bucket contextual `off`, se actualiza helper de histéresis contextual:
     - `input_number.ac_dda_cool_delta_on_bucket_*`
   - Se conserva anti-duplicado por firma de evento.

6. **Fix de robustez en Learning OFF**
   - Se define explícitamente `auto_origin_detected` antes de usarlo en `transition_origin_recent`.
   - Se evita referencia implícita a variable indefinida en plantillas.

### Casos mínimos de regresión requeridos
- **(a)** `cool_normal_on` emite ON (`Cool↑`) aun con confirmación HVAC tardía.
- **(b)** Manual ON real tras largo tiempo desde último AUTO se clasifica manual y aprende.
- **(c)** Eventos nocturnos no escriben aprendizaje diurno principal.
- **(d)** Descartes exponen razón + `trace_id` de extremo a extremo.

## 20. Contrato final Manual ON diurno (2026-04-09)

### Precondición y alcance
- El evento candidato inicia cuando el `climate` parte en **`off`** y el usuario enciende manualmente.
- El alcance funcional de `Manual ON guard` y `Learning ON feedback` queda restringido al horario diurno principal: **`07:01:00–21:59:00`**.
- Fuera de horario diurno:
  - no se escribe aprendizaje diurno,
  - se registra descarte explícito con `reason_code=out_of_scope_daytime_main`.

### Ventana de consolidación manual
- La consolidación de encendido manual se mantiene en **30 segundos**.
- Tras esa espera, el aprendizaje ON sólo puede aplicar si el modo final es **`cool`**.

### Modo final requerido para aprendizaje ON
- Condición única de modo final válido: `final_mode == cool`.
- Si el flujo termina en otro modo (`fan_only`, `heat`, etc.), se ignora con:
  - `Resultado=ignorado`
  - `reason_code=final_mode_not_cool`.

### Aprendizaje aplicado cuando el evento es válido
- Ajuste contextual ON: **`learning_step=-0.25`** sobre bucket contextual `cool`.
- En el mismo evento válido se aplica además ajuste de histéresis ON en:
  - `input_number.ac_dda_cool_delta_on_bucket_*`
  - respetando saturación operativa vigente.
- Si no hay contexto previo usable, se usa contexto base (`ctx_default:presencia`) y se escribe aprendizaje en helpers `ac_dda_*` (sin bloquear por falta de branch/contexto histórico).

### Causas válidas de ignorado (mínimas)
- `auto_transition_active`: evidencia de transición AUTO realmente reciente/activa (flags/timestamp/token con respaldo temporal).
- `lock_activo`: lock crítico del ciclo.
- `out_of_scope_daytime_main`: evento fuera de horario diurno.
- `final_mode_not_cool`: consolidación final distinta de `cool`.
- `duplicate_event`: anti-duplicado por firma de evento ya registrada.

### Trazabilidad corta sugerida (`reason_code`)
- Caso aplicado: `reason_code=applied`, `Resultado=aplicado`, incluye valores finales aprendidos (`CtxOff`, `HysOn`).
- Caso fuera de horario: `reason_code=out_of_scope_daytime_main`, `Resultado=ignorado`.
- Caso colisión AUTO: `reason_code=auto_transition_active`, `Resultado=ignorado`.
- Caso modo final inválido: `reason_code=final_mode_not_cool`, `Resultado=ignorado`.

## 21. Contrato de `ac_dda_cycle_lock` con vencimiento y recuperación (2026-04-09)

### Qué activa el lock
- El lock transaccional `input_boolean.ac_dda_cycle_lock` se activa en los flujos que abren transición HVAC sensible:
  - ramas AUTO ON/OFF de `AC - Día dinámico aprendido (principal)`,
  - secado post-cool en `AC - Manual OFF guard + pausa 5 min`,
  - puente `off -> fan_only -> cool` en `AC - Manual ON guard + presencia temporal`.
- Cada activación escribe marca temporal en `input_datetime.ac_dda_cycle_lock_since`.

### Duración máxima esperada
- TTL operativo del lock: **180 s**.
- Si un guard manual detecta lock activo, sólo se considera bloqueante cuando:
  - lock activo, y
  - edad del lock `<= 180 s`.

### Recuperación automática de lock rancio
- Si la edad del lock supera TTL, se clasifica como **lock rancio**:
  - se libera lock,
  - se registra `lock_rancio_recuperado` (o `lock_rancio_recuperado_post60`),
  - el flujo manual ON continúa validación en vez de descartarse.
- Además existe watchdog cada minuto:
  - condición: `ac_dda_cycle_lock=on` sin flags AUTO activas (`ac_dda_on/off_por_automatizacion`) y sin transición reciente,
  - acción: apagar lock y registrar `lock_recovered_stale`.

### Regla de negocio explícita
- **Un Manual ON diurno válido no debe perderse por lock rancio.**
- Sólo se descarta por lock cuando el lock sigue vigente dentro de TTL (`reason=lock_activo`).

## 22. Matriz de detección Manual ON con estados puente (2026-04-09)

### Objetivo de la matriz
- Evitar pérdida de eventos reales cuando el `climate` transita por estados intermedios (`unknown`, `unavailable`, `fan_only`) antes de llegar a `cool`.
- Mantener trazabilidad completa: **todo evento candidato** debe terminar en una salida observable (logbook + notificación de estado).

### Triggers permitidos para abrir guard
1. **`off_direct`**
   - `from: off`
   - `to: [cool, heat, fan_only]`
   - `for: 2s`
2. **`cool_any`**
   - `to: cool` (sin `from` rígido)
   - `for: 2s`
3. **`bridge_unknown_unavailable`**
   - `from: [unknown, unavailable]`
   - `to: [cool, heat, fan_only]`
   - `for: 2s`

### Ventana de arranque manual (validación obligatoria)
- Se evalúa `from_state` inmediato con normalización:
  - `unknown/unavailable` se tratan como **`off` efectivo** para debounce de puente.
- Criterio de aceptación de arranque (`manual_startup_window_ok`):
  - `from_effective == off`, **o**
  - transición a `cool` desde `fan_only` dentro de una ventana corta (`startup_window_s=45`) para capturar carrera `off -> fan_only -> cool`.
- Si no cumple, se descarta con razón explícita:
  - `manual_guard_discard=sin_off_efectivo_previo`,
  - `manual_guard_discard=fan_only_bridge_fuera_ventana`,
  - o razón de trigger fuera de matriz.

### Consolidación y carrera `off -> fan_only -> cool`
- Si el evento inicia en `fan_only`, se mantiene consolidación de **30s**.
- Si permanece en `fan_only`, se ejecuta puente asistido (espera adicional de 12s + intento a `cool`).
- Si al cierre de consolidación/puente termina en `cool` dentro de horario diurno principal, se trata como Manual ON válido.

### Reglas de aprendizaje preservadas
- Aprendizaje ON sólo en horario **07:01–21:59**.
- Aprendizaje ON sólo si **modo final = `cool`**.
- Requisito base: encendido con evidencia de origen en `off` efectivo (directo o puente válido).
- Si no hay contexto previo usable, se usa bucket base (`ctx_default:presencia`) y se aprende.

### Matriz de observabilidad obligatoria (no perder trazabilidad)
1. **Inicio de guard**
   - Logbook: `hito=manual_on_detected` (siempre).
2. **Descartes tempranos (guard/startup)**
   - Logbook con razón específica.
   - Notificación móvil `Resultado=ignorado` + `Razón=<reason_code>`.
3. **Evento válido en evaluación**
   - Notificación móvil `Resultado=pendiente` (validando/consolidación).
4. **Cierre del flujo**
   - Si aplica aprendizaje/flujo válido: notificación final de continuidad (`pendiente` hacia learning/aplicación).
   - Si no aplica: notificación `ignorado` con motivo contractual.

### Casos de referencia (directos + puente)
- **Caso A — Directo válido:** `off -> cool`
  - Debe emitir: `manual_on_detected` + `pendiente` + cierre final trazable.
- **Caso B — Puente por disponibilidad:** `off -> unavailable -> cool` o `off -> unknown -> cool`
  - Debe tratarse como `off` efectivo si entra en ventana.
- **Caso C — Carrera mecánica:** `off -> fan_only -> cool`
  - Debe consolidar 30s; si termina en `cool`, válido.
- **Caso D — Ruido no válido:** `heat -> cool` sin evidencia reciente de `off`
  - Debe descartar con razón explícita (`sin_off_efectivo_previo`) y notificación.

## 23. Regla final de no contaminación Manual ON cuando el origen fue AUTO (2026-04-09)

### Regla de negocio obligatoria
- **Si el encendido proviene de automatización, nunca debe producir `AC Manual ON pendiente/aplicado` ni aprendizaje ON manual.**
- **La transición AUTO nunca puede cerrar como manual** (ni ON ni OFF), incluso si el resto de validaciones manuales parciales resultan positivas.
- **Precedencia obligatoria:** descarte por `auto_transition_active` tiene prioridad sobre cualquier validación manual restante.
- El descarte debe resolverse en guard/feedback con:
  - `manual_guard_discard=auto_transition_active` (guard),
  - `ignored_reason_code=auto_transition_active` (learning ON),
  - sin push de flujo manual para ese evento (solo trazas técnicas).

### Evidencia AUTO fuerte (criterio único para guard + learning ON)
Se considera `auto_transition_active` cuando exista cualquiera de estas señales dentro de ventana activa:
1. `input_boolean.ac_dda_on_por_automatizacion=on` o `input_boolean.ac_dda_off_por_automatizacion=on`.
2. `input_text.ac_dda_transition_token` utilizable con `input_datetime.ac_dda_transition_ts` reciente.
3. `input_datetime.ac_last_auto_ts` reciente para colisión transaccional.

### Campos de diagnóstico obligatorios para auditoría futura
En cada descarte por AUTO deben quedar, como mínimo, estos campos en logbook:
- `auto_flags_active`
- `auto_transition_token_recent`
- `transition_age_s`
- `auto_ts_age_s` (o `minutes_since_last_auto`)
- `auto_evidence_strong`
- `last_change_origin_raw`
- `manual_guard_discard_reason` o `ignored_reason_code`

### Reglas de integridad de trazabilidad
- No actualizar firma de evento manual válido (`input_text.ac_dda_learning_last_manual_on_signature`) cuando el descarte sea por `auto_transition_active`.
- Mantener la notificación ON válida únicamente en el flujo transaccional `Src=AutoON`.

## 24. Política final de notificación AUTO ON por ciclo real (2026-04-09)

### Política obligatoria
- **Cada ciclo AUTO ON real debe producir una notificación móvil, aunque los umbrales sean iguales al ciclo anterior.**
- Política final consolidada: **cada ciclo AUTO ON real notifica una vez al móvil**.

### Implementación consolidada
- El script transaccional `ac_dda_notify_on_transaccional` usa firma `cycle_signature_v2` con identificador único real de ciclo (token de transición y/o `ac_last_auto_ts` de alta precisión).
- El anti-duplicado sólo permite una omisión controlada dentro de ventana corta (15 s); fuera de esa ventana se reintenta envío para conservar la garantía por ciclo real.
- Antes del envío se registra telemetría mínima obligatoria en logbook:
  - `trace_id`
  - `cycle_signature_v2`
  - `last_signature`
  - `duplicate=true/false`
  - `branch`
- Hitos requeridos de trazabilidad en encendido AUTO válido:
  - `hito=notify_payload_ready`
  - `hito=notify_on_preparado`
  - `hito=notify_on_intentado`
  - `hito=notify_on_enviado`

### Guía rápida de diagnóstico (`trace_id` + `notify_stage`)
1. Buscar por `trace_id=<valor>` para seguir extremo a extremo un intento de AUTO ON (principal, emergencia o confirmación).
2. Validar secuencia por `notify_stage`:
   - `payload_ready`
   - `dedupe_check`
   - `send_attempt`
   - `send_result`
3. Interpretación de `send_result`:
   - `mobile_sent`: push móvil confirmado.
   - `mobile_failed`: canal móvil con error explícito.
   - `fallback`: se emitió `persistent_notification` + logbook observable.
   - `duplicate_omitted`: reintento inmediato del mismo ciclo dentro de 15 s.
4. Si `Src=AutoON` y el `climate` quedó en `cool`, debe existir al menos salida observable en logbook para el `trace_id` (sin salida silenciosa).

## 25. Hotfix + refuerzo de ciclo AUTO ON (2026-04-10)

### Causa raíz
- Se confirmaron omisiones silenciosas de push `Src=AutoON` por anti-duplicado en ventana corta, incluso cuando había un nuevo intento válido de ON automático con trazabilidad parcial.
- Además, cuando el canal móvil no devolvía acuse explícito (`success/error`), el flujo lo trataba como fallo definitivo, generando falsos negativos operativos.

### Cambio aplicado (Fase 1 + Fase 2 consolidadas)
1. **Hotfix inmediato en `ac_dda_notify_on_transaccional`**
   - Se desactiva la omisión por duplicado para `Src=AutoON` (la rama AUTO ON siempre ejecuta intento real de envío).
   - Se mantiene ventana de dedupe de 10 s para orígenes no AUTO ON.
   - Cada llamada `Src=AutoON` ejecuta `hito=notify_on_intentado` + `notify.mobile_app_samsung_s24`.
   - Si no hay acuse explícito de éxito/error, se registra `send_result=unknown_but_attempted` (no fallo definitivo).

2. **Arreglo robusto de firma por ciclo real (`cycle_signature_v2`)**
   - Firma normalizada: `token:<nonce>|auto_on_ts:<timestamp>|branch:<rama>|src:auto_on_v2`.
   - Token toma `input_text.ac_dda_transition_token` y, si falta, usa `no_token`.
   - `auto_on_ts` toma prioridad: `ac_last_auto_ts` → `ac_dda_transition_ts` → `ac_dda_cool_cycle_contract_started_at` → `now()`.
   - Misma estructura aplicada en:
     - `cool_normal_on`,
     - `cool_emergency_on`,
     - `AC - Día dinámico aprendido (confirmación notify AUTO ON)`.

### Observabilidad y depuración por `trace_id`
1. Buscar `trace_id=<valor>` en logbook.
2. Confirmar secuencia mínima:
   - `notify_stage=payload_ready`
   - `notify_stage=dedupe_check`
   - `notify_stage=send_attempt`
   - `notify_stage=send_result`
3. Interpretar `send_result`:
   - `mobile_sent`: acuse explícito del canal móvil.
   - `unknown_but_attempted`: intento ejecutado sin acuse explícito (considerar entregado intentado, no fallo definitivo).
   - `mobile_failed`: error explícito del canal, debe existir fallback (`persistent_notification`) + `notify_on_fallido`.
4. Si el AC queda en `cool` con `Src=AutoON`, debe existir trazabilidad de intento y resultado para ese `trace_id` (sin salida silenciosa).

## 26. Normalización YAML `choose/default` para reinicio limpio (2026-04-12)

### Objetivo
- Eliminar fallos de parseo por indentación inconsistente en ramas AC de `automations.yaml` durante reinicios.

### Ajuste aplicado
- Se normalizó la estructura de bloques `- choose:` para que:
  - cada opción `- conditions:` quede al nivel correcto dentro de `choose`,
  - cada `default:` quede al mismo nivel que la lista de opciones de `choose`,
  - cada lista bajo `default:` (por ejemplo `- service:`) quede anidada exactamente 2 espacios por debajo de `default:`.

### Alcance de la normalización
- Se corrigieron los bloques señalados en trazas de error (zona de líneas ~1428–1446 y ~2181–2199).
- Se aplicó la misma corrección a bloques equivalentes detectados en otras ramas AC para prevenir regresiones por desplazamientos de ±2 espacios.

### Resultado esperado
- `automations.yaml` queda consistente para validación YAML/`check_config`.
- Se evita recurrencia de errores de parseo por `choose/default` mal anidado en reinicios futuros.

## 27. Política final Manual ON diurno sin bloqueos por AUTO/lock (2026-04-12)

### Política operativa consolidada
- **Manual ON aprende siempre en horario diurno** (`07:01:00–21:59:00`) cuando existe evento manual consolidado válido.
- **Única espera funcional del flujo Manual ON:** consolidación/setpoint de **30 s** antes de cerrar el evento.
- Dentro del horario diurno se retiraron descartes funcionales por:
  - `auto_transition_active`
  - `lock_activo`
  - validaciones intermedias de bloqueo distintas a consolidación.
- Fuera de horario se mantiene descarte explícito con:
  - `Resultado=ignorado`
  - `Razón=out_of_scope_daytime_main`.

### Orden transaccional obligatorio para evitar carreras
1. Guard Manual ON consolida 30 s.
2. Se escribe primero `input_text.ac_dda_last_manual_event_type` en variante final válida (`manual_on_final_valid_*|trace_id=...`).
3. Luego se escribe `input_datetime.ac_dda_last_manual_on_ts` para disparar `AC - Learning - Manual ON feedback`, con semántica estricta: **`last_manual_on_ts = instante de cierre validado`**.
4. Learning ON lee el evento ya consolidado y evalúa aplicación en alcance diurno.

### Simplificación de Learning ON
- `valid_feedback` queda reducido al contrato funcional:
  - evento manual consolidado válido,
  - horario diurno en alcance.
- Anti-duplicado técnico se conserva vía firma (`duplicate_event`) para evitar doble aplicación accidental.
- Notificación final normalizada:
  - aplicado: `Resultado=aplicado`, `Razón=manual_on`.
  - fuera de alcance: `Resultado=ignorado`, `Razón=out_of_scope_daytime_main`.

### Ejemplos de trazabilidad para diagnóstico
- **Caso aplicado diurno**
  - Guard: `hito=manual_on_detected` → `hito=manual_on_validating` → `hito=manual_on_final`.
  - Learning: `hito=learning_on_applied` con `reason=applied` y `Src=ManualON Resultado=aplicado Razón=manual_on`.
- **Caso fuera de horario**
  - Guard: descarte `manual_guard_discard=out_of_scope_daytime_main` + push `Resultado=ignorado Razón=out_of_scope_daytime_main`.
  - Learning: `hito=learning_on_ignored` con `reason=out_of_scope_daytime_main`.


## 28. Semántica de cierre para `last_manual_on_ts` (2026-04-20)

### Definición exacta
- `input_datetime.ac_dda_last_manual_on_ts` representa **exclusivamente** el instante de cierre validado del evento Manual ON (timestamp `ts` posterior a consolidación).
- No debe usar el timestamp de detección inicial (`detected_ts`) porque ese valor ocurre antes del cierre transaccional.

### Impacto operativo
- Las firmas de deduplicación que consumen `input_datetime.ac_dda_last_manual_on_ts` deben reflejar cierre real del evento para evitar colisiones por detección temprana.
- El orden observable esperado permanece: `pendiente` → `capturado` → `aplicado|ignorado` en notificaciones y logbook.

## 29. Política de descartes visibles en Guard Manual ON (2026-04-20)

### Regla obligatoria
- **Ningún descarte en guard Manual ON puede ser silencioso; siempre debe dejar notificación o razón visible.**

### Aplicación mínima requerida
- Todo descarte en `AC - Manual ON guard + presencia temporal` debe registrar `logbook.log` con razón explícita.
- Cuando el descarte ocurra antes de la fase de consolidación/pending, debe emitirse además notificación móvil compacta con:
  - `Resultado=ignorado`
  - `Razón=<reason_code>`
  - `Trace=<trace_id>`

## 30. Regla operativa de tercera notificación obligatoria en Learning ON (2026-04-20)

### Regla obligatoria
- **La tercera notificación es obligatoria y no depende del éxito de escrituras auxiliares.**

### Alcance mínimo
- Aplica a `AC - Learning - Manual ON feedback`.
- La notificación final `AC Learning ON` debe ejecutarse tanto en resultado `aplicado` como `ignorado`.
- Fallas no críticas en escrituras de helpers/contexto/contrato deben quedar en trazabilidad controlada (`continue_on_error` + logbook) y no bloquear la tercera notificación.

## 31. Protocolo mínimo de observabilidad para Manual ON (2026-04-20)

### Secuencia obligatoria de hitos
- El flujo Manual ON debe dejar trazabilidad en este orden mínimo:
  1. `pendiente`
  2. `capturado`
  3. `learning_on_started`
  4. notificación final con resultado contractual.

### Resultados finales permitidos
- La salida final de `AC - Learning - Manual ON feedback` debe ser exactamente uno de:
  - `Resultado=aplicado`
  - `Resultado=ignorado`
  - `Resultado=error_controlado`

### Política de resiliencia mínima
- Los cálculos/escrituras previas a la notificación final deben ejecutarse con tolerancia a fallas (fallback + `continue_on_error`) para evitar abortos silenciosos.
- Si se detecta falla controlada interna, se debe registrar `hito=learning_on_internal_error` y continuar hasta emitir notificación final con `Resultado=error_controlado`.

### Diagnóstico temporal de disparo (uso puntual)
- Puede habilitarse una automatización temporal de diagnóstico sobre `input_datetime.ac_dda_last_manual_on_ts` para confirmar disparo inmediato con:
  - `AC Learning ON Triggered Trace=<trace_helper_actual>`
- Tras validar en producción/lab, debe permanecer desactivada para evitar ruido operativo.

## 32. Hard learning por anclaje en Manual ON cool (2026-04-20)

### Regla formal
Se activa **hard learning** únicamente cuando en `AC - Learning - Manual ON feedback` se cumple todo:
1. Evento Manual ON confirmado transaccionalmente por snapshot + `trace_id`.
2. Horario diurno en alcance.
3. Modo final consolidado `cool`.
4. `Tin_promedio_actual` está fuera del rango contractual vigente `[Off, On]`.
5. `Tin_promedio_actual` también queda fuera del rango esperado tras ajuste normal incremental `(-0.25)`.

Si no se cumple la condición dura, se aplica regla normal incremental (`learning_step=-0.25`).

### Fórmulas hard anchor
- `new_on = Tin_promedio_actual`
- `new_off = Tin_promedio_actual - 0.5`

Aplicar clamps de seguridad:
- `off_final = clamp(new_off, 22.0, 25.7)`
- `on_final = min(new_on, 26.2)`
- garantizar `on_final > off_final` (ajuste mínimo técnico de separación cuando aplique).

Se persiste en:
- `input_number.ac_dda_cool_cycle_contract_on`
- `input_number.ac_dda_cool_cycle_contract_off`
- `input_text.ac_dda_cool_cycle_contract_reason` con `reason_code=manual_on_hard_anchor_applied`.

### Precedencia obligatoria
1. Validación transaccional/snapshot (`trace_id`, `event_type`, consistencia).
2. Descarte por horario o modo final distinto de `cool`.
3. Evaluación de hard learning.
4. Si hard no aplica, aprendizaje normal incremental.

### Códigos de razón y tipo (salida final)
- `manual_on_normal_applied` (aplicado normal).
- `manual_on_hard_anchor_applied` (aplicado hard).
- `out_of_scope_daytime_main`, `final_mode_not_cool`, `manual_trace_mismatch`, etc. (ignorado).
- `learning_on_internal_error` (error_controlado con finalización forzada).

### Ejemplos numéricos
- **Caso normal:** contrato `Off/On=24.2/24.8`, `Tin=24.5`
  - Está dentro del contrato → no hard.
  - Se evalúa regla normal `-0.25` en bucket/contexto.
- **Caso hard (anclaje):** `Tin=24.5` fuera de contrato y también fuera del rango normal ajustado
  - `new_on=24.5`, `new_off=24.0`
  - Resultado: `Off/On=24.0/24.5` (si no requiere clamp adicional).

### Matriz mínima de regresión operativa
1. **Caso A**: Manual ON válido dentro de rango → `Resultado=aplicado`, `hard=no`.
2. **Caso B**: Manual ON cool fuera de rango actual y normal → `Resultado=aplicado`, `hard=yes`, `On=Tin_actual`.
3. **Caso C**: fallo controlado en helper dinámico → `Resultado=error_controlado` o `aplicado` con fallback, siempre con notificación final.
4. **Caso D**: nunca truncar en dos notificaciones; secuencia observable mínima:
   - `pendiente` → `capturado` → `learning_on_started` → `notificación final`.

---

## 7. Matriz de propiedad de helpers (AC-DDA)

Fecha de actualización: **2026-05-14**.

| helper | owner writer | readers permitidos | motivo | fecha |
|---|---|---|---|---|
| `input_datetime.ac_dda_last_auto_ts` | `AC - Día dinámico aprendido (principal)` | confirmación AUTO ON, learning ON/OFF, guards manuales | timestamp contractual de última acción AUTO bajo namespace exclusivo DDA | 2026-05-14 |
| `input_text.ac_dda_last_auto_branch` | `AC - Día dinámico aprendido (principal)` | confirmación AUTO ON, learning ON/OFF, guards manuales | rama de decisión AUTO para trazabilidad y filtros | 2026-05-14 |
| `input_text.ac_dda_last_auto_action` | `AC - Día dinámico aprendido (principal)` | learning ON/OFF, guards manuales | acción AUTO consolidada para correlación temporal | 2026-05-14 |
| `input_datetime.ac_dda_last_manual_off_ts` | `AC - Manual OFF guard + pausa 5 min` | learning manual OFF | trigger contractual de learning OFF | 2026-05-14 |
| `input_datetime.ac_dda_last_manual_on_ts` | `AC - Manual ON guard + presencia temporal` | learning manual ON | trigger contractual de learning ON | 2026-05-14 |
| `input_text.ac_dda_last_manual_on_pending_signature` | `AC - Manual ON guard + presencia temporal` | `AC - Learning - Manual ON feedback` | deduplicación temprana por firma de sesión manual ON | 2026-05-15 |
| `input_text.ac_dda_last_manual_on_trace_confirmed` | `AC - Manual ON guard + presencia temporal` | `AC - Learning - Manual ON feedback` | correlación transaccional del `trace_id` manual ON consolidado | 2026-05-15 |
| `input_text.ac_dda_last_manual_on_snapshot` | `AC - Manual ON guard + presencia temporal` | `AC - Learning - Manual ON feedback` | snapshot inmutable (`trace_id|event_type|final_mode|ts`) para validación estricta | 2026-05-15 |
| `input_text.ac_dda_last_notify_status` | `AC - Manual ON guard + presencia temporal` | watchdog | estado de secuencia notify/manual-on | 2026-05-14 |

### Reglas de naming para nuevos helpers exclusivos

1. Prefijo obligatorio: `ac_dda_`.
2. Sufijo de rol de flujo cuando aplique:
   - `_manual_on_*`
   - `_manual_off_*`
   - `_auto_on_*`
   - `_watchdog_*`
3. Si un helper solo existe para una automatización secundaria, agregar el sufijo `_owner_<slug_corto_automatizacion>`.
4. No reutilizar helpers globales legacy (`ac_last_auto_*`) para escrituras funcionales nuevas.

### Protocolo para automatizaciones secundarias futuras

1. Declarar helper exclusivo por cada dato persistente nuevo.
2. Documentar `owner writer` y `readers` en esta matriz antes de activar la automatización.
3. Si se requiere compartir escritura, solo permitirlo como excepción **shared by design** con razón transaccional explícita y validación de integridad.
4. Activar chequeo de `owner mismatch` con `logbook.log` para todo helper crítico nuevo.

### Ejemplos de migración (antes/después)

- **Antes (legacy/global):**
  - `input_datetime.ac_last_auto_ts`
  - `input_text.ac_last_auto_action`
- **Después (AC-DDA exclusivo):**
  - `input_datetime.ac_dda_last_auto_ts`
  - `input_text.ac_dda_last_auto_action`

Compatibilidad de transición:
- Se permite lectura temporal de legacy solo en diagnósticos históricos.
- No se permite escritura cruzada a `ac_last_auto_*` desde automatizaciones AC-DDA activas.

## 33. Guard horario único para secundarias AC-DDA (2026-05-14)

### Expresión única reutilizable (fuente común)
- `time_guard`: `{{ now().strftime('%H:%M:%S') >= '07:01:00' and now().strftime('%H:%M:%S') <= '21:59:00' }}`
- Alcance contractual diurno principal: **07:01:00–21:59:00**.
- La misma plantilla debe usarse en todas las automatizaciones secundarias relevantes para evitar divergencias.

### Precedencia obligatoria
1. Evaluar `time_guard` al inicio de la secundaria.
2. Solo si `time_guard=true`, ejecutar consolidación/manual workflow.
3. Solo si `time_guard=true`, emitir notificaciones manuales de éxito/pendiente.

### Tabla: Secundaria vs alcance horario

| Secundaria | ¿Ejecuta fuera de horario? | ¿Notifica fuera de horario? | Razón estándar |
|---|---|---|---|
| `AC - Manual ON guard + presencia temporal` | No | No | `out_of_scope_daytime_main` |
| `AC - Manual OFF guard + pausa 5 min` | No | No | `out_of_scope_daytime_main` |
| `AC - Learning - Manual ON feedback` | No | No | `out_of_scope_daytime_main` |
| `AC - Learning - Manual OFF feedback` | No | No | `out_of_scope_daytime_main` |
| Secundarias derivadas de confirmación/manual notify | No (si mutan estado contractual) | No | `out_of_scope_daytime_main` |

### Reglas anti-efecto-colateral fuera de horario
- No mutar helpers de resultado manual final.
- No actualizar firmas de deduplicación manual.
- No disparar tercera notificación de learning manual.
- Se permite solo traza técnica mínima opcional en logbook con razón compacta:
  - `out_of_scope_daytime_main`.

## 34. Reset manual de aprendizaje (2026-05-14)

### Objetivo
- Incorporar una automatización de mantenimiento manual para limpiar aprendizaje AC-DDA sin afectar seguridad operativa ni estado físico del equipo.

### Automatización
- Alias: `AC - Mantenimiento - Reset manual aprendizaje AC-DDA`.
- Disparo manual exclusivo: `event_type: input_button.press` sobre `input_button.ac_dda_reset_learning_manual`.
- Guardia de seguridad obligatoria: solo ejecuta si `input_boolean.ac_dda_cycle_lock=off`.
- Compatible con mantenimiento fuera de horario (sin guard horario), y fija `input_text.ac_dda_last_change_origin=maintenance_reset_manual`.

### Modo simulación (dry-run)
- Flag previo: `input_boolean.ac_dda_reset_dry_run`.
- Si está `on`, reporta alcance de helpers a resetear pero no escribe cambios.

### Capas de reset (orden obligatorio)
1. **Capa A — aprendizaje contextual**
   - `input_text.ac_dda_cool_contextual_learning_map`
   - `input_text.ac_dda_cool_effective_setpoint_map`
   - `input_text.ac_dda_cool_cycle_contract_bucket`
   - Dinámicos por patrón:
     - `input_text.ac_dda_cool_learning_bucket_*`
     - `input_text.ac_dda_cool_delta_*`
     - `input_text.ac_dda_cool_effective_sp_bucket_*`
2. **Capa B — trazas manuales**
   - `input_datetime.ac_dda_last_manual_on_ts`
   - `input_datetime.ac_dda_last_manual_off_ts`
   - `input_text.ac_dda_last_manual_event_type`
   - `input_text.ac_dda_learning_last_manual_on_signature`
   - `input_text.ac_dda_learning_last_manual_off_signature`
   - `input_text.ac_dda_last_manual_on_snapshot`
   - `input_text.ac_dda_last_manual_on_trace_confirmed`
   - `input_text.ac_dda_last_manual_on_pending_signature`
   - `input_datetime.ac_dda_last_manual_final_ts`
   - `input_datetime.ac_dda_last_manual_feedback_ts`
   - `input_text.ac_dda_last_manual_learning_type`
   - `input_text.ac_dda_last_manual_final_mode`
   - `input_text.ac_dda_last_manual_final_fan`
3. **Capa C — contrato cool aprendido (baseline seguro)**
   - `input_number.ac_dda_cool_cycle_contract_off = 24.2`
   - `input_number.ac_dda_cool_cycle_contract_on = 24.8`
   - `input_number.ac_dda_cool_off_learned = 24.2`
   - Valores dentro de clamps contractuales (`off` en `[22.0,25.7]`, `on <= 26.2` y `on > off`).

### Helpers preservados (no reset)
- Flags de transición/seguridad inmediata (`ac_dda_cycle_lock`, flags AUTO ON/OFF).
- Compuertas maestras de habilitación global.
- Entidades físicas (`climate.*`, sensores) y estado real del equipo.

### Observabilidad mínima obligatoria
- `logbook.log` de inicio/fin con `trace_id` y contador de helpers objetivo.
- Notificación S24 compacta final con:
  - `Resultado=aplicado|simulacion`
  - `Helpers_reset=<n>`
  - `Trace=<id>`
- Escrituras no críticas en modo tolerante con `continue_on_error` para evitar abortos silenciosos.

### Procedimiento operativo
1. **Pre-check**
   - Confirmar `input_boolean.ac_dda_cycle_lock=off`.
   - Definir `input_boolean.ac_dda_reset_dry_run=on` para validación inicial.
2. **Ejecución**
   - Presionar `input_button.ac_dda_reset_learning_manual`.
3. **Validación post-reset**
   - Revisar en logbook `hito=reset_start` y `hito=reset_end` con mismo `trace_id`.
   - Verificar notificación S24 final y conteo de helpers.
4. **Rollback básico**
   - Si se requiere, restaurar contrato baseline manualmente:
     - `off=24.2`, `on=24.8`, `off_learned=24.2`.
   - Confirmar `input_text.ac_dda_last_change_origin` acorde al origen operativo posterior.

---

## Incidente de parseo YAML/Jinja (2026-05-14)

- **Síntoma exacto**: Home Assistant reportó `while scanning for the next token found character '%' that cannot start any token`.
- **Ubicación aproximada**: `automations.yaml` alrededor de la línea **5666** (bloque `AC Manual OFF`, mensaje de logbook largo con `trace_id`).
- **Causa raíz**: uso de `strftime('%Y%m%d%H%M%S')` dentro de un escalar YAML entre comillas simples; las comillas internas no escapadas rompían el token YAML y dejaban `%` fuera de contexto válido.
- **Corrección aplicada**: se cambió a `strftime("%Y%m%d%H%M%S")` dentro de la plantilla Jinja para mantener la cadena YAML válida sin alterar la lógica funcional.
- **Validación realizada**:
  - verificación del bloque objetivo (líneas 5620–5710) y de la estructura `choose/default` cercana;
  - intento de `check_config` no disponible en este entorno (`hass` ausente);
  - parseo YAML global con `PyYAML` ya no falla en el punto 5666 y ahora reporta un error independiente preexistente en línea 7630 (escape en doble comilla), fuera del alcance de este fix.

### Regla preventiva
Toda plantilla larga (especialmente con Jinja + formatos de fecha o `%`) debe declararse en bloque YAML `>` o `|`, con cierre explícito de delimitadores (`{{ ... }}` / `{% ... %}`) y filtros defensivos (`|default(...)`, `|float(0)`, `|int(0)`) para variables potencialmente indefinidas.

## Incidente de escape inválido en YAML (2026-05-14)

- **Síntoma exacto**: Home Assistant reportó `unknown escape character ':'` al validar `automations.yaml`.
- **Ubicación aproximada**: `automations.yaml` alrededor de las líneas **7630–7632** (variable `dynamic_learning_buckets`).
- **Causa raíz**: patrón regex dentro de string YAML en comillas dobles con `\.` (`'^input_text\.ac_dda...'`); en YAML doble comilla, `\.` es un escape inválido y dispara error de parseo.
- **Corrección aplicada**: se migró la plantilla a bloque multilinea `>` y se eliminó el backslash innecesario en el regex (`'^input_text.ac_dda...'`), preservando la misma lógica de match.
- **Validación realizada**:
  - revisión del bloque de contexto `7605–7650`;
  - búsqueda preventiva en todo `automations.yaml` de secuencias sospechosas (`\:`, `\{{`, `\{%`, `\"`), sin hallazgos;
  - `hass --script check_config` no disponible en este entorno (`hass` ausente), por lo que la validación final debe correrse en el host de Home Assistant antes del reinicio.

### Regla preventiva
Evitar escapes manuales en strings YAML largas con comillas dobles cuando contienen regex/Jinja; preferir bloque `>` y plantillas limpias sin backslashes innecesarios.

## Incidente de restauración y corrección limitada de automatizaciones (2026-05-15)

- **Causa raíz**:
  - `automations.yaml` quedó contaminado con contenido de diff en una revisión posterior, por lo que se restauró una base íntegra desde una versión previa válida del historial (`ead1100`, anterior al rango afectado por `ef33330`).
  - Dentro de dos automatizaciones específicas, había literales Jinja inválidos `''n/a''` en bloques template multilinea (`>-`), provocando error de parser Jinja (`expected token 'end of print statement', got 'n'`).
- **Alcance limitado del fix**:
  - Solo se tocaron los alias:
    1. `AC - Noche dinámico (OpenWeather) + Presencia estable + Fan Low + Notificaciones`
    2. `AC - Día dinámico aprendido (principal)`
  - No se modificaron otras automatizaciones fuera de esos bloques (salvo la restauración íntegra del archivo base).
- **Líneas/variables corregidas**:
  - En alias nocturno:
    - `setpoint_fijo_contractual` fallback: `''n/a''` → `'n/a'`.
  - En alias principal diurno:
    - `cool_cycle_contract_snapshot`: campos `On`, `Off`, `OffSensor`, `SP`.
    - `cool_cycle_final_message`: campos `Tin`, `Tout`, `H`, `On`, `Off`, `SP`, `Fan`.
    - Rama `emergency_off`: normalización equivalente en `cool_cycle_contract_snapshot`, `cool_cycle_real_off_detail` y `cool_cycle_final_message`.
- **Evidencia de validación**:
  - Validación YAML general ejecutada con `PyYAML`: carga exitosa como lista de 37 automatizaciones.
  - `Home Assistant Check Configuration` intentado en host con `hass --script check_config -c /workspace/Home-Assistant`, pero el binario `hass` no está disponible en este entorno de trabajo.
- **Fecha**: 2026-05-15.

## Incidente de quoting Jinja en bloque OFF del alias principal (2026-05-15)

- **Síntoma exacto**: Home Assistant marcó error de plantilla/Jinja por fallback inválido en bloque de variables del alias `AC - Día dinámico aprendido (principal)`.
- **Ubicación funcional**: rama de apagado `cool_normal_off` en `actions -> choose -> sequence -> variables`, incluyendo:
  - `cool_cycle_contract_snapshot`
  - `cool_cycle_final_message`
  - `cool_cycle_off_cause_detail`
- **Causa raíz**: uso de literal `''n/a''` dentro de expresiones Jinja en escalares template multilinea (`>-` / string template), lo que genera quoting ambiguo al evaluar el parser.
- **Corrección aplicada**:
  - normalización de fallback a `'n/a'` en los campos de snapshot/notificación:
    - `On`, `Off`, `OffSensor`, `SP`, `Tin`, `Tout`, `H`, `Fan`,
  - y en detalle de causa OFF (`cool_cycle_off_cause_detail`) para `Prom/t1/t2`.
- **Validación ejecutada en entorno**:
  - revisión de ocurrencias dentro del alias objetivo;
  - validación sintáctica YAML del archivo completo con `PyYAML` (`yaml.safe_load`) luego del ajuste.
- **Fecha**: 2026-05-15.

## Actualización de robustez (2026-05-15)

- Se reforzó la automatización `AC - Learning - Manual OFF feedback` para evitar warnings por variables indefinidas en plantillas Jinja.
- Se agregó una semilla defensiva `apply_learning_seed: false` y se definió `apply_learning` de forma explícita con fallback seguro.
- Se actualizaron expresiones derivadas para usar `apply_learning | default(false)` en:
  - `learning_off_discard_reason`
  - `delta_learning`
  - `learning_type`
  - mensajes de logbook/notificación con `apply=yes|no`
  - condiciones `if apply_learning` / `value_template`.
- Se preserva el contrato funcional de salida:
  - `Resultado=aplicado|ignorado`
  - `reason_code=applied|<ignored_reason_code>`.

### Identificadores clave tocados
- `apply_learning_seed`
- `apply_learning`
- `learning_off_discard_reason`
- `learning_type`
- `delta_learning`
- `ignored_reason_code`
- Mensajes de `AC Learning Manual OFF` (logbook y notificación móvil).

## Endurecimiento de `sensor.minima_23_a_07` (2026-05-15)

- **Fuente que generaba `unknown`**:
  - `sensor.pronostico_horario_casa` atributo `forecast` vacío/no disponible.
  - muestras horarias sin `temperature`/`native_temperature` numérico en la franja 23:00–07:00.
- **Mitigación aplicada**:
  - validación defensiva `is_number(t)` antes de agregar temperaturas al cálculo del mínimo;
  - normalización de salida con fallback numérico (`sensor.openweathermap_temperature | float(0)`) cuando no hay forecast o no hay muestras válidas.
- **Resultado**:
  - el `state` del sensor queda siempre numérico en todas las ramas (`if/else`), manteniendo `unit_of_measurement: "°C"` coherente.

## Ajuste nocturno de anticipación por rocío/confort (2026-05-15)

- **Objetivo del ajuste**:
  - reducir la ventana de disconfort (sensación de sudor) antes del primer encendido nocturno en `cool`, sin romper límites de seguridad térmica ya vigentes.
- **Parámetros modificados (alias nocturno)**:
  - se agregó sesgo de anticipación `cool_on_dew_bias: -0.2` aplicado al cálculo de encendido nocturno ligado a rocío/confort;
  - se elevó histéresis nocturna a `cool_night_hysteresis: 0.7`;
  - el umbral `cool_on` nocturno normal ahora se deriva de `cool_normal_off_dynamic + h + bias` y conserva guardas al no superar el `cool_on_base` previo;
  - la rama `cool` de emergencia también aplica el mismo sesgo de rocío/confort (`cool_emergency_on` incorpora `cool_on_dew_bias`) para mantener consistencia entre ramas de encendido.
- **Impacto esperado**:
  - encendido nocturno más temprano en contexto húmedo/bochornoso;
  - menos ciclos por separación ON/OFF más amplia (`h=0.7`);
  - transición más estable manteniendo criterio `on > off`.
- **Observabilidad/notificaciones**:
  - mensajes compactos S24 de alias nocturno actualizados para mostrar `On`, `Off` y `H` con formato de 1 decimal.
- **Validación operativa recomendada (post-despliegue)**:
  - observar durante **2–3 noches**:
    1. hora del primer encendido nocturno,
    2. reducción de sensación de sudor previa al encendido,
    3. número de ciclos ON/OFF por noche;
  - si persiste calor o aparece sobreenfriamiento, ajustar `cool_on_dew_bias` en pasos de `±0.1 °C`.

## Incidente de quoting YAML/Jinja en notificación AUTO OFF (2026-05-15)

- **Síntoma potencial**: bloque de mensaje largo en `automations.yaml` alrededor de la línea **891** con alto riesgo de colisión por comillas al usar plantilla Jinja embebida en escalar YAML con comillas simples.
- **Causa raíz exacta**: el mensaje `AC AUTO OFF` usaba un string YAML de una sola línea con múltiples literales Jinja escapados como `''...''` (por ejemplo `''cool_emergency_off''`, `''n/a''`), lo que vuelve frágil el parseo y dificulta mantenimiento.
- **Bloque corregido**: rama `cool` de `AC AUTO OFF` (alrededor de `automations.yaml:883-902`) migrada a bloque multilinea `>-` con delimitadores Jinja completos y comillas internas consistentes (`'...'`) dentro de `{{ ... }}`.
- **Validación ejecutada**:
  - parseo YAML completo tras el cambio (`yaml.safe_load`) exitoso: lista de 37 automatizaciones;
  - en este entorno no se ejecutó reinicio de Home Assistant ni `hass --script check_config` (binario no disponible).

## Endurecimiento defensivo de `cool_cycle_contract_active` (2026-05-15)

- **Objetivo**: eliminar riesgos de `UndefinedError`/warnings cuando `cool_cycle_contract_active` sea referenciado en condiciones, logs o ramas `choose/default` antes de quedar materializada en el contexto de templates.
- **Cambios aplicados en `automations.yaml`**:
  - Se agregó semilla explícita:
    - `cool_cycle_contract_active_seed: false`
  - Se separó el cálculo contractual en variable dedicada:
    - `cool_cycle_contract_active_computed`
  - Se normalizó la variable operativa con fallback defensivo:
    - `cool_cycle_contract_active: "{{ cool_cycle_contract_active_computed | default(cool_cycle_contract_active_seed) }}"`
  - Se forzó fallback explícito `| default(false)` en usos de:
    - mensajes de auditoría/log (`contract_active_audit`, `cool_cycle_contract_active=...`),
    - condición template de desvío contractual en rama `cool`,
    - compuerta derivada `off_gate_contract_active`.
- **Cobertura funcional**:
  - ninguna rama `choose/default` dependiente de `cool_cycle_contract_active` queda sin valor booleano seguro;
  - se preserva el comportamiento contractual normal cuando el cálculo sí está disponible.
- **Validación en este entorno**:
  - se confirmó inventario de ocurrencias y presencia de fallback explícito con búsqueda dirigida;
  - no fue posible validar recarga/reinicio de Home Assistant ni `check_config` dentro de este contenedor (requiere host HA con binarios/entorno runtime).

### Endurecimiento operativo AC-DDA (mayo 2026)
- Se establece una compuerta explícita `manual_on_lock_active` de **60 s** tras detectar `Manual ON` en `cool`.
- Durante esa ventana, la automatización principal no debe ejecutar intervenciones invasivas de cambio inmediato de modo (ej. `cool -> fan_only`), salvo excepciones de seguridad dura del equipo.
- El cierre de ventana de 60 s debe consolidar snapshot final inmutable para Learning ON con: `trace_id`, `event_type`, `final_mode`, `final_fan`, `final_setpoint`, `lock_started_ts` y `ts`.
- La confirmación de Learning ON se mantiene transaccional por `trace_id` + snapshot correlacionado; no se confirma desde estado global mutable.

### Política dura de aprendizaje por origen humano
- `AC - Learning - Manual ON feedback` y `AC - Learning - Manual OFF feedback` sólo aplican aprendizaje cuando el origen del evento es humano verificable (`manual_on` / `manual_off`) y sin evidencia de transición automática reciente.
- Eventos automáticos (`auto_on`, `auto_off`, ramas automáticas, transiciones técnicas) se clasifican como **no aprendibles**: conservan telemetría y trazabilidad, pero no modifican mapas ni umbrales.
- Todo ciclo ON/OFF debe cerrar obligatoriamente en resultado terminal único: `aplicado`, `ignorado` o `error_controlado`, con `Trace`, `Policy` y `Reason`.

### Reglas de sintaxis defensiva YAML/Jinja
- En mensajes extensos usar `message: >-`.
- Usar `'n/a'` como literal estándar para no disponible.
- Aplicar filtros defensivos `|default`, `|float`, `|int` en campos propensos a indefinidos.
- Evitar quoting frágil en regex/templates y verificar delimitadores Jinja balanceados en cada alias modificado.

## Incidente de mapping/scalar en bloque AC-DDA OFF (2026-05-15)

- **Fecha**: 2026-05-15.
- **Líneas afectadas**: `automations.yaml` alrededor de **2888–2891** (y normalización adicional del mismo bloque `cool_normal_off_skip` en ~3199).
- **Síntoma**: error de parser tipo `expected <block end>, but found <scalar>` al evaluar mensajes largos con Jinja incrustado.
- **Causa raíz**:
  - escalar YAML en una sola línea entre comillas simples con templates Jinja extensos;
  - mezcla frágil de quoting interno (`'n/a'`) dentro del mismo escalar;
  - alto riesgo de desalineación mapping/scalar al envolver líneas.
- **Patrón seguro aplicado**:
  - migración de mensajes largos a `message: >-`;
  - quoting consistente en Jinja (`'n/a'`);
  - conservación de delimitadores completos `{{ ... }}`;
  - uso/retención de filtros defensivos (`|default(false)` en bandera contractual).
- **Checklist preventivo corto**:
  1. Si `message` contiene múltiples `{{ ... }}` o condicionales inline, usar `>-`.
  2. No mezclar escalar YAML con comilla simple externa + fallback internos sin revisar parseo.
  3. Validar sintaxis YAML completa tras cada cambio de bloques `choose/sequence/default`.
  4. Revisar específicamente alias AC-DDA tocados en el diff antes de recargar HA.

## Incidente de sintaxis YAML en bloques AC-DDA (2026-05-15)

- **Fecha**: 2026-05-15.
- **Rangos corregidos**:
  - `automations.yaml:2865–2915` (error reportado en 2888/2891).
  - `automations.yaml:3830–3875` (error reportado en 3846/3862).
- **Causas raíz por rango**:
  - **Rango A**: estructura `default` desalineada con su rama `choose`, provocando riesgo de cierre incorrecto de mapping y colisión `block end/scalar`.
  - **Rango B**: combinación de indentación frágil en `default` + string template muy largo con quoting mixto (`''n/a''` / `'n/a'`) dentro de escalares inline.
- **Patrón de corrección aplicado**:
  - normalización de jerarquía `choose -> - conditions -> sequence` y `default` al mismo nivel de ramas;
  - migración de templates largos a `message: >-` / `>-'` multilinea;
  - normalización de fallback a `'n/a'` consistente;
  - preservación de delimitadores Jinja completos (`{{ ... }}`, `{% ... %}`) y filtros defensivos existentes.
- **Mini-checklist preventivo**:
  1. En cada `choose`, revisar que `default:` esté alineado con las ramas `- conditions:`.
  2. Si un `message`/template supera una línea o mezcla quotes, convertir a `>-`.
  3. Evitar `''n/a''`; usar siempre `'n/a'` dentro de Jinja.
  4. Validar YAML completo tras tocar `sequence/default`.
  5. Revalidar específicamente los rangos corregidos antes de recarga/reinicio.

## Registro técnico de incidente YAML (2026-05-15)

- **Fecha:** 2026-05-15
- **Archivo afectado:** `automations.yaml`
- **Rangos corregidos por reconstrucción de bloque:**
  - A: 1435–1468
  - B: 2868–2920
  - C: 3705–3778
  - D: 3838–3872
- **Causa raíz por tipo:**
  - `collection ?`: mezcla de niveles de lista/mapa en ramas `choose/default` y plantillas embebidas con estructura frágil.
  - `mapping/scalar`: escalares largos inline y comillas conflictivas dentro de Jinja/YAML.
- **Patrón aplicado:** reconstrucción completa de bloques lógicos, normalización de `choose/default`, migración de mensajes/plantillas largas a multilinea (`>-`) y endurecimiento defensivo en expresiones (`default`, `float`, `int`).

### Checklist preventivo obligatorio antes de reiniciar

1. Validar sintaxis YAML global completa (`automations.yaml`) y no solo el rango tocado.
2. Revisar cada `choose` para asegurar formato:
   - `choose:`
     - `- conditions:`
       - ...
       - `sequence:`
         - ...
   - `default:`
     - ...
3. Evitar escalares Jinja largos en una sola línea cuando incluyan comillas mixtas.
4. Usar `>-` en `message` / `value_template` con contenido extenso.
5. Confirmar delimitadores Jinja completos: `{{ ... }}` y `{% ... %}`.
6. Verificar defaults defensivos en variables opcionales: `|default('n/a')`, `|float(0)`, `|int(0)`.
7. Ejecutar check de configuración de Home Assistant antes de reiniciar.

## Incidente consolidado de parseo YAML (2026-05-15 00:00 UTC)

- **Rangos intervenidos en esta pasada**:
  - A: `1435–1470`
  - B: `2868–2925`
  - C: `3705–3778`
  - D: `3838–3875`
  - E: `4978–5005`
- **Causa raíz por rango**:
  - A/C: riesgo estructural de `block collection` por ramas `choose/default` y bloques extensos con indentación frágil.
  - B/D/E: `block mapping` con escalares largos inline y quoting Jinja mixto (`''n/a''`, formatos inline extensos).
- **Patrón aplicado**:
  - reconstrucción por bloque completo en zonas afectadas;
  - normalización de `default` al nivel correcto de `choose`;
  - migración de mensajes largos a `message: >-`;
  - quoting defensivo (`'n/a'`) y filtros (`|default(...)`, `|float(0)`).
- **Checklist de validación previa a restart**:
  1. Parseo YAML global después de cada bloque corregido.
  2. Revisión de forma canónica `choose -> sequence -> default`.
  3. Evitar strings Jinja gigantes inline con comillas mixtas.
  4. Verificación final con `check_config`/restart controlado en host HA.

## Rollback controlado para cascada YAML en `automations.yaml` (2026-05-15)

- **Objetivo operativo**: detener la cascada de errores de parser y recuperar un estado reiniciable priorizando rollback seguro sobre parches puntuales.
- **Errores observados antes del rollback**:
  - `1453/1454` (`block collection`, `?`)
  - `3721/3769` (`block collection`, `?`)
  - `3846/3862` (`block mapping`, `<scalar>`)
  - `4993/4994` (`block mapping`, `<scalar>`)
  - `5127/5283` (`block mapping`, `<scalar>`)

### Evidencia y punto de recuperación
- Se congelaron cambios directos sobre el archivo roto.
- Se preservó evidencia íntegra:
  - `automations.yaml.broken.20260515T030539Z`
- Se identificó y usó como baseline sintáctico válido el contenido de `automations.yaml` en el commit:
  - `608990dd5ff854ff3556f0ecc6889b4561af3656`

### Acción de recuperación aplicada
1. Restauración completa de `automations.yaml` desde baseline válido (`git checkout <commit> -- automations.yaml`).
2. Validación de parseo YAML global del archivo restaurado con `ruby/psych`:
   - resultado: `YAML_OK`.

### Estado posterior
- Se recuperó estado de parseo limpio de `automations.yaml` en este workspace.
- No se avanzó con microparches sobre líneas sueltas del archivo roto para evitar recaída de estructura.

### Regla operativa reforzada (obligatoria)
- **Sin validación YAML global exitosa no se continúa al siguiente bloque.**
- Reaplicación de cambios funcionales solo por **bloque lógico completo** (`choose/sequence/default`), nunca por edición puntual de líneas aisladas.
- En bloques con templates extensos:
  - usar `message: >-` y `value_template: >-`,
  - usar fallback `'n/a'` consistente,
  - no dejar `?` en posición estructural,
  - verificar delimitadores Jinja completos (`{{ ... }}`, `{% ... %}`).

### Nota de validación operativa final
- En este entorno no está disponible `hass --script check_config`, por lo que la confirmación de reinicio de Home Assistant debe ejecutarse en el host runtime de HA después del despliegue.

## Incidente de reconstrucción AC-DDA (2026-05-15)

- **Fecha/hora**: 2026-05-15T19:29:42Z.
- **Rango intervenido**: `automations.yaml` ~4145–4505 (alias `AC - Día dinámico aprendido (principal)`).
- **Causa raíz**: fragilidad de estructura en zona contigua `choose/sequence/default` + plantillas largas inline con quoting mixto.
- **Corrección aplicada**:
  - respaldo previo `automations.yaml.pre_fix_20260515T192942Z.bak`;
  - normalización a multilinea `>-` de templates largos (`context_key_v2`, helpers dinámicos `replace(':','_')`, cálculos `ac_dda_*`, `cool_on`, `cool_off_validated`, `cool_on_validated`);
  - normalización de quoting defensivo en plantillas compactas adyacentes.
- **Validación**:
  - `hass --script check_config` no disponible en este contenedor.
  - parseo YAML con `psych` pendiente de limpieza final en el bloque afectado.

### Regla preventiva explícita
- **En AC-DDA, templates largos siempre en `>-` y cambios por bloque lógico completo**.

## Incidente AC-DDA `choose/default` + templates largos (2026-05-15)

- **Fecha/hora**: 2026-05-15T19:44:12Z.
- **Archivo/rango corregido**: `automations.yaml`, bloque del alias `AC - Día dinámico aprendido (principal)` en torno a **4161–4505**.
- **Causa raíz**:
  - riesgo de quiebre de parser en la zona de variables por plantillas largas inline y quoting frágil;
  - `cool_contract_invalid_reason` tenía cierre de comilla residual al final del template;
  - área sensible alrededor de `cool_related_daytime_helper` y derivadas (`cool_effective_sp_inconsistency_reason`) con alto acoplamiento de Jinja/YAML.
- **Patrón aplicado**:
  - respaldo previo completo: `automations.yaml.pre_fix_20260515T194412Z.bak`;
  - normalización de templates largos a bloque `>-` en el rango intervenido (`cool_related_daytime_bucket`, `cool_related_daytime_helper`, `cool_effective_sp_doubtful_recent_feedback`, `cool_effective_sp_inconsistency_reason`);
  - normalización de quoting defensivo (`'n/a'` y comillas internas consistentes);
  - corrección de cierre inválido en `cool_contract_invalid_reason`.
- **Validación**:
  - parseo YAML estricto exitoso con `ruby/psych` (`YAML_OK`);
  - `hass --script check_config -c /config` no disponible en este contenedor (`hass: command not found`), por lo que la validación final y reinicio quedan pendientes en el host runtime de Home Assistant.
- **Regla preventiva explícita AC-DDA**:
  - en `AC - Día dinámico aprendido (principal)`, cualquier template largo o con múltiples operadores/condicionales debe declararse en `>-` (no inline);
  - en cada edición de `choose`, verificar `default` al mismo nivel que cada `- conditions` y confirmar que no quede mapping abierto antes de `variables:`.

## Rediseño robusto AC-DDA (2026-05-15)

- **Presencia efectiva OR multi-ocupante**: la elegibilidad de presencia del control diurno AC-DDA considera `movimiento estable OR S24/home`, y adicionalmente respeta ventana de override manual activa (`input_datetime.ac_dda_manual_presence_override_until`) durante 60 minutos.
- **Confirmación de presencia 3m**: se incorpora `timer.ac_dda_presence_confirm_3m` junto con `input_boolean.ac_dda_presence_gate_open`; la compuerta solo abre al completar timer con revalidación de señal de movimiento estable.
- **Ausencia sostenida 30m para OFF por desocupación**: el apagado por desocupación exige simultáneamente ausencia de movimiento y S24/persona fuera, manteniendo semántica multi-ocupante y sin corte por ruido breve.
- **Override manual ON 60m sin corte anticipado por salida S24**: ante encendido manual válido, se escribe `input_datetime.ac_dda_manual_presence_override_until = now + 60m`; durante esa ventana no se invalida presencia por salida de S24.
- **Desacople de contexto**:
  - `input_text.ac_dda_context_key_v2_active`: se actualiza en cada cálculo contextual.
  - `input_text.ac_dda_context_key_v2_last_applied`: reservado para escritura estricta solo cuando exista acción HVAC real (modo/setpoint).
- **Observabilidad**: se registran hitos compactos en logbook para gate (`confirmando_3m`, `abierto_revalidado`, `cerrado_por_ausencia_total`), override 60m y fuente de presencia.

### Checklist breve de validación futura en host HA
1. Verificar creación/carga de helpers nuevos (`input_text`, `input_boolean`, `input_datetime`, `timer`) y estado inicial.
2. Confirmar flujo gate:
   - movimiento estable <3m: gate cerrado,
   - timer 3m finalizado + revalidación positiva: gate abierto.
3. Confirmar OFF por desocupación solo cuando simultáneamente no haya movimiento ni S24/persona en home en ventana sostenida.
4. Confirmar manual ON válido escribe override +60m y **no** corta por salida posterior de S24.
5. Auditar logbook por claves: `hito=contexto_calculado`, `gate=confirmando_3m`, `gate=abierto_revalidado`, `override_60m_set`.
6. Ejecutar `check_config` y recarga de automatizaciones en host HA antes de reinicio total.

## Actualización del contrato funcional/técnico AC-DDA: eventos manuales válidos y semántica explícita (2026-05-15)

### 1) Eventos de aprendizaje manual permitidos (únicos válidos)

Se redefine el aprendizaje manual AC-DDA para aceptar **solo** los siguientes eventos terminales:

- `manual_off_during_active_cycle`
  - Definición: usuario apaga manualmente mientras el equipo está activo por un ciclo automático en curso.
  - Estado previo mínimo: equipo en `ON` por activación automática vigente.
- `manual_on_after_auto_stop`
  - Definición: usuario enciende manualmente después de un apagado automático previo.
  - Estado previo mínimo: último cierre de ciclo fue `auto_off` válido.

Evento **no válido / no existente** para aprendizaje:

- `manual_on_after_auto_on`
  - Se declara explícitamente inexistente como evento aprendible cuando el equipo ya está `ON`.
  - Cualquier detección equivalente debe normalizarse a descarte diagnóstico (`ignorado`) por ambigüedad operacional.

### 2) Reglas de ajuste con paso fijo `0.25°C` (inmediatas y sin tope)

Regla global:

- Paso de aprendizaje fijo: `Δ = 0.25°C`.
- Aplicación: desde el **primer** evento válido (sin umbral mínimo de ocurrencias).
- Sin tope artificial de acumulación (solo aplican invariantes de coherencia de banda).

#### Modo COOL

- `manual_off_during_active_cycle`
  - `T_on_cool = T_on_cool + 0.25`
  - `T_off_cool = T_off_cool + 0.25`
- `manual_on_after_auto_stop`
  - `T_on_cool = T_on_cool - 0.25`
  - `T_off_cool = T_off_cool - 0.25`

#### Modo HEAT

- `manual_off_during_active_cycle`
  - `T_on_heat = T_on_heat - 0.25`
  - `T_off_heat = T_off_heat - 0.25`
- `manual_on_after_auto_stop`
  - `T_on_heat = T_on_heat + 0.25`
  - `T_off_heat = T_off_heat + 0.25`

### 3) Invariantes operativos y corrección determinística de banda

Para preservar histéresis y evitar zonas ambiguas:

- COOL: debe cumplirse siempre `T_on_cool > T_off_cool`.
- HEAT: debe cumplirse siempre `T_on_heat < T_off_heat`.

Si una actualización viola la relación, se aplica corrección determinística inmediata:

- Definir `delta_min_band` configurable (recomendado inicial: `0.10°C`).
- COOL (si `T_on_cool <= T_off_cool`):
  - `T_on_cool = T_off_cool + delta_min_band`.
- HEAT (si `T_on_heat >= T_off_heat`):
  - `T_off_heat = T_on_heat + delta_min_band`.

Regla de desempate: en corrección, se conserva el umbral que represente el estado de salida (`off`) y se re-separa el de entrada (`on`) con `delta_min_band`.

### 4) Prioridad temporal del aprendizaje

Orden temporal obligatorio:

1. Detectar evento manual válido.
2. Esperar cierre/confirmación del evento manual (estado terminal consolidado).
3. Aplicar aprendizaje sobre umbrales en ese momento de cierre.
4. Publicar persistencia/auditoría del cambio.
5. Activar vigencia del nuevo rango en el **siguiente ciclo de decisión** (no retroactivo sobre la decisión ya tomada en curso).

### 5) Persistencia y trazabilidad mínima obligatoria

Cada aplicación de aprendizaje debe persistir un registro auditable con:

- `event_type` (`manual_off_during_active_cycle` o `manual_on_after_auto_stop`)
- `mode` (`COOL` / `HEAT`)
- `previous_state` (estado HVAC previo al evento)
- `thresholds_before` (par de umbrales antes del ajuste)
- `thresholds_after` (par de umbrales después del ajuste)
- `timestamp` (fecha/hora exacta de aplicación)

Objetivo: habilitar depuración y auditoría causal de por qué cambió cada rango.

### 6) Ejemplos de aceptación para QA (cambios exactos ±0.25)

| Caso | Evento | Before | After | Resultado esperado |
|---|---|---|---|---|
| COOL + apagado manual durante ON automático | `manual_off_during_active_cycle` | `T_on_cool=24.50`, `T_off_cool=23.75` | `T_on_cool=24.75`, `T_off_cool=24.00` | ambos `+0.25` |
| COOL + encendido manual tras auto-OFF | `manual_on_after_auto_stop` | `T_on_cool=24.50`, `T_off_cool=23.75` | `T_on_cool=24.25`, `T_off_cool=23.50` | ambos `-0.25` |
| HEAT + apagado manual durante ON automático | `manual_off_during_active_cycle` | `T_on_heat=20.25`, `T_off_heat=21.00` | `T_on_heat=20.00`, `T_off_heat=20.75` | ambos `-0.25` |
| HEAT + encendido manual tras auto-OFF | `manual_on_after_auto_stop` | `T_on_heat=20.25`, `T_off_heat=21.00` | `T_on_heat=20.50`, `T_off_heat=21.25` | ambos `+0.25` |

### 7) Criterio de no ambigüedad (norma de contrato)

- Si un evento manual no cumple precondiciones de los dos tipos permitidos, el resultado debe ser `ignorado` con razón explícita.
- No se permiten reinterpretaciones automáticas de eventos ambiguos para forzar aprendizaje.
- Toda decisión terminal de aprendizaje debe cerrar en `aplicado`, `ignorado` o `error_controlado`, con razón trazable.

## 10. AC-DDA diurno: capa contextual de Setpoint y Fan

### Separación de capas (contrato obligatorio)
- **Capa 1 ON/OFF**: conserva el contrato térmico `cool_on/cool_off` con histéresis y guardas diurnas `07:01–21:59`.
- **Capa 2 Setpoint COOL**: calcula `SP_obj` solo después de decidir que la rama ejecuta `cool`.
- **Capa 3 Fan COOL**: determina `fan_target` por demanda térmica/humedad sin alterar umbrales ON/OFF.

### Fórmula operativa de `SP_obj`
- `sp_obj_raw = sp_base_cool + sp_humidity_adj + sp_outdoor_adj + sp_tod_adj + sp_weather_adj + sp_pref_adj`.
- Clamp contractual: `sp_obj_clamped = clamp(sp_obj_raw, 17, 23)`.
- Anti-serrucho setpoint:
  - si `|sp_obj_clamped - sp_current| < 0.3` => conservar `sp_current`.
  - si no => aplicar paso máximo `±1.0°C` por ciclo (`sp_obj_limited_step`).
- Resultado operativo: `sp_obj_final` (numérico redondeado para `climate.set_temperature`).

### Política Fan por demanda + humedad
- `cool_demand = Tin - cool_off`.
- Base fan:
  - `>=1.2` => `high`
  - `0.6..1.19` => `medium`
  - `<0.6` => `low`
- Boost por humedad alta/muy alta: subir un nivel sin superar `high`.
- Antioscilación fan: debounce por helper `input_datetime.ac_dda_last_fan_change_ts` con ventana mínima 3–5 min (actual 240 s).

### Integración con aprendizaje manual (sin contaminación cruzada)
- Se mantiene aprendizaje ON/OFF (`±0.25`) independiente.
- `sp_pref_adj` solo usa señal de preferencia de setpoint por bucket con límite suave (`±1.0`) respecto de la base.
- No se reutiliza aprendizaje de umbrales ON/OFF para fan.
- Si se aprende fan manual en el futuro, debe persistirse en helper separado por bucket.

### Checklist previo a recarga/reinicio
- Verificar que `cool_on/cool_off` no cambió semánticamente.
- Validar `sp_obj_final` siempre en `[17,23]` y con paso máximo `±1.0`.
- Verificar que delta `<0.3` no fuerza escritura de setpoint.
- Validar debounce fan (`fan_should_apply`) y actualización de `ac_dda_last_fan_change_ts`.
- Confirmar telemetría compacta (`Tin/Hin/Tout`, `On/Off`, `SP`, `Fan`, `Demand`, `Bucket`, `Reason`, `resultado_terminal`).

## Contrato de notificaciones móvil AC-DDA (matriz operativa)

| Alias de automatización | Evento | Título final | Mensaje push final (humano) | Detalle de logbook (técnico) | Fallback esperado |
|---|---|---|---|---|---|
| AC - Día dinámico aprendido (principal) | Encendido automático | AC encendido automático | Se encendió el aire automáticamente. Tin: {{ tin }}°C. Objetivo: {{ sp }}°C. | `reason`, `branch`, `trace_id`, validaciones de contrato/fan/setpoint. | `persistent_notification.create` + `input_text.ac_dda_last_notify_status` + `logbook.log` |
| AC - Día dinámico aprendido (principal) | Apagado automático | AC apagado automático | Se apagó el aire automáticamente. Motivo: {{ motivo_humano }}. | Flags internos de presencia/contrato/clima y razón técnica completa. | Igual al patrón transaccional unificado |
| AC - Día dinámico aprendido (confirmación notify AUTO ON) | Confirmación de ON | Confirmación de encendido | Confirmado: el aire sigue encendido en modo frío. | Correlación con firma de ciclo, deduplicación y traza de confirmación. | Igual al patrón transaccional unificado |
| AC - Learning - Manual OFF feedback | Cierre de aprendizaje (apagado) | Aprendizaje por apagado manual | Se registró tu apagado manual y el sistema ajustó el criterio para próximas decisiones. | Resultado terminal (`aplicado/ignorado/error_controlado`), policy y `trace_id`. | Igual al patrón transaccional unificado |
| AC - Learning - Manual ON feedback | Cierre de aprendizaje (encendido) | Aprendizaje por encendido manual | Se registró tu encendido manual y el sistema ajustó el criterio para próximas decisiones. | Resultado terminal (`aplicado/ignorado/error_controlado`), policy y `trace_id`. | Igual al patrón transaccional unificado |
| AC - Manual OFF guard + pausa 5 min | Apagado manual detectado | Apagado manual detectado | Detecté un apagado manual. Se respetará una pausa antes de nuevas acciones automáticas. | Firma de deduplicación, ventana de pausa y estado de guardas. | Igual al patrón transaccional unificado |
| AC - Manual ON guard + presencia temporal | Encendido manual detectado | Encendido manual detectado | Detecté un encendido manual. Mantendré presencia temporal para evitar cortes prematuros. | Snapshot/trace, persistencia por etapas y estado de guardas. | Igual al patrón transaccional unificado |
| AC - Noche dinámico (OpenWeather) + Presencia estable + Fan Low + Notificaciones | Evento vinculado (sin presencia / bloqueo clima / calefacción automática) | Ajuste nocturno de climatización | Se ajustó la climatización nocturna por {{ causa_humana }}. | Variables nocturnas completas (Tin/Tout/Hin/condición/lock/presencia). | Igual al patrón transaccional unificado |

### Reglas de contrato UX (obligatorias)
- Push móvil: solo español humano, sin `reason_code`, `ctx`, `trace`, `signature`, ni claves internas.
- Si falta un dato confiable: usar `No disponible` y motivo breve legible.
- Orden estable por tipo de mensaje:
  1) acción, 2) motivo humano, 3) Tin/Tout si aplica, 4) objetivo o estado final.
- Diagnóstico técnico completo únicamente en `logbook.log` y helpers internos.

---

## 7.2 Actualización AC-DDA (mayo 2026)

### Protección explícita 60 s post Manual ON
- Tras un `Manual ON` válido, se debe persistir `input_datetime.ac_dda_manual_on_protection_until = now + 60s`.
- Mientras esta compuerta esté activa, ramas automáticas que intenten forzar `fan_only` u `off` por ausencia deben quedar bloqueadas.
- Excepción contractual: si la intervención manual termina en `off` o `heat`, la protección se cancela de inmediato y prevalece la orden manual.

### Precedencia de presencia temporal manual (60 min)
- En el mismo `Manual ON` válido se renueva `input_datetime.ac_dda_manual_presence_override_until = now + 60m`.
- En evaluación de presencia efectiva, el orden es:
  1. override manual activo (`manual_presence_override_active`),
  2. señales de movimiento/presencia telefónica,
  3. ausencia sostenida.
- Si el override manual está vigente, el apagado por ausencia sostenida se bloquea explícitamente.

### Aprendizaje manual AC-DDA (alcance COOL/HEAT)
- El aprendizaje manual está limitado a `cool` y `heat`.
- Modos fuera de alcance (`fan_only`, `dry`, `auto`, etc.) deben cerrar con resultado terminal `ignorado` y razón explícita.
- Delta fijo: `±0.25`.
  - COOL:
    - `manual_off_during_active_cycle => +0.25`
    - `manual_on_after_auto_stop => -0.25`
  - HEAT: semántica espejo de COOL.
- Siempre preservar invariantes de banda (`on > off` y límites de contrato) con corrección determinística si se violan.

### Cierre terminal y trazabilidad obligatoria
- Todo flujo de learning debe cerrar en: `aplicado | ignorado | error_controlado`.
- Cada cierre debe registrar `trace_id`, `policy`, `resultado_terminal`, `reason`, `modo_final`, estado de override y estado de compuerta 60 s.
- No se permiten cierres silenciosos ante descartes por carrera o guardas transaccionales.

---

## Contrato base AC-Matriz 160

### 1) Alcance y operación
- **Nombre oficial:** `AC-Matriz 160`.
- **Ventana horaria obligatoria:** `07:01 am - 09:59 pm`.
- **Presencia válida al disparo:** `movimiento en ON` o `S24 en casa`.
- **Disparadores base:**
  - tiempo cada 5 minutos,
  - cambios de sensores térmicos/humedad interior,
  - cambios exteriores relevantes,
  - cambios de presencia,
  - cambios de estado HVAC.
- **Decisión por contexto:** toda decisión de encendido/apagado se toma con base en el contexto activo de la matriz y su columna vigente.

### 2) Arquitectura contextual
- **Estados exteriores:** 8.
- **Estaciones:** 4.
- **Franjas horarias:** 5.
- **Total contractual:** `8 x 4 x 5 = 160 columnas`.

### 3) Contrato matemático
- **Estructura única de fórmula repetida:** la misma estructura base se replica en todas las columnas.
- **Parámetros propios por columna:** cada columna mantiene sus propios parámetros sin compartir valores entre columnas.
- **Histéresis fija por modo (1.0):**
  - `cool: T_on = T_off_cool + 1.0`
  - `heat: T_on = T_off_heat - 1.0`
- **Límites de seguridad:**
  - `T_off_cool` en `[22.0, 26.0]`
  - `T_off_heat` en `[17.0, 22.0]`
- **Arranque seguro de helpers (`input_number`):**
  - Todo helper `input_number` debe iniciar con valor (`initial`) dentro de su rango `min/max`.
  - Si un `initial` queda fuera de rango, Home Assistant puede fallar la carga de la integración completa `input_number` y romper servicios dependientes (por ejemplo `input_number.set_value` en automatizaciones).
  - En `heat`, mantener coherencia de histéresis lógica: `T_on_heat = T_off_heat - 1.0`. Si un helper de arranque no puede reflejar exactamente la relación por límites de entidad, iniciar con valor válido y permitir recálculo automático en el primer ciclo de la automatización.
- **Humedad siempre activa:** la humedad participa siempre en el cálculo.

### 4) Contrato de notificaciones
- **Envío obligatorio:** notificar en cada encendido y en cada apagado.
- **Lenguaje del mensaje:** humano y no técnico.
- **Campos mínimos visibles obligatorios:**
  - hora,
  - evento,
  - contexto humano,
  - umbrales,
  - datos térmicos.

### 5) Gobernanza obligatoria (crítico)
- Si se cambia la **fórmula base repetida**, el cambio debe aplicarse en las **160 columnas**.
- Si se cambia la **estructura de notificación repetida**, el cambio debe aplicarse en las **160 columnas**.
- Ningún cambio funcional se considera completo sin actualización de esta sección y trazabilidad de réplica total.

### Decisiones tomadas
**Fecha:** 2026-05-17
- Desactivación recomendada de **AC-DDA** al migrar.
- Despliegue completo en primer release con **160 columnas**.
- Política de sincronización masiva obligatoria.

## 24) Implementación operativa aplicada en repositorio (2026-05-17)

### Helpers dedicados `ac_matriz_160_*` creados
Se crean y registran helpers dedicados para AC-Matriz 160 en `helpers/input_boolean.yaml`, `helpers/input_text.yaml`, `helpers/input_number.yaml` y `helpers/input_datetime.yaml`, incluyendo compuerta maestra, firma de contexto activa, umbrales vigentes, última acción, estado de validación, deduplicación de notificación y presencia al disparo.

### Guardas activas antes de decisiones HVAC
La automatización `AC-Matriz 160` valida en cada ciclo:
- disponibilidad de helpers (`unknown/unavailable/none` invalida),
- rango contractual de umbrales,
- histéresis fija por modo,
- coherencia de firma de contexto activa.

Si falla alguna guarda, recalcula y sobrescribe helpers críticos, dejando motivo en `input_text.ac_matriz_160_ultimo_resultado_validacion`.

### Checklist post-cambio (operación segura)
- Validar que todos los `initial` de `helpers/input_number.yaml` estén dentro de `min/max`.
- Recargar configuración y confirmar que la integración `input_number` carga sin `Setup failed for 'input_number'`.
- Probar `input_number.set_value` en automatizaciones críticas (incluyendo rutas nocturnas) y validar ausencia de `Action input_number.set_value not found`.

### Anti-contaminación por cambio de columna
Cuando la firma persistida no coincide con la firma del ciclo, se fuerza recálculo y se registra `contexto_recalculado_por_cambio_columna` en validación y log de evaluación.

### Deduplicación segura de notificaciones
La firma de notificación usa `evento|modo|columna|timestamp` y se aplica ventana de supresión corta (180 s). Se persiste resultado en `input_text.ac_matriz_160_ultimo_estado_notificacion` (`emitida/suprimida/sin_evento`).

### Mantenimiento AC-Matriz 160 (regla sintáctica obligatoria)
- En automatizaciones YAML de este proyecto, usar `service:` para llamadas de servicio; **no usar `action:` como clave de servicio**.
- `action:` puede existir solo como clave raíz de automatización (`action:`/`actions:`), pero no como paso de servicio dentro de la lista.

#### Mini-checklist sintáctico previo a reinicio
1. En el alias `AC-Matriz 160`, confirmar que el primer ítem de `actions:` sea un bloque válido (`variables:`) o un paso con `service:`.
2. Verificar que cada rama `choose` use exactamente:
   - `- conditions:`
   - `  sequence:`
3. Confirmar que dentro de `sequence` cada paso sea válido (`service`, `delay`, `wait_template`, `variables`, `choose`, `stop`).
4. Revisar indentación: `default:` al mismo nivel que ramas `- conditions:` y sin claves huérfanas (`service`, `data`, `target`).
5. Ejecutar validación de configuración antes de reinicio para evitar errores tipo `extra keys not allowed @ data[0]['action']`.

### Capa Turbo por presencia y Setpoint HEAT fijo

- **Entrada a turbo (solo en detección inicial de presencia válida):** la evaluación se ejecuta únicamente cuando ocurre una nueva detección (`movimiento ON` o `S24/home`) en el inicio de permanencia.
- **Gatillos turbo COOL (detección inicial):**
  - `Tin >= T_on_cool_columna + 1.0°C`, o
  - `Hin >= 55%`.
- **Gatillo turbo HEAT (detección inicial):**
  - `Tin <= T_on_heat_columna - 1.0°C`.
- **Si no hay gatillo turbo en esa detección inicial:** el ciclo inicia en `normal` (`normal_without_turbo`).

#### Setpoints y fan en turbo
- **COOL turbo:** `hvac_mode=cool`, `setpoint=18°C`, `fan=high`.
- **HEAT turbo:** `hvac_mode=heat`, `setpoint=30°C`, `fan=high`.

#### Salida de turbo por punto medio de histéresis
- `mid_cool = (T_on_cool + T_off_cool) / 2`.
- `mid_heat = (T_on_heat + T_off_heat) / 2`.
- Salida turbo COOL cuando `Tin <= mid_cool`.
- Salida turbo HEAT cuando `Tin >= mid_heat`.
- En la transición se registra `turbo_exit_to_normal` y se bloquea reentrada dentro de la misma permanencia.

#### Régimen normal posterior
- **HEAT normal fijo global:** `setpoint_heat_normal = 28°C` (todas las columnas).
- **COOL normal:** conserva reglas por columna (setpoint/fan existentes).
- **Fan en normal:** mantiene cálculo dinámico vigente con antioscilación del contrato.

#### Bloqueo de reentrada turbo
- Una vez se sale de turbo, se activa bloqueo de reentrada durante la permanencia actual.
- Solo se habilita nueva entrada a turbo cuando hay nueva detección inicial completa de presencia válida en un nuevo ciclo.

#### Telemetría (logbook)
- Hitos obligatorios:
  - `turbo_enter_cool`
  - `turbo_enter_heat`
  - `turbo_exit_to_normal`
  - `turbo_blocked_reentry`
  - `normal_without_turbo`
- Trazas mínimas: `Tin`, `Hin`, `T_on`, `T_off`, `mid`, columna activa y motivo.

#### Ejemplos numéricos
- **COOL:** si `T_on_cool=24.6` y `T_off_cool=23.6`, entonces `mid_cool=24.1`. Con llegada `Tin=25.8` entra turbo cool; sale a normal al bajar `Tin<=24.1`.
- **HEAT:** si `T_on_heat=19.2` y `T_off_heat=20.2`, entonces `mid_heat=19.7`. Con llegada `Tin=18.0` entra turbo heat; sale a normal al subir `Tin>=19.7`.

#### Decisión tomada
- **Fecha:** 2026-05-17.
- **Motivo operativo:** mejorar confort rápido al llegar con desvío térmico marcado y mitigar ciclos cortos inducidos por sensor interno del HVAC.

#### COOL normal (no turbo): SP/Fan contractual y antioscilación (2026-05-18)
- **Demanda de frío:** `cool_demand = Tin - eff_t_off_cool`.
- **Setpoint normal contextual:**
  - `sp_cool_normal_raw = sp_cool_base_col + sp_cool_humidity_adj + sp_cool_outdoor_adj + sp_cool_slot_adj`.
  - `sp_cool_normal = clamp(sp_cool_normal_raw, 17, 23)`.
- **Matriz de fan normal por demanda:**
  - `high` si `cool_demand >= 1.2`.
  - `medium` si `0.6 <= cool_demand < 1.2`.
  - `low` si `cool_demand < 0.6`.
  - **Boost por humedad:** si `Hin >= 55%`, subir un nivel sin superar `high`.
- **Antioscilación de fan:** helper `input_datetime.ac_matriz_160_last_fan_change_ts` con ventana mínima de `240 s` para evitar escrituras en cada ciclo.
- **Precedencia contractual:** `turbo > normal` en el mismo ciclo. Si `turbo_enter_cool=true`, se conserva `SP=18` y `fan=high`; al registrarse `turbo_exit_to_normal`, los ciclos siguientes pueden aplicar `sp_cool_normal` y `fan_cool_normal_target`.

#### Salida contextual de Turbo COOL (2026-06-10)
- La entrada a Turbo COOL conserva sus dos motivos trazables: `desvio_termico_fuerte` por `Tin >= T_on_cool + 1.0` y `humedad_alta_contextual` por `Hin >= 60` con `Tin >= T_off_cool`.
- El motivo de entrada se persiste en `input_text.ac_matriz_160_turbo_cool_motivo` para que ciclos posteriores distingan la salida aplicable.
- Si Turbo COOL entró por temperatura, la salida mantiene el contrato histórico: volver a `normal` cuando `Tin <= mid_cool`, registrando `motivo=cruce_punto_medio_histeresis`.
- Si Turbo COOL entró por humedad contextual, también puede volver a `normal` cuando `Hin <= 59`, registrando `motivo=humedad_normalizada`.
- Al salir de Turbo COOL debe aplicarse inmediatamente el setpoint normal contextual `sp_cool_normal`, abandonando el setpoint turbo `18°C` en la misma transición.
- El fan normal post-turbo respeta la ventana anti-oscilación vigente: si la ventana permite el cambio se aplica `fan_target_final_label`; si no, se registra `hito=fan_normal_post_turbo_pendiente_por_ventana` y el ciclo normal posterior recalcula/aplica el fan cuando la ventana lo permita.


## Mantenimiento y depuración operativa (2026-05-17)

### Convención oficial de nomenclatura
- `ac_matriz_160_*`: helpers dedicados exclusivamente a `AC-Matriz 160`.
- `ac_night_*`: helpers de estado efectivo para la automatización nocturna.
- `tv_dormitorio_*`: temporizadores/helpers de TV dormitorio.
- `notify_mov_*`: reservado para notificaciones de movimiento (crear solo cuando exista dependencia real).
- Compatibilidad heredada permitida: entidades `ac_dda_*` se mantienen si están referenciadas por automatizaciones protegidas; no se eliminan por nombre.

### Mapa de ownership por automatización conservada
- `AC-Matriz 160`: ownership de `ac_matriz_160_*`.
- `AC - Noche dinámico (OpenWeather) + Presencia estable + Fan Low + Notificaciones`: ownership de `ac_night_*` y dependencias heredadas `ac_dda_*` que aún consume.
- `AC - Apaga a las 07:00 am`: sin helpers dedicados; actúa sobre `climate`.
- `Notificación - Movimiento después de 1h sin actividad`: ownership funcional de notificación móvil por movimiento.
- `TV Dormitorio - Programar apagado 30 min` y `TV Dormitorio - Apaga SHIELD al terminar timer`: ownership de `input_boolean.apagar_shield_en_30_min` y `timer.timer_apagado_tv_dormitorio`.

### Política de depuración futura
- Regla obligatoria: **no borrar por prefijo/nombre**.
- Solo eliminar automatizaciones/helpers/scripts cuando sean `no referenciados` por el conjunto de automatizaciones protegidas/activas.
- Antes de borrar: generar inventario de referencias (entity_id, target.entity_id, services, plantillas).
- Después de borrar: validar que no existan referencias colgantes y ejecutar validación de configuración YAML/Home Assistant.

## 25) Política de aprendizaje por columna AC-Matriz 160 (2026-05-17)

### Contrato de persistencia por columna (sin mapa JSON)
- Se definen helpers dedicados por columna y modo con prefijo `ac_matriz_160_`:
  - `input_number.ac_matriz_160_offset_cool_col_1..160`
  - `input_number.ac_matriz_160_offset_heat_col_1..160`
- Parámetros de cada helper:
  - `min: -3.0`
  - `max: 3.0`
  - `step: 0.25`
- Regla operativa de restauración:
  - “Los offsets `ac_matriz_160_offset_*` no usan `initial` para permitir restauración de estado tras reinicio.”

### Orden de cálculo obligatorio
1. Calcular fórmula base contractual por columna (`*_base`).
2. Aplicar offset aprendido de helper por columna/modo activo.
3. Revalidar límites e histéresis contractuales.
4. Decidir ON/OFF con umbrales efectivos resultantes.

### Semántica definitiva de aprendizaje
- COOL:
  - Encendido manual: `delta = -0.25`
  - Apagado manual: `delta = +0.25`
- HEAT (espejo):
  - Encendido manual: `delta = +0.25`
  - Apagado manual: `delta = -0.25`
- Clamp obligatorio de acumulado: `[-3.0, +3.0]`.

### Notificación humana obligatoria
- En cada aprendizaje aplicado se envía push simple en español con:
  - tipo de aprendizaje (encendido/apagado manual),
  - modo,
  - columna/contexto,
  - delta aplicado,
  - offset acumulado,
  - hora del evento.
- El detalle técnico completo se conserva en `logbook.log`.

### Ejemplos de acumulación
- `-0.25 + (+0.25) => 0.00`
- `-0.25 + (-0.25) => -0.50`

### Decisión tomada
- **Fecha:** 2026-05-18.
- **Decisión:** se oficializa en `codex.md` la política operativa implementada de aprendizaje manual por columna con: marcador automático transaccional TTL 30 s, precedencia absoluta de bloqueo manual de 5 min, separación seguridad/aprendizaje, retiro de `persistent_notification` en aprendizaje normal y persistencia de `manual_off_block_until` ante reinicio de HA.

## 26) Ajuste operativo COOL con setpoint entero por OFF (2026-05-18)

### Regla de encendido (cool)
- Solo se habilita cálculo/aplicación de enfriamiento cuando `Tin >= ON`.
- Si `Tin < ON`, se conserva el comportamiento de no encender `cool`.
- La automatización mantiene la guarda horaria real `07:01–21:59` y no calcula/aplica `SP/Fan` fuera de esa ventana.

### Regla de setpoint entero para HVAC
- Como el HVAC acepta enteros, en `cool` se usa:
  - `off_entero = floor(OFF)`
  - `sp_objetivo = off_entero - 1`
  - `SP_final = clamp(sp_objetivo, min_sp_hvac, max_sp_hvac)`
- `SP_final` siempre se envía como entero.

### Ejemplo contractual acordado
- `ON=24`, `OFF=23.45`:
  - `off_entero=23`
  - `SP=22`

### Regla de fan por delta térmica real
- `delta = Tin - OFF`.
- Base:
  - `delta >= 2.0` => `HIGH`
  - `1.0 <= delta < 2.0` => `MED`
  - `delta < 1.0` => `LOW`
- Humedad alta:
  - si `Hin >= 65%`, bajar un nivel de fan respecto al base (`HIGH→MED`, `MED→LOW`, `LOW→LOW`).

### Trazabilidad diagnóstica mínima
- Registrar entrada: `Tin`, `Hin`, `ON`, `OFF`, `horario_habilitado`.
- Registrar salida: `off_entero`, `SP final`, `FAN final`, `delta`, `motivo`.

---

## Contrato operativo AC-Matriz 160 — 2026-05-18

### Alcance de esta intervención
- Este contrato aplica a la automatización principal `AC-Matriz 160` (`id: ac_matriz_160_main_v1`) y deja como fuente de verdad operativa los archivos actuales del workspace.
- La intervención modifica los umbrales térmicos de encendido/apagado automático y agrega bloqueo anti-reversa bidireccional.
- El setpoint de `heat` queda explícitamente fuera de alcance: no se modifica su setpoint normal ni el comportamiento existente de `turbo_heat`.

### Base térmica fija
- La base térmica central para el cálculo contextual de `cool` y `heat` se mantiene fija en `24`.
- No se implementan bases térmicas distintas por estación.
- Los offsets de aprendizaje por columna pueden seguir desplazando los umbrales calculados, pero el resultado final queda limitado por la frontera estacional correspondiente.

### Frontera térmica por estación

| Estación | Frontera |
| --- | ---: |
| Primavera | `22` |
| Verano | `20` |
| Otoño | `22` |
| Invierno | `24` |

### Semántica de la frontera
- En `cool`, la frontera estacional es el mínimo permitido para `OFF cool`.
  - Fórmula contractual: `OFF cool = clamp(OFF cool desplazado, frontera_estacional, 26.0)`.
- En `heat`, la frontera estacional es el máximo permitido para `OFF heat`.
  - Fórmula contractual: `OFF heat = clamp(OFF heat desplazado, 17.0, frontera_estacional)`.
- La validación de rangos debe usar la frontera estacional dinámica, no una frontera fija única de `22`.

### Histéresis contractual
- La histéresis sigue siendo exactamente de `1.0 °C` entre `ON` y `OFF`.
- Para `cool`: `ON cool = OFF cool + 1.0`.
- Para `heat`: `ON heat = OFF heat - 1.0`.

### Bloqueo anti-reversa automático
- El bloqueo anti-reversa es independiente del bloqueo existente `input_datetime.ac_matriz_160_manual_off_block_until`.
- `manual_off_block_until` protege contra reencendido automático después de apagado manual.
- `input_datetime.ac_matriz_160_heat_block_until` y `input_datetime.ac_matriz_160_cool_block_until` protegen contra cambio automático inverso entre modos.
- Si la automatización apaga `cool` automáticamente (`cool -> off`), debe bloquear el encendido automático de `heat` durante 60 minutos.
- Si la automatización apaga `heat` automáticamente (`heat -> off`), debe bloquear el encendido automático de `cool` durante 60 minutos.
- Durante un bloqueo anti-reversa activo:
  - una acción candidata `turn_on_heat` se suprime si `heat_block_until` sigue vigente;
  - una acción candidata `turn_on_cool` se suprime si `cool_block_until` sigue vigente.
- Cuando un encendido automático se bloquee por anti-reversa, debe quedar trazabilidad en `logbook.log` con hitos diferenciados:
  - `hito=anti_reverse_heat_blocked` para bloqueo de `heat`;
  - `hito=anti_reverse_cool_blocked` para bloqueo de `cool`.

## 27) Nota operativa — marcador transaccional AC-Matriz 160 (2026-05-19)

- En `AC-Matriz 160` (`id: ac_matriz_160_main_v1`), el marcador automático transaccional (`ac_matriz_160_auto_origin_*`) **no debe expirar dentro de la misma transacción** que ejecuta `climate.set_hvac_mode` o `climate.turn_off`.
- La expiración debe respetar el TTL completo (mínimo 30 s) para que `AC-Matriz 160 - Aprendizaje manual por columna` pueda leer `marker_vigente=true` durante la evaluación del cambio real de estado HVAC.
- Contrato esperado:
  - eventos automáticos (`turn_on_cool`, `turn_on_heat`, `turn_off`) se clasifican como `automatico_ac_matriz_160`,
  - cierre de learning en `resultado_terminal=ignorado` con `razon=origen_automatico_ac_matriz`,
  - sin aplicar deltas de aprendizaje manual ni emitir notificación de encendido/apagado manual para esos eventos automáticos.

## 28) Mantenimiento sintáctico — aprendizaje manual por columna (2026-05-19)

- **Causa raíz:** error de parseo YAML en `automations.yaml` dentro de `AC-Matriz 160 - Aprendizaje manual por columna` por plantillas Jinja largas con comillas anidadas inestables en líneas inline.
- **Convención aplicada:** para plantillas largas de `message:` y `value:` se adopta bloque multilínea `>-`, evitando concatenación inline con comillas simples anidadas.
- **Alcance del ajuste:** bloque final de la automatización `id: ac_matriz_160_learning_manual_v1`, incluyendo:
  - normalización de `final_transition` en logs (`"->"` dentro de Jinja),
  - reescritura de:
    - `input_text.ac_matriz_160_ultima_accion`
    - `input_text.ac_matriz_160_ultimo_resultado_validacion`
  - verificación de estructura `choose/default/sequence` sin claves huérfanas.

## 29) Mantenimiento — AC-Matriz 160 Learning manual (2026-05-19)

- **Causa raíz:** plantillas Jinja con acceso inválido por atributo sobre `states.climate.<entity_id>` cuando el `entity_id` inicia por número (`020000...`), lo que rompe el parser (`TemplateSyntaxError`).
- **Convención obligatoria:**
  - usar `states('entity_id')` para lectura de estado plano,
  - usar `states.<domain>['entity_id']` para acceder al objeto state (ej. `last_changed`).
- **Helper agregado/normalizado:** `input_text.ac_matriz_160_learning_manual_evento_firma` en `helpers/input_text.yaml` (buffer de deduplicación de evento manual para evitar reprocesamiento de la misma transición).


## 30) Nota técnica mínima — corrección de bloque roto en Learning manual (2026-05-19)

- **Ubicación corregida:** `automations.yaml`, automatización `id: ac_matriz_160_learning_manual_v1` (alias `AC-Matriz 160 - Aprendizaje manual por columna`), tramo cercano a líneas 1437–1438.
- **Causa:** plantilla/string inline mal cerrada por comillas anidadas en `transicion_final_from`, generando arrastre de parser YAML.
- **Estándar adoptado:** plantillas largas o sensibles de `value:`/`message:` se expresan en bloque multilínea `>-` para evitar roturas de comillas y cierres Jinja ambiguos.

## 31) Clasificación simplificada por marker + consumo seguro (2026-05-19)

- **Fuente primaria de clasificación:** el learning `AC-Matriz 160 - Aprendizaje manual por columna` decide origen por `marker vigente + compatible` y no por heurísticas secundarias frágiles.
- **Prioridad estricta de decisión:**
  1. validar transición HVAC real (`off->cool`, `off->heat`, `cool->off`, `heat->off`);
  2. si no hay transición real => `resultado_terminal=ignorado`, `razon=evento_no_transicion`;
  3. con transición real, si marker vigente/no consumido/compatible => `automatico_ac_matriz_160`, cierre `ignorado` con `razon=origen_automatico_ac_matriz`;
  4. en cualquier otro caso => `manual_externo` y se aplica aprendizaje contractual.
- **Contrato del marker transaccional (emisor AC-Matriz 160):**
  - antes de `turn_on_cool`, `turn_on_heat` o `turn_off`, escribir marker con:
    - `kind=automatico_ac_matriz_160`,
    - `trace_id` único,
    - `last_action` esperada,
    - `expires_at` con TTL 30 s,
    - `consumed=false`.
  - orden obligatorio: marker primero, `climate.*` después.
  - el emisor no limpia marker en la misma transacción.
- **Consumo seguro de marker (receptor learning):**
  - solo consumir (`consumed=true`) cuando hubo transición HVAC real y el cierre terminal fue `origen_automatico_ac_matriz`;
  - no consumir ni limpiar marker en descartes por ruido/no transición.
- **Aprendizaje contractual sin cambios de negocio:**
  - COOL: `off->cool=-0.25`, `cool->off=+0.25`.
  - HEAT espejo: `off->heat=+0.25`, `heat->off=-0.25`.
  - clamp acumulado: `[-3.0, +3.0]`.
- **Notificación:**
  - automáticos descartados por marker: sin push de aprendizaje manual.
  - manuales aplicados: push móvil en español + log técnico.
- **Matriz breve de decisión:**

| Transición HVAC real | Marker vigente+compatible | Origen | Resultado terminal |
| --- | --- | --- | --- |
| No | N/A | `sin_transicion_real` | `ignorado:evento_no_transicion` |
| Sí | Sí | `automatico_ac_matriz_160` | `ignorado:origen_automatico_ac_matriz` |
| Sí | No | `manual_externo` | `aplicado:manual_externo_aplicado` (si guardas OK) |

- **Ejemplos de trazas esperadas:**
  - `hito=learning_manual_ignorado | resultado_terminal=ignorado | razon=origen_automatico_ac_matriz | marker_compatible=true`.
  - `hito=auto_marker_consumido | resultado_terminal=ignorado | razon=origen_automatico_ac_matriz`.
  - `hito=learning_manual_columna | resultado_terminal=aplicado | razon=manual_externo_aplicado`.


## 32) Ajuste por franja en fórmula COOL de AC-Matriz 160 (2026-05-20)

- Se incorpora ajuste explícito por franja horaria en `AC-Matriz 160` (`id: ac_matriz_160_main_v1`) para que `cool_off` y `cool_on` varíen dentro del horario diurno.
- Implementación aplicada sobre `t_off_cool_base` antes de offsets de aprendizaje por columna.
- Mapeo de ajuste por `slot_idx`:
  - `0` (`07:01–10:00`): `+0.30`
  - `1` (`10:01–13:00`): `-0.20`
  - `2` (`13:01–16:00`): `-0.30`
  - `3` (`16:01–19:00`): `-0.10`
  - `4` (`19:01–21:59`): `+0.20`
- Fórmula operativa:
  - `t_off_cool_base_no_slot = clamp(base_cool, frontera_estacional, 26.0)`
  - `t_off_cool_base = clamp(t_off_cool_base_no_slot + slot_cool_adjust, frontera_estacional, 26.0)`
  - `t_on_cool_base = t_off_cool_base + 1.0`
- Seguridad/robustez:
  - Se conservan clamps estacionales y máximos contractuales existentes.
  - Se preserva histéresis fija de `1.0 °C`.
  - No se altera la lógica de offsets por columna ni bloqueos de seguridad.
- Observabilidad:
  - `logbook` de evaluación ahora incluye `cool_off_no_slot` y `slot_adj` para trazabilidad diagnóstica.

## 33) Nota operativa — normalización dinámica de fan en `turn_on_cool` AC-Matriz 160 (2026-05-20)

- En la automatización `AC-Matriz 160` (`id: ac_matriz_160_main_v1`) se agrega validación dinámica de capacidades reales de fan antes de `climate.set_fan_mode` para evitar errores `not_valid_fan_mode`.
- Capacidades confirmadas del equipo:
  - `fan_modes: Auto, Low, Med, High`
  - `hvac_modes: off, auto, cool, fan_only, heat`
- Regla oficial de normalización para esta entidad:
  - target interno `medium` siempre se traduce a etiqueta real `Med`.
- Política de fallback aplicada en `turn_on_cool`:
  - usar target normalizado si está soportado;
  - si `medium` no existe, intentar `High` y luego `Auto`;
  - si no hay modo soportado alterno, conservar `fan_mode` actual y no llamar servicio.
- Guarda de ejecución:
  - `fan_call_allowed = fan_should_apply AND fan_target_valid AND fan_target_final_label != fan_mode_actual`.
- Telemetría técnica:
  - cuando se requiere fan pero se omite la llamada, se registra `hito=fan_mode_skip_invalid` con `fan_target_internal`, `fan_target_final_label`, `fan_mode_actual`, `fan_modes_supported` y `razon` (`target_no_soportado` o `sin_cambio_requerido`).
- La ruta de `turn_on_cool` mantiene el flujo general y la notificación de encendido automático sin cambios estructurales.

## 34) Política FAN auto-ON y verificación post-aplicación AC-Matriz 160 (2026-05-20)

- **Alcance:** automatización `AC-Matriz 160` (`id: ac_matriz_160_main_v1`), rama `action_target == turn_on_cool`.
- **Bypass controlado de 240 s (solo primer set FAN en auto-ON):**
  - Se introduce condición explícita `fan_auto_on_first_set` para permitir intento de aplicación de FAN en el encendido automático inicial aun cuando `fan_change_window_ok=false`.
  - La ventana anti-flapping de `240 s` se mantiene vigente para ajustes dinámicos posteriores (`fan_should_apply_dynamic`).
- **Capacidades del equipo y normalización:**
  - Se mantiene lectura de `fan_modes` reales y la normalización `medium -> Med`.
  - Si existe modo soportado objetivo, se ejecuta `climate.set_fan_mode`.
  - Si no existe, se conserva fallback definido y se registra `hito=fan_mode_skip_invalid` con razón técnica y momento (`auto_on` o `dinamico`).
- **Verificación post-aplicación en auto-ON:**
  - Luego de aplicar `climate.set_temperature` y potencial `climate.set_fan_mode`, se espera `3 s`, se releen `temperature` y `fan_mode` reales y se comparan contra objetivo.
  - Si FAN no coincide y era aplicable en auto-ON, se ejecuta un único reintento de `climate.set_fan_mode`, nueva espera corta y nueva lectura.
  - Se registra resultado en `logbook` con `hito=fan_post_check_auto_on` y estados: `aplicado`, `aplicado_tras_reintento`, `no_aplicado_controlado`, `no_aplicado_por_limitacion`.
- **Notificación ON/OFF humana compacta:**
  - Se mantiene deduplicación/ventana para eventos automáticos y solo se notifican ON/OFF automáticos.
  - Para ON de `cool`, la notificación usa valores finales confirmados (lectura real):
    - FAN en español: `Low->Bajo`, `Med/Medium->Medio`, `High->Alto`, con fallback seguro.
    - SP mostrado desde `temperature` real del equipo.
- **Trazas esperadas de soporte:**
  - `hito=turn_on_cool_normal` con `sp_final` y `fan_apply` finales.
  - `hito=fan_mode_skip_invalid` con capacidades reportadas y razón técnica.
  - `hito=fan_post_check_auto_on` con resultado final post-check y reintento.

## 35) Reconciliación post-encendido manual con modo heredado (2026-05-20)

- **Alcance:** automatización `AC-Matriz 160 - Aprendizaje manual por columna` (`id: ac_matriz_160_learning_manual_v1`), reutilizando la clasificación vigente (`manual_externo` vs `automatico_ac_matriz_160`).
- **Condiciones de entrada:**
  - Solo aplica cuando el origen ya fue clasificado como `manual_externo`.
  - Se activa para encendido/manual con modo heredado `fan_only` o `auto`.
  - También puede aplicar a `cool`/`heat` cuando el `SP` queda inconsistente frente al contrato de columna activa.
- **Decisión de modo objetivo por columna activa:**
  - Se decide `cool` o `heat` usando los umbrales efectivos vigentes (`t_on/t_off`) ya persistidos por AC-Matriz 160.
  - La rama define `SP` contractual objetivo y FAN objetivo con normalización de etiqueta real del equipo (`medium -> Med`).
- **Orden de aplicación atómica por evento:**
  1. `climate.set_hvac_mode` al modo objetivo,
  2. `climate.set_temperature` al `SP` objetivo,
  3. `climate.set_fan_mode` al FAN normalizado cuando exista soporte real.
  4. Persistencia de firma de reconciliación para deduplicación por evento/traza.
- **Exclusión por intención manual `FAN/AUTO`:**
  - Si el usuario cambia manualmente a `fan_only` o `auto`, se activa un hold (`ac_matriz_160_manual_legacy_hold=on`) y no se reimpone columna en ese acto.
  - El hold se desactiva únicamente con una nueva selección manual explícita a `cool` o `heat`, rehabilitando la reconciliación.
- **Garantías de no regresión:**
  - No se modifica la lógica base de clasificación de origen.
  - No se resetean ni limpian bloqueos estructurales (`manual_off_block_until`, `cool_block_until`, `heat_block_until`).
  - Se agregan hitos de observabilidad terminal (`reconcile_manual_post_on_applied`, `reconcile_manual_post_on_skip`, `reconcile_manual_hold_on`, `reconcile_manual_hold_off`).

## 36) Ajuste climático dinámico en ON/OFF por columna AC-Matriz 160 (2026-05-21)

- **Alcance:** automatización principal `AC-Matriz 160` (`id: ac_matriz_160_main_v1`), cálculo de umbrales `cool_off/cool_on` para las 160 columnas.
- **Objetivo operativo:** cuando el exterior esté más caliente/húmedo, `cool` debe encender antes, conservando histéresis fija de `1.0 °C`.
- **Variables nuevas del cálculo COOL base:**
  - `adj_tout_cool`: ajuste por temperatura exterior (`tout`) con referencia `24 °C`.
  - `adj_hout_cool`: ajuste por humedad exterior (`hout`) con referencia `60 %`.
  - `adj_clima_cool`: suma acotada de ambos ajustes.
- **Fórmulas y clamps aplicados:**
  - `adj_tout_cool = clamp((tout - 24) * -0.05, -0.40, +0.40)`
  - `adj_hout_cool = clamp((hout - 60) * -0.01, -0.20, +0.20)`
  - `adj_clima_cool = clamp(adj_tout_cool + adj_hout_cool, -0.50, +0.50)`
  - `t_off_cool_base = clamp(t_off_cool_base_no_slot + slot_cool_adjust + adj_clima_cool, frontera_estacional, 26.0)`
  - `t_on_cool_base = t_off_cool_base + 1.0`
- **Robustez implementada:**
  - `hout_raw` se lee con `float(none)` y, si no existe, `hout` usa fallback seguro `60`.
  - si `tout` no está disponible, `adj_tout_cool` se fuerza a `0` (sin sesgo por temperatura exterior ausente).
  - todos los ajustes tienen clamp por componente y clamp total para prevenir sobre-reacción.
- **Observabilidad:**
  - `logbook` de evaluación incorpora `adj_tout`, `adj_hout` y `adj_clima` para trazabilidad de decisiones.
- **No regresión contractual:**
  - se conserva histéresis fija de `1.0 °C` en COOL;
  - se conservan clamps estacionales, offsets por columna y validaciones estructurales existentes.

## 37) Política de apagado por no presencia S24+movimiento AC-Matriz 160 (2026-05-21)

- **Alcance:** automatización dedicada `AC-Matriz 160 - Presencia/Ausencia` (`id: ac_matriz_160_presencia_ausencia_v1`), separada del control térmico principal.
- **Modos HVAC cubiertos:** solo `cool` y `heat`.
- **Precedencia de presencia:** si S24 está en `home`, no se apaga por no presencia.
- **Ramas de decisión:**
  - `10m`: cuando S24 pasa a `not_home` y el movimiento ya está en `off`, se agenda apagado tras 10 minutos.
  - `30m`: cuando S24 pasa a `not_home` con movimiento en `on`, se espera `30m` continuos en `off` para apagar.
- **Guardas antes de apagar (`climate.turn_off`):**
  - S24 sigue `not_home`.
  - Movimiento cumple la rama activa (10m/30m).
  - HVAC sigue en `cool` o `heat`.
  - Respeta bloqueos vigentes (`manual_off_block_until`) y cancelaciones por retorno de S24 o cambio de HVAC fuera de alcance.
- **Deduplicación y carrera:**
  - firma de evento + ventana corta (`dedup`) para evitar dobles disparos.
  - `mode: restart` para cancelar rama pendiente si llega evento de cancelación (`S24 home` o HVAC fuera de alcance).
- **Notificaciones push oficiales:**
  - Título: `AC-Matriz 160 · Apagado por no presencia`
  - Rama `10m`: `Se apagó el AC ({{ modo_previo }}) por no presencia: S24 fuera y sin movimiento durante 10 min.`
  - Rama `30m`: `Se apagó el AC ({{ modo_previo }}) por no presencia: S24 fuera y 30 min continuos sin movimiento.`
- **Observabilidad en `logbook.log`:**
  - terminales: `hito=auto_off_no_presencia_10m` / `hito=auto_off_no_presencia_30m`.
  - cancelaciones: `hito=auto_off_no_presencia_cancelado`.
  - payload mínimo: `trace_id`, `modo_previo`, `s24_state`, `movimiento_state`, `resultado_terminal`, `razon`.

## 38) Override manual de presencia (60 min) AC-Matriz 160 (2026-05-22)

- **Alcance:** `AC-Matriz 160` (`id: ac_matriz_160_main_v1`), `AC-Matriz 160 - Presencia/Ausencia` (`id: ac_matriz_160_presencia_ausencia_v1`) y `AC-Matriz 160 - Aprendizaje manual por columna` (`id: ac_matriz_160_learning_manual_v1`).
- **Helper de expiración:** `input_datetime.ac_matriz_160_manual_presence_override_until` define vigencia del override manual (persistente tras reinicio de HA).
- **Helper de traza:** `input_text.ac_matriz_160_manual_presence_override_trace` conserva `trace_id`, modo, razón y expiración para observabilidad.
- **Activación/renovación (1h):**
  - solo cuando `origen_clasificacion=manual_externo`, transición real `off->cool` o `off->heat`, S24 fuera, sin movimiento y sin presencia real.
  - acción: fijar `override_until = now + 1h` (renovación reemplaza expiración, no acumula).
  - trazabilidad: `hito=manual_presence_override_set` con `resultado_terminal=activado|renovado`.
- **Cancelación temprana:**
  - si durante vigencia se detecta presencia real (`s24_home` o `movimiento_on`), invalidar override (timestamp pasado).
  - trazabilidad: `hito=manual_presence_override_cancelled` con razón terminal explícita.
- **Presencia efectiva operativa en principal:**
  - se mantiene `presence_ok` como presencia real.
  - se deriva `manual_presence_override_active = now < override_until`.
  - se usa `presence_ok_effective = presence_ok OR manual_presence_override_active` para elegibilidad de acciones por presencia.
  - trazabilidad de impacto en auto-ON: `hito=presence_effective_by_override`.
- **Auto-off por no presencia:**
  - en automatización dedicada de ausencia, si override está activo se cancela apagado con `hito=auto_off_no_presencia_cancelado_por_override`.
- **Precedencias y no regresión:**
  - `manual_off_block_until` mantiene precedencia absoluta sobre auto-ON.
  - `cool_block_until` / `heat_block_until` mantienen anti-reversa sin excepciones.
  - sin override activo, el comportamiento existente se conserva.

## 39) FAN dinámico intra-ciclo COOL con ventanas por dirección AC-Matriz 160 (2026-05-22)

- **Alcance:** automatización principal `AC-Matriz 160` (`id: ac_matriz_160_main_v1`) en modo `cool`.
- **Evaluación dinámica en ciclo activo:** además de cambios de sensores, se evalúa cada 1 minuto para permitir ajustes de FAN aunque `action_target=none` y el HVAC ya esté en `cool`.
- **Política delta COOL (sin cambios de negocio):**
  - `delta_cool = Tin - eff_t_off_cool`.
  - `delta >= 2.0 => High`
  - `1.0 <= delta < 2.0 => Med`
  - `delta < 1.0 => Low`
  - Se mantiene normalización a modos reales del equipo (`Low`, `Med`, `High`, `Auto`) y validación contra `fan_modes`.
- **Dirección de cambio y compuertas:**
  - `downshift` (`High->Med`, `Med->Low`) requiere ventana mínima de `90 s`.
  - `upshift` (`Low->Med`, `Med->High`) requiere ventana mínima de `240 s`.
  - `none` no requiere ventana y no dispara `set_fan_mode`.
- **Guardas obligatorias para aplicar `climate.set_fan_mode`:**
  - `climate_mode == cool`,
  - fase distinta de `turbo_cool`,
  - target soportado por el equipo,
  - cambio real requerido,
  - ventana cumplida según dirección.
- **Exclusiones explícitas:**
  - no aplica ajuste dinámico durante `turbo_cool`,
  - no modifica comportamiento de `turbo_heat`,
  - no altera lógica de `heat`.
- **Observabilidad técnica (`logbook.log`):**
  - `hito=fan_dynamic_cycle_eval` para evaluación,
  - `hito=fan_dynamic_cycle_apply` cuando aplica cambio,
  - `hito=fan_dynamic_cycle_skip` cuando se omite.
  - Campos mínimos: `delta`, `fan_actual`, `fan_objetivo`, `change_direction`, `window_required_s`, `window_ok`, `razon`, `col`.

## 40) Ajuste climático dinámico en ON/OFF HEAT por columna AC-Matriz 160 (2026-05-22)

- **Alcance:** automatización principal `AC-Matriz 160` (`id: ac_matriz_160_main_v1`), cálculo de umbrales `heat_off/heat_on` para las 160 columnas.
- **Objetivo operativo:** modular el ciclo de calefacción con contexto exterior (`tout`/`hout`) sin romper la frontera estacional ni la histéresis contractual.
- **Variables nuevas del cálculo HEAT base:**
  - `adj_tout_heat`: ajuste por temperatura exterior (`tout`) con referencia `12 °C`.
  - `adj_hout_heat`: ajuste fino por humedad exterior (`hout`) con referencia `60 %`.
  - `adj_clima_heat`: suma acotada de ambos ajustes.
- **Fórmulas y clamps aplicados:**
  - `adj_tout_heat = clamp((tout - 12) * -0.04, -0.35, +0.35)`
  - `adj_hout_heat = clamp((hout - 60) * +0.005, -0.10, +0.10)`
  - `adj_clima_heat = clamp(adj_tout_heat + adj_hout_heat, -0.40, +0.40)`
  - `t_off_heat_base = clamp(base_heat + adj_clima_heat, 17.0, frontera_estacional)`
  - `t_on_heat_base = t_off_heat_base - 1.0`
- **Robustez implementada:**
  - si `tout` no está disponible, `adj_tout_heat` se fuerza a `0`;
  - `hout` conserva fallback seguro a `60`;
  - se mantienen clamps por componente y total para evitar sobre-reacción.
- **Observabilidad:**
  - `logbook` de evaluación agrega `heat_adj_tout`, `heat_adj_hout` y `heat_adj_clima`.
- **No regresión contractual:**
  - se mantiene histéresis fija de `1.0 °C` en HEAT;
  - se conserva frontera estacional por modo (`t_off_heat` nunca supera frontera de estación);
  - se preservan offsets por columna y validaciones estructurales existentes.


## 41) Secado post-cool obligatorio en apagados AC-Matriz 160 (2026-05-22)

- **Alcance:** automatización principal `AC-Matriz 160` (`id: ac_matriz_160_main_v1`) y automatización dedicada `AC-Matriz 160 - Presencia/Ausencia` (`id: ac_matriz_160_presencia_ausencia_v1`).
- **Contrato operativo de secado:** toda salida de `cool` hacia apagado ejecuta secuencia fija:
  1. `climate.set_hvac_mode` a `fan_only`.
  2. `climate.set_fan_mode` a `Low`.
  3. espera obligatoria de `00:02:00`.
  4. cierre en `off` (`climate.turn_off`).
- **No regresión por modo previo:**
  - si `modo_previo != cool`, el apagado conserva el flujo actual sin secado.
  - si `modo_previo == cool`, no se permite apagado directo salvo fallback técnico.
- **Fallback robusto de secado:**
  - si `fan_only` no entra al primer intento, se reintenta una vez.
  - si el reintento falla, se fuerza cierre seguro en `off` y se registra razón terminal explícita.
- **No presencia integrada:**
  - los apagados automáticos por no presencia (ramas 10m y 30m) también aplican secado cuando `modo_previo=cool`.
- **Notificación de apagado:**
  - la notificación de “apagado” se emite solo al cierre real en `off` (post-secado o fallback).
  - no se emite notificación de apagado al entrar en `fan_only`.
- **Trazabilidad técnica obligatoria (`logbook.log`):**
  - `hito=post_cool_dry_start`
  - `hito=post_cool_dry_completed`
  - `hito=post_cool_dry_fallback_off`
  - payload mínimo: `trace_id`, `modo_previo`, `resultado_terminal`, `razon`.

## 42) Ajuste operativo de trazas en learning manual AC-Matriz 160 (2026-05-22)

- **Alcance exacto:** automatización `ac_matriz_160_learning_manual_v1` (`AC-Matriz 160 - Aprendizaje manual por columna`).
- **Cambio aplicado:** `trace.stored_traces` ajustado de `50` a `200`.
- **Motivo:** aumentar capacidad de auditoría y diagnóstico en ejecuciones del aprendizaje manual.
- **Simetría operativa verificada:** la automatización principal `ac_matriz_160_main_v1` ya conserva `trace.stored_traces: 200`.

## 43) Política de reporte diagnóstico por modo demandado AC-Matriz 160 (2026-05-23)

- **Alcance:** script `ac_matriz_160_reporte_diagnostico` en `scripts.yaml` (notificación móvil y logbook de diagnóstico bajo demanda).
- **Modo demandado como fuente de reporte:**
  - el reporte ahora deriva `modo_demandado` desde la lógica efectiva de demanda (`turn_on_cool` / `turn_on_heat`) y no desde el `hvac_mode` actual.
  - si ambos demandan simultáneamente por ruido, se prioriza `cool` como fallback estable de observabilidad.
- **Builder de razones sin mezcla de columnas:**
  - con `modo_demandado=cool`, solo se listan guardas/umbrales de encendido COOL (`manual_off_block`, `cool_block`, presencia efectiva, `cool_on`).
  - con `modo_demandado=heat`, solo se listan guardas/umbrales de encendido HEAT (`manual_off_block`, `heat_block`, presencia efectiva, `heat_on`).
  - se excluyen explícitamente razones de la columna no demandada para evitar ruido operativo.
- **Normalización de clima OpenWeather a español (con fallback robusto):**
  - `clear/sunny/clear-night -> Despejado`
  - `few clouds/scattered clouds/partly cloudy -> Parcialmente nublado`
  - `broken clouds/overcast/cloudy -> Nublado`
  - `rain/drizzle/pouring -> Lluvioso`
  - `thunderstorm/lightning* -> Tormenta`
  - `mist/fog/haze/smoky -> Neblina`
  - `snow* -> Nevando`
  - fallback final: `Condición no disponible`.
- **Compuerta por estado HVAC para bloque de apagado:**
  - `HVAC OFF`: se reporta solo “por qué no enciende” por modo demandado + clima.
  - `HVAC ON`: se mantiene bloque “Cuándo se apaga” con condición y estimación existentes.
- **Trazabilidad diagnóstica reforzada:**
  - `logbook.log` emite `hito=diagnostico_bajo_demanda_reporte` con `modo_demandado`, `hvac_state`, `resultado_reporte` y `razones` incluidas para verificar no mezcla de modos.

### Ejemplos esperados

- **OFF + demanda COOL:**
  - incluye solo causas COOL (ej. `Tin < cool_on`, bloqueos cool/manual, presencia efectiva).
  - no incluye causas HEAT ni bloque “Cuándo se apaga”.
- **OFF + demanda HEAT:**
  - incluye solo causas HEAT (ej. `Tin > heat_on`, bloqueos heat/manual, presencia efectiva).
  - no incluye causas COOL ni bloque “Cuándo se apaga”.
- **ON (cool o heat):**
  - conserva diagnóstico por modo demandado y agrega evaluación “Cuándo se apaga” según contrato vigente.

## 44) Alineación nocturna de SP/fan con contrato AC-Matriz 160 (2026-05-24)

- **Alcance:** automatización `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`).
- **Contrato nocturno de setpoint (equivalente a AC-Matriz 160):**
  - en `cool`, se calcula `sp_cool_target = clamp(floor(off_cool) - 1, min_temp_equipo, max_temp_equipo)`;
  - en `heat`, se aplica `sp_heat_target` con valor base fijo `24` y clamp al rango térmico del equipo (`min_temp/max_temp`);
  - ambos respetan límites de seguridad térmica del dispositivo (sin forzar setpoints fuera de capacidad real).
- **Orden transaccional de encendido nocturno:**
  1. `climate.set_hvac_mode` (`cool` o `heat`),
  2. `climate.set_temperature` con `sp_*_target`,
  3. `climate.set_fan_mode` en `Low` (si el equipo lo soporta).
- **Política fan nocturno:** `Low` fijo por contrato operativo nocturno.
  - Si el equipo no soporta `Low` en `heat`, no se rompe el flujo: se registra telemetría explícita `resultado=fan_heat_no_soportado`.
- **Observabilidad:** `resultado=sin_cambio` incluye `sp_cool_target`, `sp_heat_target`, `fan=Low`, `col_idx`, `tin` y `hvac_mode` para auditoría compacta.
- **No cambios de alcance:** se preservan presencia, ventanas horarias nocturnas e histéresis ON/OFF existentes.

## 45) Aprendizaje manual nocturno autónomo (2026-05-24)

- **Alcance:**
  - `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`) y nueva automatización `AC Night - Aprendizaje manual por columna` (`id: ac_night_learning_manual_v1`).
  - Flujo 100% Night: no usa ni lee/escribe helpers `ac_matriz_160_*`.
- **Horario estricto de aprendizaje nocturno:** solo entre `22:00:00` y `07:00:00` (incluye cruce de medianoche).
- **Clasificación de origen (manual vs automático):**
  - `ac_night_matrix_v1` escribe marcador transaccional Night en `input_text.ac_night_auto_origin_payload` antes de acciones automáticas ON/OFF, con TTL de `30 s`.
  - Estructura del marcador: `kind`, `trace_id`, `last_action`, `expected_transition`, `expires_at`, `consumed`.
  - `ac_night_learning_manual_v1` clasifica como `automatico_night` solo si el marcador está vigente, no consumido y compatible con la transición observada.
  - Tras clasificar, si se usó marcador válido, se consume (`consumed=1`) para evitar reuso.
- **Transiciones válidas para aprendizaje:**
  - `off->cool`, `cool->off`, `off->heat`, `heat->off`.
  - Cualquier transición con `fan_only`, `auto` u otros modos queda en `resultado_terminal=ignorado`.
- **Cálculo de columna (`col_idx`) alineado con Night control:**
  - Se replica la misma lógica de `estacion`, `franja`, `weather_state` y fórmula de índice de `ac_night_matrix_v1` para garantizar escritura en la misma columna operativa.
- **Delta de aprendizaje por modo con paso fijo `0.10` y clamp `[-3.0,+3.0]`:**
  - COOL: `off->cool = -0.10`, `cool->off = +0.10`.
  - HEAT espejo: `off->heat = +0.10`, `heat->off = -0.10`.
  - Escritura destino:
    - `input_number.ac_night_offset_cool_col_<col_idx>`
    - `input_number.ac_night_offset_heat_col_<col_idx>`
- **Deduplicación mínima:**
  - Firma de evento en `input_text.ac_night_learning_last_signature`:
    - `context_id + last_changed + transicion + col_idx`.
  - Si la firma se repite, cierre terminal `ignorado` con razón explícita.
- **Trazabilidad terminal obligatoria (`logbook.log`):**
  - Campos mínimos por evento: `trace_id`, `col_idx`, `modo`, `transicion`, `origen_clasificacion`, `delta`, `offset_anterior`, `offset_nuevo`, `resultado_terminal`, `razon`.
  - Resultados terminales usados: `aplicado`, `ignorado`.
  - Reserva de `error_controlado` para fallos controlados en validaciones/entidades helper (si se habilitan guardas adicionales de disponibilidad).

### Ejemplos breves de traza
- **Aplicado (manual):**
  - `trace_id=abc123 | col_idx=37 | modo=cool | transicion=off->cool | origen_clasificacion=manual_externo | delta=-0.10 | offset_anterior=0.20 | offset_nuevo=0.10 | resultado_terminal=aplicado | razon=manual_externo_aplicado`
- **Ignorado (automático Night):**
  - `trace_id=def456 | col_idx=37 | modo=heat | transicion=off->heat | origen_clasificacion=automatico_night | delta=+0.10 | offset_anterior=-0.10 | offset_nuevo=-0.10 | resultado_terminal=ignorado | razon=origen_automatico_night`
- **Ignorado (dedup):**
  - `trace_id=ghi789 | col_idx=37 | modo=cool | transicion=cool->off | origen_clasificacion=manual_externo | delta=+0.10 | offset_anterior=0.10 | offset_nuevo=0.10 | resultado_terminal=ignorado | razon=dedup_signature_repetida`

## 46) Notificaciones push Night terminales (2026-05-24)

- **Alcance:** `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`).
- **Regla de emisión:** se notifica **solo en eventos terminales deduplicados** de control nocturno:
  - encendido `turn_on_cool`,
  - encendido `turn_on_heat`,
  - apagado `turn_off`.
- **Sin notificación en no-op:** cuando la decisión es `sin_cambio`, no se envía push.
- **Formato contractual Night (estilo AC‑Matriz 160):**
  - `HH:MM AM/PM | EVENTO= ... | MODO= ... | SP= ... | FAN= ... | INTERIOR= ... | EXTERIOR= ... | TEMP APAGADO= ... | CONTEXTO= Columna ... (Clima | Estación | Horario ...)`
- **Equivalencias de etiqueta:**
  - `cool -> Frío`
  - `heat -> Calor`
  - `off -> Apagado`
  - `fan low -> Bajo` (patrón de fan en español alineado a AC‑Matriz 160; mapeos `med/medium -> Medio`, `high -> Alto` reservados para futuras variantes Night con fan dinámico).
- **Contexto reutilizado Night:**
  - `col_idx` (índice de columna),
  - `weather_label_es`,
  - `estacion_label`,
  - `franja_label` con prefijo legible `Horario ...`.
- **Trazabilidad paralela (`logbook.log`) al emitir push:**
  - ON: `hito=night_auto_on_notified`
  - OFF: `hito=night_auto_off_notified`
  - campos mínimos: `trace_id`, `modo`, `col_idx`, `resultado_terminal`.

### Ejemplos de notificación
- **ON cool:**
  - `11:35 PM | EVENTO= AUTO_ON_NIGHT_COOL | MODO= Frío | SP= 22°C | FAN= Bajo | INTERIOR= 24.8°C | EXTERIOR= 27.1°C | TEMP APAGADO= 23.6°C | CONTEXTO= Columna 37 (Parcial | Primavera | Horario 22:00-00:59)`
- **ON heat:**
  - `04:10 AM | EVENTO= AUTO_ON_NIGHT_HEAT | MODO= Calor | SP= 23°C | FAN= Bajo | INTERIOR= 19.2°C | EXTERIOR= 15.9°C | TEMP APAGADO= 20.1°C | CONTEXTO= Columna 61 (Despejado | Invierno | Horario 04:00-05:59)`
- **OFF (desde cool o heat, conservando modo previo):**
  - `01:20 AM | EVENTO= AUTO_OFF_NIGHT_UMBRAL | MODO= Frío | SP= 22°C | FAN= Bajo | INTERIOR= 23.4°C | EXTERIOR= 25.0°C | TEMP APAGADO= 23.4°C | CONTEXTO= Columna 44 (Nublado | Primavera | Horario 01:00-03:59)`

## 47) Eliminación de compuerta helper en Night (2026-05-24)

- **Alcance:** automatización `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`).
- **Cambio operativo:** se elimina la condición de entrada por helper `input_boolean.ac_night_auto_habilitado`.
- **Motivo:** evitar bloqueos de ejecución tras reinicio o recarga de configuración cuando el helper queda en `off`.
- **Comportamiento resultante:** Night se ejecuta por ventana horaria (`22:00–07:00`) y sus guardas internas existentes, sin dependencia del booleano.

## 48) Recalibración integral de confort nocturno por bochorno (2026-05-24)

- **Alcance:** `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`).
- **Filosofía operativa:** prioridad de confort al dormir; se reduce el sesgo de ahorro agresivo cuando existe riesgo de sudoración/incomodidad nocturna, sin romper el contrato matricial por columna.
- **Contrato preservado por columna (sin romper aprendizaje):**
  - Se conserva `col_idx` y el esquema de helpers `input_number.ac_night_offset_cool_col_<col_idx>` / `...heat...`.
  - `off_cool` permanece como valor final efectivo para control nocturno de frío, calculado como base + offset contextual por columna + clamps.
  - Se deja explícito `off_cool_final_real` para derivaciones de encendido/setpoint.
- **Nuevo índice `bochorno_score` (interior dominante):**
  - Componentes interiores (`tin`, `hin`) con peso dominante (82% del score total).
  - Componentes exteriores (`tout`, `hout`) como ajuste auxiliar suave (18%).
  - Resultado final en `[0,1]` redondeado a 2 decimales para trazabilidad.
- **Histéresis dinámica nocturna (`hysteresis_eff`):**
  - Reemplaza banda fija por banda adaptable al `bochorno_score`.
  - A mayor bochorno, menor banda para adelantar respuesta de confort.
  - Clamps contractuales anti-ciclo y anti-ahorro excesivo: mínimo `0.45`, máximo `1.15` (redondeo a 2 decimales).
- **Nuevo cálculo de `on_cool` con tope dinámico nocturno:**
  - Base: `off_cool_final_real + hysteresis_eff`.
  - Sesgo de confort adicional (`comfort_bias_cool`) para adelantar ON en noches húmedas/bochornosas.
  - Tope dinámico `on_cool_cap_night_dynamic` para impedir encendidos tardíos cuando sube el bochorno.
  - Guardas duras: `on_cool > off_cool` siempre y banda mínima anti-ciclo de `0.35`.
- **Contrato de setpoint en frío (sin cambios de principio):**
  - `off_cool_floor = floor(off_cool_final_real)`
  - `sp_cool_target_raw = off_cool_floor - 1`
  - `sp_cool_target = clamp(sp_cool_target_raw, hvac_min_sp, hvac_max_sp)`
- **Verificación post-escritura de setpoint en equipo HVAC:**
  - Tras `climate.set_temperature`, se lee atributo real reportado por el equipo (`temperature`).
  - Se registra en `logbook`:
    - `sp_objetivo`
    - `sp_reportado_equipo`
    - `sp_confirmado_ok`
  - Si no coincide, se ejecuta **1 reintento controlado** con delay corto y log terminal `confirmado` / `no_confirmado`.
- **Observabilidad nocturna ampliada:**
  - En `resultado=sin_cambio` y eventos ON/OFF se reportan `bochorno_score`, `hysteresis_eff` y (para ON/sin_cambio) `on_cool_cap_night_dynamic`.
  - En ON se agrega estado de confirmación de SP (`sp_confirmado_ok`) para auditar discrepancias cálculo-vs-equipo.
- **Ejemplo de auditoría (similar al caso reportado):**
  - Escenario: `Tin=24.11`, `Hin=56.3`, noche húmeda.
  - Antes: `on_cool` podía quedar alto (ej. `25.17`), retrasando encendido por confort.
  - Ahora: `bochorno_score` elevado reduce `hysteresis_eff`, aplica sesgo de confort y cap dinámico, dejando `on_cool` más cerca de `Tin` para encender antes o quedar “cerca de encender” sin romper anti-ciclo.

## 7. Contrato operativo AC-Matriz 160 (aprendizaje manual)

### Encendido manual compuesto (off → fan_only → cool/heat)
- Se considera transición manual compuesta válida cuando ocurre `off -> fan_only` y el modo final térmico (`cool` o `heat`) llega dentro de una **ventana fija de 10 segundos**.
- La transición efectiva para aprendizaje se consolida como:
  - `off->cool`, o
  - `off->heat`.
- Si el evento queda únicamente en `fan_only` al cierre de 10 segundos, el terminal es `ignorado` y **no** se aprende.

### Fuente única de verdad para origen
- La clasificación de origen no se duplica en learning.
- `ac_matriz_160_learning_manual_v1` consume exclusivamente el marcador transaccional emitido por `ac_matriz_160_main_v1`.
- Precedencia contractual:
  1. Si existe marcador automático vigente y compatible con la transición consolidada, el resultado terminal es `ignorado`.
  2. Si no existe marcador compatible y pasan guardas vigentes, el origen final es `manual_externo`.

### Reglas de aprendizaje y deduplicación
- El aprendizaje aplica únicamente sobre el modo térmico final (`cool`/`heat`).
- No debe existir doble aprendizaje entre el evento intermedio `off->fan_only` y el cierre térmico.
- La deduplicación opera sobre la firma del evento final consolidado.

### Trazabilidad mínima obligatoria
- El registro terminal debe incluir: `trace_id`, transición observada, transición consolidada, origen final, modo de aprendizaje y razón terminal.
- Razón técnica recomendada para el caso compuesto aplicado: `manual_compuesto_desde_fan_only`.
- Mensaje humano recomendado: “Encendido manual detectado por transición compuesta (apagado → ventilación → frío/calor)”.
- El estado intermedio de consolidación no debe generar notificación visible al usuario.

---

## 7. Corrección AC-Matriz 160: precedencia marker + transición consolidada (2026-05-26)

### Causa raíz
En `AC-Matriz 160 - Aprendizaje manual por columna`, la compatibilidad del marker automático se evaluaba contra la transición inmediata (`modo_anterior->modo_nuevo`).
En secuencias válidas `off->fan_only->cool/heat`, la primera observación (`off->fan_only`) no coincide con `turn_on_cool/turn_on_heat`, produciendo clasificación errónea como manual.

### Regla de precedencia nueva
Se establece la precedencia:

`marker automático vigente + transición consolidada final` **>** `heurística de fan_only`.

Implementación contractual:
- `marker_transition_observed_inmediata`: transición instantánea del trigger.
- `marker_transition_observed_final`: usa `transicion_observada_consolidada` cuando `cierre_compuesto_valido=true`; si no, usa la inmediata.
- `marker_compatible_final`: compatibilidad entre `marker_transition_expected` y `marker_transition_observed_final` (incluye wildcard `*->off` para `turn_off`).
- `marker_vigente_final`: telemetría explícita del estado vigente del marker en cierre.

### Alcance exacto modificado en `automations.yaml`
- Automatización `ac_matriz_160_learning_manual_v1`:
  - Bloque post-estabilización (cálculo de cierre compuesto y clasificación final).
  - Consumo de marker (`hito=auto_marker_consumido`) condicionado por clasificación automática consolidada.
  - Logs terminales (`hito=learning_manual_columna`, `hito=learning_manual_ignorado`) enriquecidos con transición inmediata/final y compatibilidad final.
- Automatización `ac_matriz_160_main_v1`:
  - Sin cambio funcional del contrato de firma; se mantiene emisión de `kind`, `trace`, `last_action`, `expires_at`, `consumed=false`.
  - TTL operativo de marker mantenido en `30s` (válido para evaluación de learning).

### Telemetría esperada
1. **Automático consolidado ignorado (sin tocar offset)**
   - `origen_clasificacion=automatico_ac_matriz_160`
   - `resultado_terminal=ignorado`
   - `razon=origen_automatico_ac_matriz`
   - `marker_compatible_final=true`

2. **Manual asistido aplicado (`off->fan_only->cool/heat` sin marker compatible final)**
   - `resultado_terminal=aplicado`
   - `razon=manual_compuesto_desde_fan_only`
   - `cierre_compuesto_valido=true`
   - `marker_compatible_final=false`

3. **Descartado por deduplicación**
   - `razon=dedup_consolidado`
   - `hito=learning_manual_dedup_descartado`

4. **No transición térmica válida**
   - `razon=evento_no_transicion` o `fan_only_sin_cierre_termico_10s`
   - `resultado_terminal=ignorado`

## 49) AC-Matriz 160 — aprendizaje dinámico por columna COOL/HEAT en espejo (2026-05-26)

- **Alcance:** automatización `AC-Matriz 160 - Aprendizaje manual por columna` (`id: ac_matriz_160_learning_manual_v1`) y helpers `input_number.ac_matriz_160_offset_*_col_*`.
- **Cambio de precisión en helpers de offset (sin renombrar entidades):**
  - `step` de columnas COOL/HEAT pasa de `0.25` a `0.05`.
  - Se mantienen `entity_id` actuales para preservar historial/persistencia.
- **Contrato dinámico por columna (aplicación inmediata en el mismo ciclo):**
  - Tras calcular `delta`, el offset se clampa en `[-3.0, +3.0]` y se persiste.
  - En la misma ejecución se recalculan umbrales efectivos de columna:
    - `off_nuevo = off_vigente + delta_aplicado_real`
    - `on_nuevo = off_nuevo + 1.0` en COOL
    - `on_nuevo = off_nuevo - 1.0` en HEAT
  - No se difiere al siguiente ciclo.
- **COOL — encendido manual (`off->cool`):**
  - **Fuera de rango bajo** (`Tin < OFF_vigente`):
    - `OFF_obj = Tin - 0.5`
    - `ON_obj = OFF_obj + 1.0`
    - `delta_offset = OFF_obj - OFF_vigente` (con clamp contractual)
  - **Dentro de rango** (tramos con `Tin - OFF_vigente`):
    - `>0.7 && <=1.0 => -0.50`
    - `>0.5 && <=0.7 => -0.25`
    - `>0.2 && <=0.5 => -0.10`
    - `<0.2 => -0.05`
- **COOL — apagado manual (`cool->off`, dentro de rango):**
  - Tramos con `ON_vigente - Tin`:
    - `>0.7 && <=1.0 => +0.50`
    - `>0.5 && <=0.7 => +0.25`
    - `>0.2 && <=0.5 => +0.10`
    - `<0.2 => +0.05`
- **HEAT — espejo térmico y de signo:**
  - **Encendido manual (`off->heat`)**
    - Fuera de rango alto (`Tin > OFF_vigente`): `OFF_obj = Tin + 0.5`, `ON_obj = OFF_obj - 1.0`, `delta_offset = OFF_obj - OFF_vigente`.
    - Dentro de rango por tramos con `OFF_vigente - Tin`:
      - `>0.7 && <=1.0 => +0.50`
      - `>0.5 && <=0.7 => +0.25`
      - `>0.2 && <=0.5 => +0.10`
      - `<0.2 => +0.05`
  - **Apagado manual (`heat->off`)**
    - Tramos con `Tin - ON_vigente`:
      - `>0.7 && <=1.0 => -0.50`
      - `>0.5 && <=0.7 => -0.25`
      - `>0.2 && <=0.5 => -0.10`
      - `<0.2 => -0.05`
- **Observabilidad terminal reforzada:**
  - Se registran en `logbook` campos de auditoría: `off_previo`, `on_previo`, `off_nuevo`, `on_nuevo`, `delta`, `delta_aplicado`, `col_idx`, `modo`, `resultado_terminal`, `razon`.
  - Se conservan terminales de contrato: `aplicado | ignorado | error_controlado`.

## 50) Fix de parseo YAML/Jinja en telemetría DELTA (AC-Matriz 160) (2026-05-26)

- **Alcance:** automatización `AC-Matriz 160 - Aprendizaje manual por columna` (`id: ac_matriz_160_learning_manual_v1`) en `automations.yaml`.
- **Problema corregido:** error de validación de configuración en `automations.yaml` (referencia previa: `line 2982, column 63`) por uso de formato con `%` dentro de plantilla Jinja embebida en literal YAML (`'%+.2f' | format(...)`).
- **Cambio aplicado (dos bloques duplicados del flujo):**
  - Se reemplazó `DELTA_REAL= {{ '%+.2f' | format(...) }}` por construcción segura sin `%`:
    - `DELTA_REAL= {{ ('+' if (delta_aplicado_real | float(0)) >= 0 else '') ~ ((delta_aplicado_real | float(0)) | round(2)) }}`
  - Se reemplazó `DELTA_OBJ= {{ '%+.2f' | format(...) }}` por construcción segura sin `%`:
    - `DELTA_OBJ= {{ ('+' if (delta | float(0)) >= 0 else '') ~ ((delta | float(0)) | round(2)) }}`
- **Motivo:** evitar colisiones de parseo YAML/Jinja por `%` en plantillas inline largas, preservando telemetría `DELTA_REAL` y `DELTA_OBJ` en notificaciones.
- **Resultado esperado:** Home Assistant vuelve a validar configuración y cargar la automatización sin errores de `annotatedyaml.loader` relacionados a ese tramo.

## 51) Incidente parseo YAML/Jinja en `mensaje_humano` (AC-Matriz 160) — cierre validado (2026-05-26)

- **Fecha del incidente:** 2026-05-26.
- **Automatización afectada:** `AC-Matriz 160 - Aprendizaje manual por columna` (`id: ac_matriz_160_learning_manual_v1`).
- **Causa raíz:** en cadenas YAML con comillas simples, la plantilla Jinja de `DELTA_REAL`/`DELTA_OBJ` quedó con comillas simples internas sin escape (`'+'` y `''`), rompiendo el parseo del loader YAML en el tramo reportado (`line 2982`).
- **Solución aplicada (formato seguro por concatenación):**
  - se mantuvo construcción sin `%` para `DELTA_REAL` y `DELTA_OBJ` (signo manual + redondeo a 2 decimales + concatenación `~`),
  - y se corrigió el escape YAML de comillas simples internas a `''+''` y `''''` en ambos bloques `mensaje_humano` (bloque inicial y bloque post-estabilización), preservando string YAML válido de una sola pieza.
- **Evidencia de validación posterior (OK):**
  - validación de parseo YAML local ejecutada con Python + PyYAML sin errores luego del ajuste (`yaml.safe_load('automations.yaml')`),
  - desaparece el error de parser en `line 2982` dentro de la validación de archivo.

## 52) AC-Matriz 160 — Corrección de interpretación por salida de umbral OFF (2026-05-26)

- **Alcance:** `AC-Matriz 160 - Aprendizaje manual por columna` (`id: ac_matriz_160_learning_manual_v1`).
- **Objetivo del ajuste:** cuando `Tin` queda fuera del umbral `off` durante arranque manual y puede derivar en comportamiento no deseado (`fan_only`/apagado), reubicar el rango completo por traslación rígida manteniendo histéresis fija de `1.0 °`.
- **Condiciones de activación por modo:**
  - **COOL:** si `Tin < off_actual`, entonces `off_objetivo = Tin - 0.5`.
  - **HEAT (espejo):** si `Tin > off_actual`, entonces `off_objetivo = Tin + 0.5`.
- **Fórmula única de ajuste (sin forzar signo de offset):**
  - `delta = off_objetivo - off_actual`.
  - Aplicación uniforme: `off_nuevo = off_actual + delta`, `on_nuevo = on_actual + delta`, `offset_nuevo = offset_actual + delta`.
  - El signo de `offset_actual` no altera la regla: aplica igual para offset positivo, negativo o cruce por cero.
- **Consistencia de histéresis:**
  - El rango se mueve como bloque (misma traslación), sin recalcular `on/off` de forma independiente para el caso ancla fuera de rango.
  - Se agrega telemetría `ancho_histeresis_nuevo` para auditar que la banda se conserva en `1.0` según convención interna del módulo.
- **No alcance:** no se alteran otras reglas de aprendizaje fuera de AC-Matriz 160.

## 53) Night — eliminación de secado post-cool para proteger aprendizaje manual (2026-05-26)

- **Alcance estricto:** automatización `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`) en `automations.yaml`.
- **Cambio operativo:** se elimina exclusivamente en Night el flujo intermedio de secado `cool -> fan_only -> off` (incluyendo `delay` intermedio) para apagado por umbral en frío.
- **Nuevo comportamiento Night (cool):**
  - se mantiene escritura de marcador transaccional en `input_text.ac_night_auto_origin_payload` con:
    - `last_action=turn_off`
    - `expected_transition=cool->off`
  - el apagado pasa a ser terminal directo con `climate.turn_off` (sin `fan_only` intermedio).
  - se conservan notificación push terminal y `logbook.log` con `hito=night_auto_off_notified`.
- **Motivación:** robustecer la clasificación del aprendizaje manual nocturno evitando contaminación por estado intermedio `fan_only` y prevenir secuencias inducidas `off-fan-cool` por la propia automatización Night.
- **No alcance:**
  - no se modifica `ac_night_learning_manual_v1`.
  - no se alteran automatizaciones fuera de `ac_night_matrix_v1`.

## 54) Night — bias global COOL de confort (-0.5 °C) en baseline nocturno (2026-05-26)

- **Estado actual:** reemplazado por la sección 66; `cool_global_bias` ya no es parche activo y queda en `0` solo por compatibilidad de trazas.
- **Alcance histórico:** automatización `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`) en `automations.yaml`.
- **Objetivo operativo:** adelantar reacción de frío nocturno para reducir bochorno/sudoración, aplicando un ajuste global únicamente al flujo COOL de Night.
- **Fórmula aplicada (COOL Night):**
  - `cool_global_bias = -0.5`
  - `off_cool_biased_pre_clamp = off_cool_base_plus_offset + cool_global_bias`
  - `off_cool = clamp(off_cool_biased_pre_clamp, 22.0, 25.7)`
  - Derivaciones preservadas desde `off_cool_final_real`:
    - `on_cool_pre_cap = off_cool_final_real + hysteresis_eff + comfort_bias_cool`
    - `on_cool = clamp(max(off_cool_final_real + 0.35, min(on_cool_cap_night_dynamic, on_cool_pre_cap)), ..., 26.0)`
    - `sp_cool_target = clamp(floor(off_cool_final_real) - 1, hvac_min_sp, hvac_max_sp)`
- **No alcance (HEAT intacto):**
  - sin cambios en `off_heat`, `on_heat` ni `sp_heat_target` contractual.
  - no se modifica lógica de aprendizaje manual nocturno por columna; solo coexiste con el nuevo baseline COOL.
- **Contrato y guardas preservadas:**
  - se mantiene `on_cool > off_cool` mediante banda mínima anti-ciclo (`+0.35`) y clamps existentes.
  - se conservan clamps/rangos de seguridad ya definidos para operación nocturna.
- **Observabilidad / auditoría recomendada:**
  - se expone `cool_global_bias` en notificaciones/logbook de eventos terminales y en `resultado=sin_cambio`.
  - campos sugeridos para auditoría Night: `trace_id`, `col_idx`, `tin`, `off_cool`, `on_cool`, `hysteresis_eff`, `bochorno_score`, `cool_global_bias`, `sp_cool_target`, `resultado_terminal`.
- **Impacto esperado:**
  - **confort:** encendido COOL más oportuno en ventana Night (`22:00–07:00`) al bajar el umbral efectivo de apagado/encendido derivado.
  - **consumo:** posible incremento moderado de tiempo en frío por mayor prontitud de reacción, manteniendo protecciones anti-ciclo y límites contractuales.

## 55) Night — aprendizaje manual por columna con delta 0.20 y notificación espejo diurna (2026-05-26)

### Cambios operativos aplicados
- **Alcance estricto:** solo la automatización `AC Night - Aprendizaje manual por columna` (`id: ac_night_learning_manual_v1`) en `automations.yaml`.
- **Ajuste de aprendizaje manual Night:** los deltas por transición manual pasaron de `0.10` a `0.20` (manteniendo signo por tipo de transición):
  - `off->cool`: `-0.20`
  - `cool->off`: `+0.20`
  - `off->heat`: `+0.20`
  - `heat->off`: `-0.20`
- **Sin alterar reglas existentes:** se conserva la lógica actual de clasificación de origen (`manual_externo`/`automatico_night`), deduplicación por firma, clamps y transiciones válidas.
- **Notificación de aprendizaje Night:** se homologó estructura de mensaje al formato diurno (campos, orden y estilo) usando variables propias de Night (`TIPO`, `MODO`, `COLUMNA`, `DELTA_REAL`, `DELTA_OBJ`, `OFFSET`, `ENVÍO`, `TEMP APAGADO`).
- **Canal de envío confirmado:** notificación por `notify.mobile_app_samsung_s24`.
- **Terminalidad sin duplicados:** se emite una sola notificación terminal por evento manual ON/OFF válido y no deduplicado, respetando la dedup existente por `signature`.

## 56) AC-Matriz 160 — aplicación inmediata transaccional del aprendizaje manual (2026-05-27)

- **Alcance:** `ac_matriz_160_learning_manual_v1` y validación de consumo operativo en `ac_matriz_160_main_v1`.
- **Objetivo:** eliminar desfase entre persistencia de offset aprendido y uso de umbrales en el mismo evento manual.
- **Contrato operativo aplicado en caliente (mismo ciclo):**
  - Tras calcular `delta_aplicado_real`, se recalculan siempre:
    - `off_nuevo = off_vigente + delta_aplicado_real`
    - `on_nuevo = off_nuevo + 1.0` en COOL
    - `on_nuevo = off_nuevo - 1.0` en HEAT
  - Esta regla queda uniforme para las 4 transiciones manuales válidas:
    - `off->cool`, `cool->off`, `off->heat`, `heat->off`.
- **Precedencia de consumo en el evento actual:**
  - Si `resultado_terminal=aplicado`, la lógica de reconciliación usa primero umbrales operacionales recalculados (`umbral_off_*_operacional`, `umbral_on_*_operacional`) en vez de helpers previos.
  - Si no aplica aprendizaje, se mantiene fallback a helpers vigentes.
- **Trazabilidad/telemetría sincronizada en caliente:**
  - Se mantiene publicación de `off_previo`, `on_previo`, `delta`, `delta_aplicado`, `off_nuevo`, `on_nuevo`, `offset_nuevo`, `modo`, `col_idx`, `trace_id`, `resultado_terminal`, `razon`.
- **Garantías preservadas:**
  - clamp de offset `[-3.0,+3.0]`,
  - histéresis espejo por modo (`+1.0` COOL, `-1.0` HEAT respecto a `off`),
  - terminal obligatorio `aplicado|ignorado|error_controlado` con razón explícita.

## 57) AC-Matriz 160 — Turbo por humedad solo contextual (2026-05-27)

- **Alcance:** automatización `AC-Matriz 160` (`id: ac_matriz_160_main_v1`) en `automations.yaml`.
- **Decisión operativa:** **Turbo por humedad solo contextual, umbral 60%, sin humedad aislada**.
- **Regla aplicada en reingreso/presencia (`new_presence_event`):**
  - Se mantiene `new_presence_event` como gatillo de evaluación.
  - El ingreso a `turbo_enter_cool` exige además ausencia de bloqueos (`manual_off_block_active`, `cool_block_active`, `turbo_blocked`) y una de dos rutas:
    1. `desvio_termico_fuerte`: `Tin >= eff_t_on_cool + 1.0`.
    2. `humedad_alta_contextual`: `Hin >= 60` **y** `Tin >= eff_t_off_cool`.
- **Garantía funcional:** `Hin >= 60` por sí sola ya no habilita turbo cuando `Tin` está fuera de contexto de frío.
- **Observabilidad:** `hito=turbo_enter_cool` ahora reporta `motivo=desvio_termico_fuerte` o `motivo=humedad_alta_contextual` y conserva trazabilidad compacta (`Tin`, `Hin`, `T_on`, `T_off`, `col`, `trace`).

## 58) AC-Matriz 160 — coherencia única de columnas entre control principal y aprendizaje manual (2026-05-29)

- **Alcance:** automatizaciones `AC-Matriz 160` (`id: ac_matriz_160_main_v1`) y `AC-Matriz 160 - Aprendizaje manual por columna` (`id: ac_matriz_160_learning_manual_v1`) en `automations.yaml`.
- **Causa corregida:** existía un desfase de índice de temporada para `Primavera`: la principal la trataba como índice `1`, mientras aprendizaje la resolvía como índice `0`. En el caso `weather_idx=1`, `slot_idx=3`, eso hacía que la principal leyera columna `29` y aprendizaje escribiera columna `24`.
- **Fuente única de verdad diurna:** ambas automatizaciones usan el mismo orden de temporada para la matriz 8x4x5:
  - `Primavera = 0`
  - `Verano = 1`
  - `Otoño = 2`
  - `Invierno = 3`
- **Fórmula contractual compartida:** `col_idx = (weather_idx * 20) + (season_idx * 5) + slot_idx + 1`.
- **Garantía operativa:** bajo el contexto concreto `Primavera`, `Parcialmente nublado` (`weather_idx=1`) y franja `04:01 pm - 07:00 pm` (`slot_idx=3`), ambas automatizaciones resuelven `col_idx=24`; por tanto aprendizaje escribe `input_number.ac_matriz_160_offset_<modo>_col_24` y la principal lee ese mismo helper.
- **Sincronización defensiva:** si aprendizaje detecta que `input_text.ac_matriz_160_columna_activa_idx` conserva una columna previa distinta de la recalculada, actualiza los helpers `input_text` de columna/contexto hacia la columna recalculada antes de aplicar aprendizaje.
- **Trazabilidad agregada:** los logbook de evaluación principal y aprendizaje manual reportan `season_idx`, `weather_idx`, `slot_idx`, columna calculada, contexto humano y helper de offset leído/escrito para detectar de inmediato cualquier nuevo desfase.

## 59) AC-Matriz 160 — trazabilidad reforzada de coherencia de columnas (2026-05-29)

- **Alcance:** automatizaciones `AC-Matriz 160` (`id: ac_matriz_160_main_v1`) y `AC-Matriz 160 - Aprendizaje manual por columna` (`id: ac_matriz_160_learning_manual_v1`) en `automations.yaml`.
- **Objetivo:** dejar evidencias explícitas en logbook para auditar que control principal y aprendizaje manual usan el mismo contrato de columna.
- **Contrato visible en logs:** ambos flujos registran la fórmula canónica `weather_idx*20 + season_idx*5 + slot_idx + 1` y el esquema de temporada `Primavera=0,Verano=1,Otoño=2,Invierno=3`.
- **Control principal:** el hito `evaluacion` reporta la columna calculada, el helper de columna activo antes de sincronizar, si estaba desfasado, contexto previo, helpers de offset leídos y offsets vigentes.
- **Aprendizaje manual:** los hitos de sincronización, aplicación e ignorado reportan columna recalculada, columna previa del helper, helpers de offset resuelto/previo, coherencia del helper usado y los índices `season/weather/slot`.
- **Caso contractual:** para `Primavera`, `Parcialmente nublado` y franja `04:01 pm - 07:00 pm`, el cálculo debe resolver columna `24` en ambos flujos.

## 60) AC Night — protección contra reversión falsa por auto-off posterior a encendido manual (2026-05-29)

- **Alcance:** automatizaciones `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`) y `AC Night - Aprendizaje manual por columna` (`id: ac_night_learning_manual_v1`) en `automations.yaml`; helpers Night en `helpers/input_text.yaml`.
- **Causa corregida:** `input_text.ac_night_auto_origin_payload` y `input_text.ac_night_learning_last_signature` eran consumidos por la lógica Night pero no estaban declarados en helpers, por lo que el aprendizaje podía leer `marker_raw=unknown`, calcular `marker_valid=false` y clasificar un `cool->off` automático como `manual_externo`/`apagado_manual`.
- **Contrato de marcador Night:** antes de ejecutar un apagado automático por umbral, la matriz escribe `kind=night_auto`, `last_action=turn_off`, `auto_event=AUTO_OFF_NIGHT_UMBRAL`, `expected_transition=cool->off`, `expires_at`, `consumed=0` y una razón explícita cuando aplica (`tin_ya_estaba_por_debajo_de_off_cool`).
- **Regla de aprendizaje:** si el aprendizaje ve un marcador no expirado, no consumido y con `expected_transition` igual a la transición real, clasifica la transición como `automatico_night`, consume el marcador y no aplica delta ni recálculo caliente manual.
- **Caso terminal protegido:** para `cool->off` automático con `Tin <= off_cool` inmediatamente después de un encendido manual válido, el aprendizaje registra `resultado_terminal=ignorado_auto_off_post_manual_on` y `razon=tin_ya_estaba_por_debajo_de_off_cool` sin bloquear el apagado real del equipo.
- **Observabilidad agregada:** el logbook de ignorado automático incluye `marker_raw`, `marker_valid`, `marker_consumed`, `expected_transition`, `expires_at`, `tin` y `off_cool` para auditar por qué una transición fue o no reconocida como automática.

## 61) AC Night — validación robusta de marker automático consumido (2026-05-29)

- **Alcance:** automatización `AC Night - Aprendizaje manual por columna` (`id: ac_night_learning_manual_v1`) en `automations.yaml`.
- **Causa corregida:** `marker_valid` dependía de comparar `marker_consumed == '0'`. En trazas de Home Assistant el valor puede materializarse como número `0` en vez de cadena `'0'`, por lo que un marker vigente `consumed=0` podía evaluarse como inválido y clasificar un `cool->off` automático como `manual_externo`.
- **Regla robusta aplicada:** la validación normaliza `marker_consumed` con `marker_consumed | int(1)` y solo considera abierto el marker cuando el valor convertido es `0`.
- **Consumo del marker:** al reconocer la transición esperada, el aprendizaje reemplaza el valor real encontrado tras `consumed=` por `consumed=1`, no solo el literal exacto `consumed=0`, para tolerar representaciones equivalentes.
- **Protección funcional:** un apagado automático Night posterior a un encendido manual (`cool->off` con `expected_transition=cool->off`) se clasifica como `automatico_night`, no aplica delta, no reescribe `input_text.ac_night_hot_learning_recalc_payload` y no revierte el offset recién aprendido.
- **Notificaciones:** las transiciones reconocidas como automáticas quedan solo en logbook y suprimen la notificación móvil de `Apagado Manual`, evitando falsas alertas y ráfagas por recálculo.
- **Observabilidad:** el logbook de ignorado automático agrega `marker_consumed_open` y `notificacion=suprimida_por_origen_automatico` para auditar la decisión.

## 62) Guardia transaccional Night contra reversión post-recalculo caliente (2026-05-29)

- **Alcance:** `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`), `AC Night - Aprendizaje manual por columna` (`id: ac_night_learning_manual_v1`) y helper `input_text.ac_night_learning_auto_off_guard_payload`.
- **Contrato final:** un `off->cool` manual nocturno aprende y puede reducir el offset de la columna; si ese aprendizaje recalcula el umbral y provoca un `cool->off` inmediato por `AUTO_OFF_NIGHT_UMBRAL`, ese apagado se clasifica como automático aunque falle `input_text.ac_night_auto_origin_payload`.
- **Clasificación secundaria:** el aprendizaje lee `input_text.ac_night_hot_learning_recalc_payload` como evidencia de `mode`, `transition`, `col`, `offset_old`, `offset_new`, `delta`, `trace` y `ts`. Si la transición actual es `cool->off`, el marker principal no es válido, el payload previo es `off->cool`/`cool` para la misma columna, el timestamp tiene menos de 60 segundos y `Tin` ya está por debajo del umbral `off_cool` recalculado con `offset_new`, se usa `origen_clasificacion=automatico_night_hot_recalc_guard`.
- **Helper explícito recomendado y vigente:** `input_text.ac_night_learning_auto_off_guard_payload` guarda `expected_transition=cool->off`, `col`, `offset_new`, `expires_at`, `consumed=0`, `reason` y `trace` cuando un `off->cool` manual aplica delta. La matriz también lo reescribe justo antes de `climate.turn_off` si el disparo proviene del recálculo caliente y va a apagar por umbral. El helper tiene TTL de 60 segundos y solo se consume si coincide con la transición esperada `cool->off`.
- **Efecto anti-reversión:** para `automatico_night` y `automatico_night_hot_recalc_guard` el aprendizaje no ejecuta `input_number.set_value`, no reescribe `input_text.ac_night_hot_learning_recalc_payload`, no notifica `Apagado Manual` y no vuelve a disparar recálculo.
- **Trazabilidad obligatoria:** la rama automática registra `marker_valid`, `hot_recalc_guard_valid`, payload completo de recálculo caliente, payload explícito de guardia, `tin`, `off_cool`, `resultado_terminal=ignorado_auto_off_post_hot_recalc` y `razon=auto_off_derivado_de_recalculo_caliente` cuando opera la guardia secundaria.


## 63) AC Night — guardia causal por context/parent contra ecos post auto-off (2026-05-29)

- **Alcance:** automatizaciones `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`) y `AC Night - Aprendizaje manual por columna` (`id: ac_night_learning_manual_v1`) en `automations.yaml`.
- **Problema corregido:** después de un `AUTO_OFF_NIGHT_UMBRAL` legítimo, algunos ecos `off->cool` o `cool->off` sin `user_id` podían llegar con `context.id`/`parent_id` encadenado al evento automático, pero el marcador principal ya estaba `consumed=1`; el aprendizaje los trataba como `manual_externo` y modificaba el offset.
- **Regla causal nueva:** el aprendizaje extrae `context.id`, `parent_id`, `user_id`, `trace_id`, `expected_transition`, `expires_at` y tipo de evento del marker Night. Si no hay `user_id`, el marker es `night_auto`, el evento fue `turn_off`/`AUTO_OFF_NIGHT_UMBRAL`, el `context.id` o `parent_id` coincide con el `trace_id` del marker y sigue dentro del TTL extendido de cadena, se activa `auto_chain_guard_valid`.
- **Transiciones protegidas:** para un marker `cool->off`, la guardia causal protege tanto el `cool->off` esperado como su eco inverso `off->cool` dentro de la misma cadena; para calor aplica el equivalente `heat->off`/`off->heat`. Al consumir el marker esperado se abre una guardia explícita con `trace` del evento real y `echo_transition`; cada eco protegido refresca ese `trace` para no dejar desprotegido el siguiente salto causal. Estas transiciones se clasifican como `automatico_night_auto_chain_guard` y no escriben offset ni payload de recálculo caliente.
- **Recalculo caliente:** los guards de `hot_learning_recalc` y `learning_auto_off_guard` ya no dependen exclusivamente de comparar `Tin` contra el `off_cool` recalculado; también aceptan una coincidencia causal por `context.id`/`parent_id` y TTL, manteniendo el requisito de transición, columna y payload esperado.
- **Observabilidad:** el log de aprendizaje automático reporta `context_id`, `parent_id`, `user_id`, `marker_valid`, `explicit_auto_off_guard_valid`, `context_match_auto`, `auto_chain_guard_valid`, matches de guards calientes, razón final y `offset_protegido=true`.
- **No bloqueo de manuales reales:** si no existe marker/payload válido, no hay coincidencia por contexto, el TTL expiró o hay `user_id` humano, la clasificación cae en `manual_externo` y el aprendizaje manual legítimo sigue aplicándose.

## 64) AC Night — anchor manual real `off->cool` para aprendizaje nocturno (2026-05-29)

- **Alcance:** automatización `AC Night - Aprendizaje manual por columna` (`id: ac_night_learning_manual_v1`) en `automations.yaml`.
- **Condición estricta de activación:** el anchor solo aplica cuando la clasificación final es `origen_clasificacion=manual_externo`, la transición real es `off->cool`, el modo aprendido es `cool` y `Tin < off_cool_actual` calculado con el delta nocturno normal. Si la transición pertenece a cadenas automáticas Night, recálculo caliente, guardias por `context/parent`, eco post apagado automático o cualquier origen distinto de `manual_externo`, se conserva el comportamiento de protección y no se aplica anchor.
- **Fórmula del objetivo:** para un encendido manual real en frío cuando la habitación ya estaba por debajo del umbral de apagado, el sistema interpreta intención de enfriar antes y calcula `off_cool_objetivo = Tin - 0.5`. Desde la sección 66 ese objetivo se transforma a offset con `offset_anchor_raw = off_cool_objetivo - off_cool_base - exterior_adjust_cool + comfort_pull`, porque `cool_global_bias` queda en `0` y ya no participa como parche activo.
- **Resolución del offset:** el cálculo histórico de delta fijo se conserva como `offset_new_delta`. El offset final `offset_new` usa `offset_anchor_clamped` únicamente si `cool_manual_on_anchor_needed=true`; en cualquier otro caso usa `offset_new_delta`.
- **Clamps respetados:** el anchor respeta el clamp de offset `[-3.0,+3.0]` mediante `offset_anchor_clamped` y mantiene los límites térmicos nocturnos vigentes para `off_cool_resultante` (`[22.7,24.2]` desde la sección 66). La telemetría diferencia si el objetivo fue limitado por clamp de offset (`anchor_limited_by_offset_clamp`) y conserva el umbral resultante para auditoría.
- **Histéresis dinámica nocturna:** `on_cool_resultante` se recalcula desde `off_cool_resultante` usando la histéresis dinámica Night (`hysteresis_eff`) y el cap dinámico continuo de `night_comfort_pressure`. No se usa una regla fija `ON = OFF + 1.0`.
- **Trazabilidad:** el payload caliente y los logs de `AC Night Learning` exponen diagnóstico de anchor (`anchor_aplicado`, `off_cool_anchor_obj`, `offset_anchor_raw`, `offset_anchor_clamped`, `anchor_limited_by_offset_clamp`, `hysteresis_eff`, `off_cool_resultante`, `on_cool_resultante`) para poder reconstruir si el aprendizaje fue delta normal o anchor manual real.

## 65) AC — aprendizaje manual por columna contra el umbral que debió actuar (2026-05-29)

- **Alcance:** automatizaciones `AC-Matriz 160 - Aprendizaje manual por columna` (`id: ac_matriz_160_learning_manual_v1`) y `AC Night - Aprendizaje manual por columna` (`id: ac_night_learning_manual_v1`) en `automations.yaml`.
- **Regla corregida para COOL:** un `encendido_manual` mide la distancia contra `ON` porque el usuario está pidiendo enfriar antes del encendido automático; un `apagado_manual` mide la distancia contra `OFF` porque el usuario está indicando que el apagado automático debió ocurrir antes.
- **Regla espejo para HEAT:** un `encendido_manual` mide la distancia contra `ON` de calor y un `apagado_manual` contra `OFF` de calor, conservando la inversión propia de la histéresis de calefacción.
- **Magnitud dinámica:** `delta_tramo` se calcula con la magnitud absoluta de `rango_dist`, mientras que el signo del ajuste queda centralizado en `delta`: COOL encendido baja offset, COOL apagado sube offset, HEAT encendido sube offset y HEAT apagado baja offset.
- **Anchors fuera de rango:** se conserva el comportamiento especial de `fuera_rango_anchor` para encendidos manuales fuera del rango ON/OFF. En Night se mantiene el anchor existente de COOL y se agrega su espejo para HEAT cuando un encendido manual ocurre por encima del `OFF` de calor vigente.
- **Intención operativa:** el aprendizaje deja de medir contra el umbral contrario de la histéresis cuando Tin está dentro de la banda; ahora mide contra el umbral que debió haber actuado automáticamente.

## 66) AC Night — fórmula predictiva continua de confort nocturno COOL (2026-05-30)

- **Alcance:** automatización `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`) y espejo de cálculo térmico en `AC Night - Aprendizaje manual por columna` para conservar compatibilidad de umbrales, anchors y recálculo caliente.
- **Eliminación del parche fijo:** `cool_global_bias` deja de ser un sesgo operativo de `-0.5`; se conserva únicamente como variable de compatibilidad con valor `0` para no romper trazas históricas o plantillas que todavía la inspeccionen.
- **Base nocturna nueva:** `off_cool_base` queda centrado en `23.5 °C`. El umbral final `off_cool` ya no nace de una base exterior alta, sino de `23.5 + offset_cool_col + exterior_adjust_cool - comfort_pull` con clamp nocturno `[22.7, 24.2]`.
- **Modelo continuo y predictivo:** el confort nocturno de frío usa `Tin`, `Hin` y un punto de rocío con fórmula Magnus simplificada (`dew_point_night` conserva redondeo a 2 decimales y alimenta las mismas variables dependientes). Cada señal se normaliza con `smoothstep(x)=x*x*(3-2*x)` para evitar saltos duros:
  - `temp_pressure`: empieza cerca de `23.0 °C` y llega fuerte cerca de `24.2 °C`.
  - `hum_pressure`: empieza cerca de `52%` y crece gradualmente hacia `70%`.
  - `dew_pressure`: empieza cerca de `13.8 °C` y crece hacia `18.3 °C`.
  - `night_comfort_pressure = 0.50*temp_pressure + 0.25*hum_pressure + 0.25*dew_pressure`.
- **Contrato de umbrales COOL:** `bochorno_score` queda como alias de `night_comfort_pressure`; `comfort_pull = night_comfort_pressure * 0.45`; `hysteresis_eff = clamp(0.65 - night_comfort_pressure*0.20, 0.42, 0.70)`; `on_cool_cap_night_dynamic = clamp(23.95 - night_comfort_pressure*0.45, 23.55, 23.95)`; `on_cool = max(off_cool + 0.35, min(off_cool + hysteresis_eff, on_cool_cap_night_dynamic))` con tope nocturno razonable.
- **Ajuste exterior secundario:** `exterior_adjust_cool = clamp(((Tout - 24) * -0.02) + ((Hout - 60) * -0.003), -0.15, 0.10)`. El exterior modula suavemente, pero el confort interior domina la decisión.
- **Aprendizaje por columna preservado:** el offset aprendido sigue entrando mediante `input_number.ac_night_offset_cool_col_<col_idx>`. El espejo en aprendizaje manual usa la misma base/pull/ajuste exterior para que `off_cool_vigente`, anchors manuales y `off_cool_resultante` representen el mismo contrato térmico que la matriz nocturna.
- **Recálculo caliente preservado:** el trigger por `input_text.ac_night_hot_learning_recalc_payload` sigue intacto. Cuando el aprendizaje modifica un offset en caliente, la matriz recalcula inmediatamente `off_cool`, `on_cool` y `sp_cool_target` con el nuevo contrato sin cambiar markers ni guardias causales.
- **Observabilidad:** logs de `AC Night` agregan diagnóstico compacto de `dew_point_night`, `temp_pressure`, `hum_pressure`, `dew_pressure`, `night_comfort_pressure`, `comfort_pull` y `exterior_adjust_cool`; las notificaciones móviles mantienen una versión corta para no crecer demasiado.

## 67) AC Night — aprendizaje manual COOL con anchor previo al delta (2026-05-31)

- **Alcance:** automatización `AC Night - Aprendizaje manual por columna` (`id: ac_night_learning_manual_v1`) en `automations.yaml`.
- **Prioridad corregida para `off->cool` manual externo:** la decisión se toma contra los umbrales vigentes previos al aprendizaje (`off_cool_vigente` y `on_cool_vigente`), no contra umbrales recalculados con `offset_new_delta`.
- **Anchor bajo OFF:** si `Tin < off_cool_vigente`, se usa la rama `anchor_below_off`; `off_cool_anchor_obj = Tin - 0.50` y el offset final guardado es el valor absoluto `offset_anchor_clamped`, no `offset_prev + offset_anchor_raw` ni el delta por tramo.
- **Delta variable dentro de banda:** si `off_cool_vigente <= Tin < on_cool_vigente`, se usa `variable_delta_inside_band` con `distancia_a_on = on_cool_vigente - Tin` y deltas negativos de `-0.05`, `-0.10`, `-0.25` o `-0.50` según la distancia al ON automático.
- **Caso anómalo en o sobre ON:** si `Tin >= on_cool_vigente`, se usa `anomalous_at_or_above_on`; no se aplica anchor ni aprendizaje agresivo y el delta queda en `0` para preservar el offset.
- **Observabilidad:** los logs y el payload de recálculo caliente exponen `decision_branch`, `distancia_a_on`, `delta_tramo`, `delta_aplicado_real`, `off_cool_vigente`, `on_cool_vigente`, `offset_new`, `anchor_aplicado`, `anchor_limited_by_offset_clamp` y `off_cool_limited_by_thermal_clamp` para auditar clamps y distinguir anchor absoluto de delta gradual.

## 68) AC Night — confirmación transaccional de AUTO_OFF_NIGHT_UMBRAL COOL (2026-06-02)

- **Alcance:** automatización `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`) en `automations.yaml` y helper `input_text.ac_night_auto_off_pending_payload` en `helpers/input_text.yaml`.
- **Problema corregido:** el apagado por umbral COOL notificaba `AUTO_OFF_NIGHT_UMBRAL` justo después de enviar `climate.turn_off`, aunque `climate.0200009211c7_climate` todavía pudiera reportar `cool`. Con ráfagas de sensores y `mode: restart`, ejecuciones posteriores podían volver a entrar en la misma rama y duplicar la notificación.
- **Nuevo helper transaccional:** `input_text.ac_night_auto_off_pending_payload` registra un apagado COOL pendiente con `event=AUTO_OFF_NIGHT_UMBRAL`, climate, columna, `trace`, expiración y resultado (`sent`, `confirmed` o `pending_timeout`). Este helper es una guarda operativa; no reemplaza `input_text.ac_night_auto_origin_payload`, que sigue siendo el marcador usado por aprendizaje y trazabilidad causal.
- **Cambio de concurrencia:** `ac_night_matrix_v1` pasa a `mode: queued` con `max: 10` para evitar que una ráfaga cancele la ejecución que está esperando confirmación del `off`. Las ejecuciones acumuladas reevalúan el estado real al entrar y, si encuentran un pendiente reciente del mismo climate/contexto, se suprimen con log detallado.
- **Contrato de notificación:** la notificación `AUTO_OFF_NIGHT_UMBRAL` se emite únicamente después de observar `climate == off` dentro de una ventana breve. Si no se confirma dentro de la ventana, se emite `AUTO_OFF_NIGHT_UMBRAL_PENDIENTE` y se registra el estado previo/posterior para auditoría.
- **Aprendizaje Night preservado:** el flujo sigue escribiendo `input_text.ac_night_auto_origin_payload` antes del `climate.turn_off`, con `expected_transition=cool->off`, `auto_event=AUTO_OFF_NIGHT_UMBRAL`, TTL extendido y `consumed=0`, para no romper el clasificador de `AC Night - Aprendizaje manual por columna` ni las guardas existentes de auto-off y recálculo caliente.
- **Observabilidad:** los logs `night_auto_off_suppressed`, `night_auto_off_confirmed_notified` y `night_auto_off_pending_timeout` incluyen `trace_id`, trigger, estado previo, estado posterior, columna, umbrales, resultado de confirmación y motivo de supresión cuando aplica.

## 69) AC Night — reintento controlado tras `pending_timeout` de AUTO_OFF COOL (2026-06-04)

- **Alcance:** automatización `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`) en `automations.yaml`.
- **Decisión operativa:** `pending_timeout` no se trata como pendiente bloqueante absoluto cuando el climate sigue en `cool`, la temperatura interior (`Tin`) sigue en o bajo `off_cool` y el pendiente reciente pertenece al mismo climate/contexto.
- **Reintento acotado:** se añade el campo `retry` al payload `input_text.ac_night_auto_off_pending_payload`. Un `pending_timeout` reciente permite un único reintento inmediato (`retry < 1`) bajo las mismas condiciones térmicas de apagado; si ese reintento vuelve a quedar en `pending_timeout`, los triggers acumulados quedan suprimidos hasta que expire la ventana terminal.
- **Protección contra doble notificación:** los pendientes con `result=sent` siguen bloqueando ejecuciones duplicadas mientras la transición está en curso. Los resultados terminales confirmados (`confirmed`) continúan fuera de la lista de pendientes recientes, y el reintento solo puede confirmar/notificar si el equipo aún reporta `cool` al entrar de nuevo en la rama legítima.
- **Observabilidad:** los logs `night_auto_off_suppressed`, `night_auto_off_confirmed_notified` y `night_auto_off_pending_timeout` exponen `retry`/`pending_retry` y `retry_allowed` para auditar cuándo se permitió el reintento y cuándo se suprimió por protección anti-duplicado.

## 70) AC-Matriz 160 — reconciliación inmediata con umbral aprendido COOL (2026-06-04)

- **Alcance:** automatización `AC-Matriz 160 - Aprendizaje manual por columna` (`id: ac_matriz_160_learning_manual_v1`) en `automations.yaml`.
- **Umbral operativo post-aprendizaje:** cuando el resultado terminal del aprendizaje es `aplicado` y el modo aprendido es `cool`, la automatización usa `off_nuevo` como `umbral_off_cool_operacional` inmediatamente, antes de calcular reconciliación, notificación y fan. Si el aprendizaje no aplica, conserva el helper vigente `input_number.ac_matriz_160_t_off_cool`.
- **Reconciliación COOL inmediata:** `reconcile_sp_target`, `reconcile_cool_delta`, `reconcile_fan_internal` y `reconcile_fan_target_final` se calculan contra el umbral operativo post-aprendizaje, incluyendo el caso anchor `Tin < OFF` y el caso dentro de la banda ON/OFF.
- **Notificación coherente:** `TEMP APAGADO` en `mensaje_humano` muestra el umbral operativo usado por el flujo actual, no necesariamente el valor persistido todavía en el helper global.
- **Aplicación al climate:** la reconciliación de un encendido manual externo puede aplicar `set_temperature` y `set_fan_mode` cuando el contrato resultante difiere por setpoint o por fan, aunque el modo HVAC ya sea `cool`.
- **Observabilidad:** el log `reconcile_manual_post_on_applied` expone `off_previo`, `off_nuevo`, `sp_objetivo`, `fan_objetivo`, `anchor_aplicado` y `delta_aplicado_real` para auditar que el climate recibió el contrato calculado con el nuevo offset.

## 71) AC-Matriz 160 — reconcile operativo fan_only → modo térmico (2026-06-04)

- **Alcance:** automatización `AC-Matriz 160 - Aprendizaje manual por columna` (`id: ac_matriz_160_learning_manual_v1`) en `automations.yaml`.
- **Problema corregido:** una transición inmediata `fan_only->cool` o `fan_only->heat` quedaba clasificada como `sin_transicion_real`, lo cual es correcto para no aprender offset, pero también bloqueaba el reconcile operativo de setpoint y ventilador.
- **Separación explícita:** se conserva la definición de `transicion_hvac_real` para aprendizaje de offset; se añade una elegibilidad independiente `reconcile_manual_thermal_from_fan` solo para reconcile operativo cuando el evento viene de `fan_only`, termina en `cool`/`heat` y no existe marcador automático compatible.
- **Protección anti-auto:** `reconcile_fan_to_thermal_marker_compatible` trata como automático compatible un marker vigente `off->cool`/`off->heat` observado como cierre `fan_only->cool`/`fan_only->heat`, evitando confundir acciones de AC-Matriz con acciones manuales.
- **Contrato operativo:** `reconcile_apply` ahora permite actuar si el evento es `manual_externo` o si cumple `reconcile_manual_thermal_from_fan`, siempre con `legacy_manual_hold_active` inactivo, dedup por `reconcile_last_signature`, y trabajo real de contrato (`SP`, `FAN`, modo inconsistente o garantía operativa fan→térmico).
- **Aprendizaje preservado:** si el único motivo es `fan_only->cool`/`fan_only->heat`, `resultado_terminal` puede seguir en `ignorado` y no se modifica ningún offset.
- **Observabilidad:** el reconcile aplicado en este caso registra `hito=reconcile_manual_fan_to_thermal_applied`, `from`, `to`, `sp_objetivo`, `fan_objetivo`, `fan_soportado`, `guarantee` y `razon=fan_only_to_<modo>_manual_reconcile`. Los skips exponen `reconcile_skip_reason`, `auto_marker_fan_to_thermal`, `fan_from_fan_only_eligible`, inconsistencias, hold, dedup y soporte de fan para diagnosticar por qué no actuó.

### AC-Matriz 160 — Contrato de presencia/ausencia robusto

- **Sensor crudo de movimiento**: `binary_sensor.tze204_gkfbdvyx_ts0601`. Es la fuente instantánea para ausencia real, ráfagas y validación de encendidos por movimiento.
- **Sensor estable de movimiento**: `binary_sensor.presencia_movimiento_estable`. Mantiene filtrado de continuidad para presencia estable; no debe usarse para sumar otra ventana de ausencia de 30 minutos.
- **Apagado por ausencia 10 min**: `AC-Matriz 160 - Presencia/Ausencia` apaga solo si S24 pasa a `not_home`, el movimiento crudo está `off`, transcurren 10 minutos y siguen S24 fuera, movimiento crudo `off`, sin override manual activo y el HVAC en `cool` o `heat`. Hito: `turn_off_por_ausencia_10m_s24_away`.
- **Apagado por ausencia 30 min**: la misma automatización apaga si el movimiento crudo lleva `off` 30 minutos, S24 no está `home`, no hay override manual activo y el HVAC está en `cool` o `heat`. Hito: `turn_off_por_ausencia_30m_movimiento_off`.
- **Exclusión de `fan_only`**: la ausencia nunca apaga desde `fan_only`; solo opera sobre `cool` o `heat`.
- **Marcador automático obligatorio**: antes de cada apagado por ausencia se escriben `input_text.ac_matriz_160_auto_origin_kind`, `trace`, `expires_at`, `last_action=turn_off` y `consumed=false` para que `AC-Matriz 160 - Aprendizaje manual por columna` clasifique el cambio como `automatico_ac_matriz_160` y no aprenda un apagado manual falso.
- **Encendido por presencia efectiva**: la automatización principal permite encendido por S24/home, override manual activo, movimiento estable de 5 minutos o ráfagas válidas.
- **Ráfagas válidas**: se cuentan detecciones del sensor crudo terminadas en los últimos 15 minutos, con duración mínima de 60 segundos; se requiere más de 3 detecciones (4 o más) y el sensor crudo debe estar `on` en el instante de evaluación para habilitar encendidos basados en movimiento.
- **Persistencia de ráfagas**: `input_text.ac_matriz_160_motion_burst_payload` guarda timestamps depurados de eventos válidos y `input_datetime.ac_matriz_160_motion_burst_last_ts` registra la última actualización del payload.

## 72) AC-Matriz 160 — llegada real para turbo por humedad contextual (2026-06-12)

- **Alcance:** automatización principal `AC-Matriz 160` (`id: ac_matriz_160_main_v1`) en `automations.yaml`.
- **Presencia efectiva actual:** `presence_motion` vuelve a respetar el `delay_off` de `binary_sensor.presencia_movimiento_estable`; un `off` corto del sensor crudo ya no derriba presencia mientras el sensor estable siga `on`. Las ráfagas siguen exigiendo sensor crudo `on`.
- **Llegada elegible para turbo:** se separa `new_presence_event` de `turbo_arrival_real_eligible`. El turbo por `humedad_alta_contextual` ahora requiere una llegada confiable reciente por S24/persona, transición reciente del movimiento estable, o ráfagas válidas sin presencia estable continua.
- **Bloqueo anti-rebote:** si `Hin >= 60` y `Tin` está en rango contextual, pero la señal corresponde a presencia estable continua, rebote del movimiento crudo u override manual sin llegada real, `turbo_cool_contextual_humidity_allowed` queda falso y no entra a `turbo_cool` por humedad contextual.
- **Observabilidad:** los logs de evaluación exponen `llegada_turbo`, `llegada_razon`, `hum_contextual` y `hum_contextual_allowed`. Cuando se bloquea el caso de humedad contextual se registra `hito=turbo_cool_contextual_humidity_blocked` con origen de presencia, estados de movimiento y motivo del bloqueo.

---

## Nota operativa: AC-Matriz 160 · frío normal contextual

- `eff_t_off_cool` sigue siendo la meta/fuente de verdad para el apagado en frío; los ajustes de setpoint no modifican esa temperatura de apagado.
- Durante un ciclo activo en `cool` normal, si cambia el contexto/columna y el nuevo `sp_cool_normal` calculado desde el `eff_t_off_cool` vigente queda por debajo del setpoint actual del climate, la automatización puede bajar el SP para re-sincronizarlo con el contexto más exigente.
- La re-sincronización contextual es solo descendente durante el ciclo: no sube el SP si el nuevo `sp_cool_normal` es mayor que el SP actual.
- Si pasan 40 minutos acumulados en frío normal y `Tin` sigue por encima de `eff_t_off_cool` (con margen de 0.2 °C), puede aplicarse una sola vez por ciclo un refuerzo temporal de `SP actual - 1`, respetando el `min_temp` del climate.
- La fase `turbo_cool` no cuenta para ese temporizador y no ejecuta ni re-sincronización contextual ni refuerzo de 40 minutos; al salir de turbo hacia `cool` normal empieza un conteo nuevo desde cero.

## 73) AC-Matriz 160 — override contextual de upshift dinámico de fan (2026-06-15)

- **Alcance:** automatización principal `AC-Matriz 160` (`id: ac_matriz_160_main_v1`) en `automations.yaml`.
- **Problema corregido:** después de una re-sincronización contextual descendente de setpoint (`sp_contextual_downsync_apply`), el ventilador dinámico podía quedar bloqueado por la ventana normal de upshift de 240 segundos aunque el nuevo contexto exigiera más capacidad de enfriamiento.
- **Nueva señal:** `fan_contextual_upshift_override` se activa solo cuando ya existe `cool_contextual_downsync_needed`, el ciclo normal de frío está activo, el cálculo dinámico pide `upshift`, el cambio real de fan es necesario, el target es soportado y la fase no es `turbo_cool`.
- **Ventana efectiva:** `fan_change_window_effective_ok` conserva la ventana normal (`fan_change_window_ok`) y agrega la excepción contextual únicamente para upshift. Los downshift siguen respetando `fan_downshift_min_window_s` para evitar oscilaciones.
- **Aplicación dinámica:** las decisiones de aplicación y bloqueo del fan dinámico usan la ventana efectiva, sin modificar la lógica de SP contextual ni el refuerzo agresivo de 40 minutos.
- **Observabilidad:** los logs `fan_dynamic_cycle_eval`, `fan_dynamic_cycle_apply`, `fan_dynamic_cycle_skip` y el skip por ventana exponen ventana original, ventana efectiva y override contextual. Cuando aplica por esta excepción, la razón queda como `contexto_mas_exigente_upshift`.

## 74. AC Night Matriz Contextual — resincronización y refuerzo progresivo de ciclo COOL

- **Alcance:** automatización `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`) y helpers nocturnos dedicados.
- **Resincronización contextual con HVAC ya encendido:** durante horario nocturno, si el equipo ya está en `cool` y existe presencia válida, Night compara el setpoint reportado por el climate contra el setpoint nocturno efectivo esperado. Si no coincide, aplica `climate.set_temperature` con el SP efectivo y fuerza `fan_mode=Low` cuando el ventilador no está alineado. Esto permite corregir un encendido heredado desde `AC-Matriz 160` u otra automatización sin esperar un nuevo `AUTO_ON_NIGHT_COOL`.
- **Contrato efectivo del ciclo:** el contrato base se calcula con `sp_cool_target`, `off_cool`, `on_cool`, columna, franja, clima y presión de confort nocturna. Si ese contexto cambia mientras el ciclo sigue activo, Night resincroniza SP/fan contra el nuevo contrato, pero conserva `input_datetime.ac_night_cool_cycle_started_ts`; por lo tanto, no reinicia el contador progresivo del ciclo activo.
- **Refuerzo progresivo operativo:** cada ciclo de enfriamiento inicia con `sp_cool_target` y `input_number.ac_night_cool_reinforcement_count=0`. Si pasan 20 minutos y `Tin > off_cool` con `hvac_mode=cool` y presencia válida, Night aplica `sp_cool_target - 1`. A los 50 minutos aplica `sp_cool_target - 2` y a los 80 minutos `sp_cool_target - 3`, siempre que todavía no se haya llegado a `off_cool`.
- **Límites:** el refuerzo máximo por ciclo es de `3 °C` y el SP efectivo nunca baja de `hvac_min_sp`. El cálculo usado es `max(hvac_min_sp, sp_cool_target - refuerzos)`.
- **Reset por ciclo:** el ciclo y sus refuerzos se reinician cuando Night apaga por `Tin <= off_cool`, por ausencia, al salir del horario nocturno, cuando el HVAC deja de estar en `cool`, o cuando empieza un nuevo ciclo nocturno de frío. El siguiente ciclo vuelve a iniciar con `sp_cool_target`, sin heredar el SP reforzado anterior.
- **No aprendizaje:** el refuerzo es una acción operativa temporal. No modifica offsets contextuales (`input_number.ac_night_offset_cool_col_*`), no dispara aprendizaje manual nocturno y no altera el payload de `hot_learning_recalc_requested` salvo la resincronización normal ya existente.
- **Observabilidad:** los eventos nuevos quedan en logbook con hitos `night_sp_context_resync`, `night_fan_context_resync`, `night_sp_progressive_reinforcement` y `night_cool_cycle_reset`. Los logs incluyen `trace_id`, `col_idx`, `tin`, `off_cool`, `sp_cool_target`, `sp_efectivo`, cantidad de refuerzos, minutos de ciclo y motivo.

## 75) AC-Matriz 160 — contrato de SP COOL y centinela de ciclo normal (2026-06-15)

- **Alcance:** automatización principal `AC-Matriz 160` (`id: ac_matriz_160_main_v1`) en `automations.yaml` e integración local GE/SmartHQ en `custom_components/ge_home/entities/common/ge_climate.py`.
- **Fuente contractual del setpoint:** el SP normal de frío sigue saliendo de `floor(eff_t_off_cool) - 1` con clamp del climate. El refuerzo agresivo de 40 minutos ya no parte del SP reportado por el equipo; se calcula como `clamp(sp_cool_normal - 1, hvac_min_sp, hvac_max_sp)`, evitando acumulaciones sobre lecturas truncadas o residuales del dispositivo.
- **Uso del SP reportado:** `sp_actual` queda como lectura diagnóstica y guarda operativa para no reenviar bajadas innecesarias. No es fuente de contrato para `sp_cool_normal` ni `sp_cool_aggressive`.
- **Centinela inválido:** `1970-01-01 00:00:00` y cualquier timestamp anterior a `2000-01-01 00:00:00` se consideran inactivos. También se descartan timestamps futuros. El temporizador del refuerzo solo cuenta minutos reales cuando el ciclo normal de cooling tiene timestamp válido del ciclo actual.
- **Inicio de ciclo normal:** al ejecutar `turn_on_cool` automático se registra inmediatamente `now()` en `input_datetime.ac_matriz_160_cool_normal_cycle_started_ts` y se resetea `input_boolean.ac_matriz_160_cool_aggressive_sp_applied`. Si el equipo ya aparece en `cool` normal por acción manual o externa y no existe timestamp válido, la automatización abre un nuevo ciclo normal con `now()` en vez de calcular tiempo contra el centinela.
- **Conversión GE/SmartHQ:** la entidad local declara Fahrenheit porque el ERD del equipo opera en Fahrenheit. Cuando Home Assistant recibe una solicitud Celsius, la convierte a Fahrenheit con decimales (por ejemplo 21 °C ≈ 69.8 °F). La integración normaliza con `ceil()` antes de enviar el ERD entero para que las solicitudes 18–23 °C no caigan sistemáticamente al Celsius inferior por truncamiento descendente (`int()`).
- **Confirmación del refuerzo agresivo:** el hito `sp_agresivo_40m_apply` ya no marca `input_boolean.ac_matriz_160_cool_aggressive_sp_applied` apenas solicita el cambio. Primero envía `sp_cool_aggressive`, espera unos segundos y confirma que el SP reportado por `climate.0200009211c7_climate` coincide con tolerancia `0.2 °C`. Si no coincide, reintenta una vez. Solo si la lectura final confirma el SP se enciende el flag y se guarda `sp_agresivo_40m_aplicado`; si tampoco confirma tras el reintento, el flag queda apagado, se guarda `sp_agresivo_40m_no_confirmado` y el siguiente ciclo de evaluación puede volver a intentarlo.
- **Observabilidad:** los logs de resincronización contextual y refuerzo agresivo exponen `trace_id`, `sp_contractual`, `sp_cool_normal`, `sp_cool_aggressive`, `sp_solicitado`, lecturas reportadas y motivo/contexto para auditar si el contrato o la lectura del equipo explica cada ajuste. El refuerzo agresivo registra internamente `resultado_terminal=aplicado`, `resultado_terminal=aplicado_tras_reintento` o `resultado_terminal=no_aplicado_controlado`, sin notificaciones móviles ni persistentes.

---

## Contrato causal AC-Matriz 160: aprendizaje manual por columna sin doble aprendizaje

### Alcance
- Aplica a `AC-Matriz 160 - Aprendizaje manual por columna` (`id: ac_matriz_160_learning_manual_v1`).
- El objetivo es que una sola intención manual `cool -> off` produzca como máximo un aprendizaje y una notificación, aunque el dispositivo emita o confirme una cadena `cool -> off -> cool -> off` y las ejecuciones se procesen tarde por `mode: queued`.

### Contrato de clasificación causal
- Cada transición captura desde el `trigger` su `context.id`, `parent_id`, `user_id`, contexto anterior, `last_changed`, transición observada y una raíz causal (`parent_id` cuando existe; si no, `context.id`).
- La firma causal de evento usa `modo|columna|raíz_causal|transición` y complementa la firma exacta previa; no la reemplaza.
- Un marcador automático compatible no solo se consume: también se persiste como contexto automático aceptado con `context_id`, `parent_id`, `root_id`, transición, columna, modo y `marker_trace_id`.
- Un evento posterior se ignora aunque `ac_matriz_160_auto_origin_consumed=true` si comparte `context_id`, `parent_id` o raíz causal con una transición automática aceptada.
- Un apagado posterior se ignora como rebote post apagado manual solo si comparte raíz causal, modo y columna con el último apagado manual aplicado y la ventana corta `manual_off_rebound_until` sigue activa.
- `manual_off_block_until` queda como guarda operativa anti auto-ON y no es un bloqueo global de aprendizaje: no debe impedir por sí solo un apagado manual legítimo con raíz causal independiente.

### Escenarios obligatorios A-G
- **Caso A — `cool -> off` manual normal:** si no hay marcador automático compatible ni coincidencia causal automática/manual previa, clasifica `apagado_manual_real`, aplica un aprendizaje, emite una notificación y registra firma causal manual.
- **Caso B — `cool -> off -> cool -> off`:** solo aprende el primer `cool -> off`; el `off -> cool` derivado automático se ignora y el `cool -> off` posterior con la misma cadena causal se ignora como derivado/rebote causal.
- **Caso C — `cool -> off` automático con marcador compatible:** clasifica como automático, no aprende, no notifica aprendizaje manual y persiste el contexto automático aceptado.
- **Caso D — `off -> cool` automático con confirmaciones tardías:** no aprende si coincide con marcador automático o con contexto automático aceptado, incluso si el helper mutable ya fue consumido al salir de la cola.
- **Caso E — segundo apagado manual legítimo con nueva raíz causal:** sí puede aprender aunque esté temporalmente cerca, siempre que no comparta raíz causal con la cadena automática aceptada ni con la firma manual reciente.
- **Caso F — ejecuciones en cola:** la decisión debe depender de los datos capturados desde `trigger` y de firmas/contextos causales persistidos, por lo que debe ser equivalente a una ejecución sin cola.
- **Caso G — dos `cool -> off` cercanos con contextos independientes:** no se deduplican solo por proximidad temporal; si la raíz causal cambia y no hay coincidencia automática, el segundo apagado puede ser manual válido.

### Resultado esperado para la traza crítica
- Primer `cool -> off`: manual válido, `delta +0.50`, offset final `0.45`, notificación emitida.
- `off -> cool`: automático, ignorado, sin cambio de offset ni notificación manual.
- Segundo `cool -> off`: derivado/rebote causal, ignorado, sin delta, sin cambio de offset y sin segunda notificación.
- El resultado final esperado es `offset_cool_col_7 = 0.45`, `off_cool = 24.16` y `on_cool = 25.16`; no debe terminar en `offset_cool_col_7 = 0.55`, `off_cool = 24.26` y `on_cool = 25.26`.

---

## 2026-06-16 — Corrección GE/SmartHQ Celsius impar y anti-loop de refuerzo nocturno

### GE/SmartHQ y contrato de temperatura
- La integración local `custom_components/ge_home` trata los ERD de temperatura del equipo GE/SmartHQ como valores Fahrenheit internos. Home Assistant es responsable de convertir esos Fahrenheit a Celsius cuando la instancia se muestra en unidades métricas.
- `target_temperature` no debe convertir el ERD Fahrenheit a Celsius para redondearlo a múltiplos artificiales de `2 °C` ni reconvertirlo a Fahrenheit. Ese bucketing hacía que un setpoint enviado como `21 °C` (`70 °F` por normalización segura) se reportara como `22 °C` y bloqueaba la confirmación de setpoint.
- `current_temperature` se conserva como lectura diagnóstica/interna del equipo y tampoco debe aplicar redondeos locales en Celsius. La lectura contractual para confirmar setpoint sigue siendo el atributo `temperature`, no `current_temperature`.
- `async_set_temperature()` sigue normalizando solicitudes Celsius convertidas por Home Assistant a Fahrenheit entero con `math.ceil()`, para evitar truncar hacia abajo valores como `21 °C ≈ 69.8 °F`.

### Protección anti-loop del refuerzo progresivo Night
- `AC Night Matriz Contextual` mantiene `input_number.ac_night_cool_reinforcement_count` como contador de refuerzos confirmados. Si el setpoint solicitado no confirma contra `state_attr(climate_ent, 'temperature')`, el contador no se marca como aplicado.
- Se agrega memoria operativa en `input_text.ac_night_cool_reinforcement_pending_payload` con climate, columna, refuerzo debido, setpoint solicitado, resultado, expiración y `retry_at`.
- Si un refuerzo no confirma, la matriz registra un cooldown de 600 segundos antes de reintentar el mismo paso (`due` + `sp`) para evitar tormentas por triggers inmediatos, incluyendo cambios de `current_temperature` del climate.
- El log `night_sp_progressive_reinforcement` ahora incluye `trigger_entity`, setpoint contractual, setpoint solicitado, setpoint reportado antes/final, `current_temperature` antes/después, refuerzos actuales/debidos, resultado de confirmación, cooldown aplicado y próxima hora de reintento.

## 2026-06-16 — GE/SmartHQ: reporte métrico entero para HVAC Fahrenheit interno

- **Alcance:** integración local `custom_components/ge_home/entities/common/ge_climate.py`.
- **Contrato interno del equipo:** los ERD del HVAC GE/SmartHQ siguen siendo Fahrenheit enteros y la entidad conserva `temperature_unit = UnitOfTemperature.FAHRENHEIT` para que Home Assistant mantenga el flujo nativo correcto.
- **Reporte en Home Assistant métrico:** cuando `ErdCode.TEMPERATURE_UNIT` está en `METRIC`, `target_temperature` y `current_temperature` convierten el Fahrenheit ERD a Celsius, aplican redondeo entero normal con `round(celsius)` y devuelven el equivalente Fahrenheit de ese Celsius entero. Así Home Assistant expone atributos métricos enteros como `19`, `21` o `22`, sin decimales físicos (`19.4`, `21.1`, `22.2`) y sin buckets artificiales de `2 °C`.
- **Regla anti-regresión:** no reintroducir `round(celsius / 2) * 2` ni cualquier normalización a múltiplos de `2 °C`; los valores impares como `19 °C`, `21 °C` y `23 °C` deben conservarse como enteros comparables.
- **Escritura de setpoint:** `async_set_temperature()` mantiene `math.ceil()` sobre la solicitud Fahrenheit ya convertida por Home Assistant para evitar truncamiento hacia abajo al Fahrenheit entero inferior. La comparación de cambio se hace contra el ERD bruto actual, no contra la lectura normalizada para UI.
- **Semántica operativa:** `temperature` es el setpoint objetivo usado para confirmar refuerzos y resincronizaciones; `current_temperature` es la lectura actual/interna del HVAC presentada con la misma normalización métrica entera.

---

## Contrato de notificaciones HVAC móviles

Las notificaciones móviles de HVAC son un **resumen humano y breve**, no un log técnico. La telemetría diagnóstica, estados internos, trazas, confirmaciones y cálculos auxiliares deben permanecer en `logbook.log` cuando sean necesarios para depuración.

### Títulos visibles
- Control diurno: `AC-Matriz Diurna`.
- Control nocturno: `AC-Matriz Nocturna`.

### Vocabulario visible obligatorio
- Usar `Ajuste de temp.` para la temperatura configurada del equipo.
- Usar `Compensación actualizada` para el nuevo ajuste aprendido.
- Usar `Ajuste especial` solo bajo la regla indicada abajo.
- Incluir `Humedad interior` en las notificaciones HVAC relevantes.

### Contexto obligatorio
Toda notificación móvil HVAC que muestre contexto de columna debe usar exactamente el patrón:

`Columna N (Condición externa | Estación del año | Horario HH:MM-HH:MM)`

No se deben usar contextos genéricos como `Noche`; siempre debe mostrarse la franja horaria concreta.

### Aprendizaje y ajuste especial
- Las notificaciones móviles de aprendizaje se envían solo cuando el aprendizaje queda aplicado.
- Los aprendizajes ignorados, descartados, deduplicados o bloqueados no envían notificación móvil; se registran solo en logs.
- La línea `Ajuste especial: temperatura fuera del rango esperado.` se muestra únicamente cuando exista anchor/ajuste especial aplicado.
- Si no aplica ajuste especial, no se muestra ninguna línea relacionada.
- La palabra técnica `anchor` y sus campos internos no deben aparecer en notificaciones móviles.

### Condición clara
- Usar `Despejado` como etiqueta visible de condición clara.
- No usar `Soleado - Despejado` en textos visibles.


## 2026-06-17 — AC Night: validación de ciclo nocturno contra helpers restaurados

- **Alcance:** automatización `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`) en `automations.yaml`.
- **Problema corregido:** `input_datetime.ac_night_cool_cycle_started_ts` podía restaurarse con un valor epoch/local (`1970-01-01`, observado como `28800`) o de una noche anterior. La automatización lo trataba como ciclo activo por ser mayor que cero, calculaba millones de minutos transcurridos y aplicaba hasta 3 refuerzos nocturnos de golpe al entrar en `2200_0059`.
- **Contrato nuevo:** el inicio del ciclo solo es válido si pertenece a la ventana nocturna operativa actual (22:00-07:00), no está en el futuro salvo tolerancia corta y la ejecución todavía está dentro de esa ventana. Valores epoch, vacíos, restaurados, futuros o de noches anteriores se descartan como `sin_ciclo`.
- **Refuerzos:** si el ciclo restaurado no es válido, `night_cycle_elapsed_min`, `night_reinforcement_count` y `night_reinforcement_due_count` se fuerzan a `0`; por tanto los refuerzos solo pueden vencer a los 20/50/80 minutos reales desde un inicio válido de la noche actual.
- **Limpieza transaccional:** al iniciar un ciclo limpio o resetearlo se limpia `input_text.ac_night_cool_reinforcement_pending_payload`, evitando que un payload de refuerzo viejo condicione el resync o el cooldown del ciclo nuevo.

## 2026-06-17 — AC Night: vencimiento progresivo 20/50/80 de refuerzos COOL

- **Alcance:** automatización `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`) en `automations.yaml`.
- **Ajuste operativo:** los refuerzos nocturnos de setpoint COOL ahora vencen a los **20/50/80 minutos** desde el inicio válido del ciclo nocturno, manteniendo el máximo de 3 refuerzos por ciclo y conservando la validación de helpers restaurados.
- **Observabilidad:** el motivo técnico del hito `night_sp_progressive_reinforcement` queda neutral como `refuerzo_progresivo_sin_llegar_a_off_cool`, sin referirse al umbral antiguo del primer refuerzo.

---

## AC-Matriz 160: mejora contextual COOL con memoria térmica y forecast

### Alcance exacto del cambio
Esta intervención mejora únicamente la **base contextual de COOL** de `AC-Matriz 160` (`id: ac_matriz_160_main_v1`). No cambia el aprendizaje manual, anchors, clasificación manual/automático, markers transaccionales, offsets aprendidos ni los helpers `input_number.ac_matriz_160_offset_cool_col_*` / `input_number.ac_matriz_160_offset_heat_col_*`.

La secuencia contractual se conserva: primero se calcula la base contextual (`t_off_cool_base` y `t_on_cool_base`) y después se aplica el offset aprendido de la columna (`offset_cool_helper`) para obtener `t_off_cool_shifted`, `t_on_cool_shifted`, `t_off_cool` y `t_on_cool`. La regla final sigue siendo que `t_on_cool = t_off_cool + 1.0`.

### Helpers auxiliares agregados
Los insumos auxiliares son técnicos, exclusivos de `AC-Matriz 160`, y no forman parte del aprendizaje:

- `input_number.ac_matriz_160_tout_1h_ago`: muestra exterior persistente para estimar tendencia de 1 hora.
- `input_number.ac_matriz_160_tin_30m_ago`: muestra interior persistente para estimar inercia de 30 minutos.
- `input_number.ac_matriz_160_forecast_max_temp_2h`: máxima temperatura prevista en las próximas 2 horas.
- `input_number.ac_matriz_160_forecast_rain_probability_2h`: probabilidad máxima de lluvia en próximas 2 horas.
- `input_number.ac_matriz_160_forecast_rain_amount_2h`: lluvia acumulada prevista en próximas 2 horas cuando la fuente la entrega.
- `input_datetime.ac_matriz_160_tout_memory_updated_ts`: timestamp de memoria exterior.
- `input_datetime.ac_matriz_160_tin_memory_updated_ts`: timestamp de memoria interior.
- `input_datetime.ac_matriz_160_forecast_updated_ts`: timestamp del forecast auxiliar.
- `input_text.ac_matriz_160_contextual_reliability`: resumen operativo (`ok`, `parcial`, `sin_forecast`, `sin_historial`, `error_controlado` o combinaciones parciales).

La automatización `AC-Matriz 160 - Memoria contextual y forecast` actualiza estos helpers periódicamente, lee `weather.openweathermap` y los mismos sensores internos que la matriz principal, y no cambia modo HVAC ni setpoint.

### Grupos de ajuste COOL
La base mantiene `base_cool = 24.0`, histéresis fija de `1.0` y el ajuste de franja existente. Sobre esa base se agrupan tres bloques:

1. **Clima actual (`adj_weather_now`)**: combina temperatura exterior, humedad exterior, punto de rocío y sensación térmica. Si punto de rocío o sensación térmica no existen, su aporte es `0`.
2. **Clima futuro (`adj_weather_future`)**: combina tendencia exterior de 1 hora, forecast de máxima temperatura en 2 horas y lluvia contextual.
3. **Carga real del apartamento (`adj_apartment_load`)**: combina diferencia interior-exterior e inercia térmica interior de 30 minutos.

El ajuste total se calcula como `adj_contextual_total = clamp(slot_cool_adjust + adj_weather_now + adj_weather_future + adj_apartment_load, -1.40, +0.80)`.

### Protecciones y degradación segura
Los clamps principales son:

- `adj_weather_now` en `[-1.00, +0.60]`.
- `adj_weather_future` en `[-0.60, +0.35]`.
- `adj_apartment_load` en `[-0.50, +0.30]`.
- `adj_contextual_total` en `[-1.40, +0.80]`.
- `t_off_cool_base` entre `thermal_boundary_by_season` y `26.0`.
- `t_off_cool` final conserva los límites contractuales existentes y `t_on_cool` se recalcula siempre como `t_off_cool + 1.0`.

Si faltan forecast, OWM, memoria madura o datos numéricos, el aporte afectado se fuerza a `0` y la automatización continúa. Esto permite operar después de reinicios o fallos temporales de integración sin romper YAML/Jinja ni bloquear la evaluación normal.

### Validación operativa recomendada
Para validar en operación:

1. Revisar logbook de `AC-Matriz 160` y confirmar que aparecen `adj_weather_now`, `adj_weather_future`, `adj_apartment_load`, `adj_contextual_total`, `adj_tout`, `adj_hout`, `adj_dew`, `adj_feels`, `adj_trend`, `adj_forecast`, `adj_rain`, `adj_delta_io`, `adj_inertia` y `confiabilidad_contextual`.
2. Confirmar que los helpers de memoria maduran tras aproximadamente 1 hora exterior y 30 minutos interior.
3. Confirmar que, sin forecast o sin historial maduro, la confiabilidad queda parcial y los ajustes dependientes permanecen en `0`.
4. Confirmar en los helpers efectivos que `input_number.ac_matriz_160_t_on_cool = input_number.ac_matriz_160_t_off_cool + 1.0`.
5. Probar escenarios manuales: día caliente/húmedo baja el umbral, tarde fresca con exterior bajando relaja el umbral, apartamento calentándose rápido anticipa encendido y ausencia de datos externos no causa errores.

## 76. AC Night Matriz Contextual — guardia anti-bochorno, compresor y fan seguro

- **Alcance:** automatización `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`), helpers nocturnos en `helpers/input_datetime.yaml`, `helpers/input_number.yaml` y `helpers/input_boolean.yaml`, y sensor de potencia `sensor.dormitorio_aire_acondicionado_0200009211c7_wac_demand_response_power` integrado en `sensors.yaml`.
- **Guardia anti-bochorno para auto-off COOL:** el apagado normal queda separado en `normal_off_ready = hvac_mode == 'cool' and tin <= off_cool`. Si el punto de rocío nocturno es al menos `14.8 °C` (o humedad/`bochorno_score` respaldan incomodidad), `muggy_guard_active` bloquea el apagado aunque `Tin` ya haya bajado del umbral. La guardia se libera por seguridad operativa con límite dinámico: `60 min` para bochorno moderado, `75 min` para bochorno alto y `90 min` para bochorno severo, salvo protección de sobreenfriamiento (`tin <= off_cool - 0.4`) que evita extender a 90 minutos. Las trazas diferenciadas son `night_auto_off_blocked_by_humidity_guard` y `night_auto_off_humidity_guard_released_by_timeout`, ambas reportando el límite dinámico usado.
- **Clasificación de bochorno:** se conservan `bochorno_score`, `temp_pressure`, `hum_pressure`, `dew_pressure` y la fórmula de `night_comfort_pressure`. La nueva capa añade `dew_moderate/high/severe` y `muggy_moderate/high/severe`, priorizando punto de rocío (`14.8`, `15.6`, `16.2 °C`) y usando humedad interior y `bochorno_score` como respaldo.
- **Contrato de compresor:** la fuente principal es `sensor.dormitorio_aire_acondicionado_0200009211c7_wac_demand_response_power` (valor en kW convertido internamente a W para los umbrales de compresor); como fallback se aceptan `sensor.ac_power_w`, `binary_sensor.ac_compressor_active` y atributos defensivos del climate (`hvac_action`, `action`, `compressor`, `compressor_state`, `running`). La matriz publica internamente `compressor_state = active | inactive_probable | unknown`, con umbrales iniciales de `350 W` para compresor y `120 W` para fan-only. `input_datetime.ac_night_compressor_last_active_ts` mide cuánto lleva el equipo en COOL sin evidencia de compresor activo.
- **Baseline de ciclo y mejora higrométrica:** al iniciar o detectar un ciclo COOL nocturno se guardan `Tin`, humedad interior y punto de rocío en `input_number.ac_night_tin_at_cycle_start`, `input_number.ac_night_hin_at_cycle_start` e `input_number.ac_night_dew_at_cycle_start`; `input_datetime.ac_night_last_humidity_check_ts` deja memoria de chequeo. A partir de 20 minutos se consideran `dew_not_improving` y `humidity_not_improving` cuando el punto de rocío/humedad siguen altos sin mejora suficiente.
- **Refuerzo de setpoint por humedad:** se mantiene el mínimo HVAC, máximo de 3 refuerzos, contador `input_number.ac_night_cool_reinforcement_count`, firma de ciclo y payload pendiente con retry/confirmación. Además de la presión térmica normal, puede reforzar por `muggy_high/severe`, falta de mejora de punto de rocío/humedad o compresor probablemente inactivo con bochorno alto. Los escalones por humedad son: severo desde `15/35/55 min`, alto desde `20/45/70 min`, y normal conserva `20/50/80 min`. Las trazas diferencian `night_humidity_based_sp_reinforcement` y `night_humidity_compressor_inactive_reinforcement`.
- **Fan seguro:** con compresor activo puede subir a `Med` si hay bochorno alto y a `High` si es severo y está soportado. Con `compressor_state=inactive_probable` no se sube fan y se prioriza bajar SP. Con `compressor_state=unknown` se mantiene `Low`, salvo que `input_boolean.ac_night_enable_humidity_fan_boost` habilite explícitamente un boost experimental acotado por `input_datetime.ac_night_humidity_fan_boost_started_ts` a 15 minutos. Los cambios de fan usan `night_humidity_fan_adjustment`.

## 77. AC Night — separación de confort térmico y guardia de humedad (2026-07-16)

- **Alcance:** automatización `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`) en `automations.yaml`.
- **Causa corregida:** `bochorno_score` es una presión de confort compuesta que incluye `temp_pressure`; por ello podía activar `muggy_moderate/high/severe` y bloquear un apagado COOL aun con humedad relativa y punto de rocío normales.
- **Contrato nuevo de humedad real:** `muggy_moderate`, `muggy_high` y `muggy_severe` dependen exclusivamente de humedad interior (`58/62/63 %`) o de punto de rocío (`14.8/15.6/16.2 °C`). `muggy_guard_active` reutiliza `muggy_moderate`, por lo que las extensiones de 60/75/90 minutos, refuerzos `humidity_dew`/`compressor_inactive_muggy` y ajustes de ventilador por humedad usan la misma clasificación higrométrica real.
- **Confort térmico preservado:** `temp_pressure`, `hum_pressure`, `dew_pressure`, `night_comfort_pressure`, `bochorno_score`, `comfort_pull`, `hysteresis_eff`, `off_cool`, `on_cool` y el setpoint contextual conservan su función térmica. En particular, `bochorno_score` sigue ajustando confort, pero ya no puede bloquear por sí solo el apagado mediante la guardia de humedad.
- **Diagnóstico:** se añade `muggy_guard_reason` (`dew_*`, `humidity_*` o `none`) a los logs de bloqueo/liberación de guardia, refuerzos por humedad y ajustes de ventilador. Esos logs conservan `bochorno_score`, `temp_pressure`, `hum_pressure` y `dew_pressure` para diferenciar presión de confort de humedad real.

---

## Anexo: escenarios operativos críticos de `AC Night Matriz Contextual`

Este anexo documenta los escenarios principales de la automatización nocturna `AC Night Matriz Contextual` (`id: ac_night_matrix_v1`) para facilitar mantenimiento por IA o por programadores.

### 1. Encendido nocturno normal
- **Valores de entrada**: horario entre 22:00 y 07:00, presencia estable activa, `hvac_mode != cool`, `tin >= on_cool`, sin bloqueo manual vigente.
- **Variables clave calculadas**: `dew_point_night` se calcula con Magnus simplificado; `dew_pressure` alimenta `night_comfort_pressure` y `bochorno_score`; `sp_cool_target` sale del contrato nocturno; `humidity_fan_target` normalmente queda en `Low` salvo bochorno y compresor activo.
- **Acción esperada**: cambiar el equipo a `cool`, solicitar `sp_cool_target`, iniciar ciclo nocturno, guardar temperatura/humedad/punto de rocío iniciales y dejar contador de refuerzos en cero.
- **Log esperado**: `hito=night_auto_on_notified` con `dew`, `bochorno_score`, `sp_contractual`, `sp_solicitado` y `resultado_terminal=turn_on_cool` si el setpoint queda confirmado.

### 2. Refuerzo progresivo por tiempo
- **Valores de entrada**: ciclo nocturno activo en `cool`, presencia estable, `tin > off_cool`, sin señales fuertes de bochorno, y `night_cycle_elapsed_min` cruza los tramos progresivos de 20, 50 u 80 minutos.
- **Variables clave calculadas**: `night_reinforcement_due_count_normal`, `night_reinforcement_due_count`, `night_reinforcement_primary_cause=thermal_progressive`, `night_reinforcement_flags` con señales de humedad/compresor en `0` cuando no aplican.
- **Acción esperada**: bajar temporalmente el setpoint solicitado a `sp_cool_reinforced_next` sin modificar el mínimo nocturno configurable porque esa mejora queda explícitamente fuera de alcance.
- **Log esperado**: `hito=night_sp_progressive_reinforcement`, `causa_principal=thermal_progressive`, `banderas=...`, `motivo=thermal_progressive` y `resultado_terminal=reinforcement` cuando confirma.

### 3. Refuerzo por punto de rocío o humedad
- **Valores de entrada**: ciclo nocturno activo en `cool`, presencia estable, `muggy_high`/`muggy_severe` verdadero o `dew_not_improving`/`humidity_not_improving` verdadero tras al menos 20 minutos.
- **Variables clave calculadas**: `dew_point_night` con Magnus simplificado; `dew_pressure` alimenta `night_comfort_pressure`; `bochorno_score` conserva esa presión de confort; `night_reinforcement_primary_cause` prioriza `dew_not_improving`, `humidity_not_improving`, `muggy_severe` o `muggy_high` según corresponda.
- **Acción esperada**: aplicar el siguiente refuerzo nocturno permitido y ajustar ventilador a `Med`/`High` solo cuando la lógica de `humidity_fan_target` lo requiera.
- **Log esperado**: `hito=night_humidity_based_sp_reinforcement`, con `causa_principal` específica y `banderas` compactas para separar causa principal de señales secundarias.

### 4. Refuerzo por compresor inactivo con bochorno
- **Valores de entrada**: `hvac_mode=cool`, `compressor_state=inactive_probable`, `muggy_high=true` y ciclo nocturno activo con refuerzo pendiente.
- **Variables clave calculadas**: `compressor_inactive_while_cool=true`, `night_reinforcement_primary_cause=compressor_inactive_muggy`, `night_reinforcement_reason=compressor_inactive_muggy` para conservar compatibilidad con el log existente.
- **Acción esperada**: mantener la decisión térmica existente y reforzar setpoint si corresponde; la nueva observabilidad no convierte `unknown` en acción agresiva.
- **Log esperado**: `hito=night_humidity_compressor_inactive_reinforcement`, `causa_principal=compressor_inactive_muggy`, `banderas=...compressor_inactive=1`, `compressor_state=inactive_probable`.

### 5. Apagado normal por temperatura alcanzada
- **Valores de entrada**: `hvac_mode=cool`, `tin <= off_cool`, presencia estable o condición de apagado aplicable, y `muggy_guard_active=false`.
- **Variables clave calculadas**: `normal_off_ready=true`, `muggy_guard_active=false`, `muggy_guard_force_release` no es necesario para permitir apagado.
- **Acción esperada**: apagar el climate, limpiar ciclo nocturno, reiniciar refuerzos y payloads pendientes.
- **Log esperado**: `hito=night_auto_off_confirmed_notified` con `resultado_terminal=turn_off_confirmed`; en apagado por ausencia también puede verse `hito=night_auto_off_notified`.

### 6. Apagado bloqueado por `muggy_guard_active`
- **Valores de entrada**: `hvac_mode=cool`, `tin <= off_cool`, presencia estable, `muggy_guard_active=true` y `night_cycle_elapsed_min < muggy_guard_max_elapsed_min`.
- **Variables clave calculadas**: `muggy_guard_max_elapsed_min` dinámico: 60 minutos si el bochorno es moderado, 75 si es alto, 90 si es severo, excepto que con `tin <= off_cool - 0.4` no se extiende a 90 minutos.
- **Acción esperada**: no apagar todavía para no cortar el trabajo de deshumidificación percibida.
- **Log esperado**: `hito=night_auto_off_blocked_by_humidity_guard`, con `max_elapsed` y `limite_dinamico_min` reportando el límite dinámico activo.

### 7. Apagado liberado por timeout dinámico
- **Valores de entrada**: `normal_off_ready=true`, `muggy_guard_active=true` y `night_cycle_elapsed_min >= muggy_guard_max_elapsed_min`.
- **Variables clave calculadas**: `muggy_guard_force_release=true`; el límite usado depende de severidad y protección de sobreenfriamiento.
- **Acción esperada**: permitir apagado aunque siga la señal de bochorno para evitar ciclos nocturnos excesivamente largos.
- **Log esperado**: `hito=night_auto_off_humidity_guard_released_by_timeout`, con `max_elapsed` y `limite_dinamico_min` iguales al límite dinámico que liberó el apagado.

### 8. Resync de setpoint/fan
- **Valores de entrada**: `hvac_mode=cool`, presencia estable, ciclo activo y `night_resync_sp_needed=true` o `night_resync_fan_needed=true`.
- **Variables clave calculadas**: `sp_cool_effective` sigue usando el contrato actual y los refuerzos existentes; `humidity_fan_target` puede cambiar por bochorno y estado de compresor; no se agrega `night_min_comfort_sp` en esta intervención.
- **Acción esperada**: reescribir setpoint efectivo o fan esperado sin reiniciar el ciclo nocturno.
- **Log esperado**: `hito=night_sp_resync` para setpoint y/o `hito=night_humidity_fan_adjustment` con `resultado_terminal=resync` para fan.

### Diagnóstico adicional: compresor desconocido persistente
- **Valores de entrada**: `compressor_state=unknown` más de una vez dentro del mismo ciclo nocturno.
- **Variables clave calculadas**: `compressor_unknown_next_count`, `compressor_unknown_repeated` y payload `input_text.ac_night_compressor_unknown_diag_payload`.
- **Acción esperada**: registrar observabilidad de baja confianza sin cambiar la decisión térmica basada en `unknown`.
- **Log esperado**: `hito=night_compressor_state_low_confidence`, `compressor_state=unknown`, `ac_power_w`, estado de `binary_sensor.ac_compressor_active`, `hvac_action` y `night_cycle_elapsed_min`.

## 76) AC-Matriz 160 — protección contra colisión manual ON + auto-OFF tardío (2026-06-20)

- **Alcance:** automatizaciones `AC-Matriz 160` (`id: ac_matriz_160_main_v1`) y `AC-Matriz 160 - Aprendizaje manual por columna` (`id: ac_matriz_160_learning_manual_v1`) en `automations.yaml`.
- **Revalidación previa al apagado:** antes de ejecutar una rama `turn_off`, la automatización principal vuelve a leer modo HVAC, Tin y helpers operacionales `t_off_cool`/`t_off_heat`. Si la demanda ya no confirma el apagado con los umbrales actuales, registra `hito=turn_off_cancelled_by_revalidation` y cancela la rama para evitar apagar con una decisión calculada antes de un aprendizaje manual.
- **TTL de marcador automático en apagados:** para `action_target=turn_off`, el marcador `ac_matriz_160_auto_origin_*` usa una vigencia extendida de 180 s, cubriendo el secado `post_cool_dry`, el apagado final y eventos derivados inmediatos.
- **Clasificación de cierres automáticos tardíos:** el learning considera `cierre_automatico_tardio` cuando llega un `cool/heat -> off` poco después de un marcador automático `turn_off` expirado pero aún no consumido. Ese evento termina como `ignorado`, con `aprendizaje_aplicado_o_bloqueado=bloqueado`, `delta=0` efectivo y sin mover el offset.
- **Sincronización inmediata post-aprendizaje:** cuando un aprendizaje manual aplicado cambia offset, el learning sincroniza inmediatamente los helpers operacionales `t_off/t_on` del modo afectado y `input_text.ac_matriz_160_contexto_firma_activa`, para que la reconciliación y la principal usen el bloque actualizado.
- **Anti-aprendizaje por ciclo corto:** tras un encendido manual aprendido se abre una guarda de 5 min (`manual_on_learning_short_cycle_guard_set`) usando el rebound existente. Un apagado manual dentro de esa ventana se ignora con `razon=conflicto_post_encendido_manual`, evitando que desacuerdos entre usuarios o colisiones con auto-OFF contaminen el offset recién aprendido.
- **Reconciliación fan_only protegida:** `fan_only -> cool/heat` deja de considerarse reconciliable si hay evidencia reciente de un `turn_off` automático de AC-Matriz, incluso si el marker acaba de expirar. Esto evita revivir `cool` durante el secado post-cool salvo que exista una cancelación explícita del apagado automático.

## 77) AC-Matriz 160 — guardia temprana Manual ON contra auto-OFF viejo (2026-06-21)

- **Alcance:** automatizaciones `AC-Matriz 160` (`id: ac_matriz_160_main_v1`) y `AC-Matriz 160 - Aprendizaje manual por columna` (`id: ac_matriz_160_learning_manual_v1`), más helpers de trazabilidad en `helpers/input_datetime.yaml` y `helpers/input_text.yaml`.
- **Detección temprana:** la matriz principal detecta candidatos de encendido manual COOL por transición real del climate `off->cool` o `fan_only->cool`, siempre que no exista marcador automático vigente compatible ni coincidencia clara con la cadena automática de `AC-Matriz 160` por contexto o parent/root.
- **Hold corto Manual ON:** ante candidato manual se crea o respeta `input_datetime.ac_matriz_160_manual_on_hold_until` por 3 minutos y se registran `manual_on_candidate_detected` y `manual_on_hold_created`. Este hold es una guarda operativa anti-colisión, no un cambio de contrato térmico.
- **Defensa primaria antes de fan_only:** si la corrida ya traía una decisión `action_target=turn_off`, la rama destructiva revalida inmediatamente Tin, `OFF/ON` COOL frescos, offset, setpoint contractual y fan objetivo antes de iniciar secado. Si `Tin > OFF_fresco`, cancela antes de `fan_only`, mantiene/restaura `cool`, reescribe SP contractual y fan válido, suprime notificación de apagado automático y registra `turn_off_blocked_before_fan_only_by_manual_on`, `turn_off_revalidated_with_fresh_thresholds`, `turn_off_cancelled_by_manual_on_hold` y `cool_restored_after_cancelled_turn_off`.
- **Aprendizaje como señal secundaria:** el learning escribe `input_datetime.ac_matriz_160_manual_learning_applied_ts`, `input_text.ac_matriz_160_last_manual_learning_root` e `input_text.ac_matriz_160_manual_learning_result`; la matriz principal usa esa evidencia reciente como protección adicional y registra `turn_off_cancelled_by_manual_learning` cuando aplica.
- **Defensa secundaria:** se conserva una revalidación justo antes de `climate.turn_off` al final del secado post-cool. Esta defensa solo cubre carreras tardías; el mecanismo principal es el guard previo a `fan_only`.

## 2026-06-23 — AC Night: anchor de apagado manual COOL por encima de `on_cool`

- **Alcance:** automatización `AC Night - Aprendizaje manual por columna` (`id: ac_night_learning_manual_v1`) en `automations.yaml`.
- **Caso corregido:** cuando una acción `manual_externo` apaga el HVAC en frío (`cool->off`) con `Tin > on_cool_vigente`, el aprendizaje ya no cae en `delta_standard` con delta potencialmente cero. Esa intención humana se interpreta como “esta temperatura ya es suficientemente cómoda y no quiero más frío”.
- **Nueva rama:** `decision_branch=manual_off_anchor_above_on`, con prioridad antes de `delta_standard`.
- **Cálculo:** el objetivo absoluto de apagado aprendido es `off_cool_manual_off_anchor_obj = Tin + 0.25`. Como el helper `input_number.ac_night_offset_cool_col_X` guarda offset, se calcula `offset_manual_off_anchor_raw = off_cool_manual_off_anchor_obj - off_cool_base - exterior_adjust_cool + comfort_pull`, se limita a `[-3.0, 3.0]` y se usa como `offset_new` solo para esta rama.
- **Observabilidad:** el payload caliente, logs y notificación exponen `manual_off_anchor`, `off_manual_anchor_obj`, `manual_off_anchor_clamped`, `thermal_clamped`, `delta_aplicado_real`, `offset_manual_off_anchor_raw`, `offset_manual_off_anchor_clamped` y `manual_off_anchor_limited_by_thermal_clamp` para distinguir objetivo del anchor, clamp de offset y clamp térmico (`off_cool_resultante` sigue respetando `[22.7, 24.2]`).

## 78) AC-Matriz 160 — encendido asistido autoritativo y secado no bloqueante (2026-07-19)

- **Causa confirmada:** un gesto físico `off -> fan_only` quedaba sin asistencia cuando `Tin` no había cruzado el umbral automático `OFF`. Además, el secado post-cool bloqueaba dos minutos la automatización principal en `mode: single`; una corrida antigua podía ignorar eventos posteriores y apagar incluso después de un aprendizaje Manual ON que ya había actualizado el contrato.
- **Encendido asistido:** `off -> fan_only` con presencia, horario válido, AUTO habilitado y sin bloqueos de seguridad se considera intención manual autoritativa. La selección entre `cool` y `heat` continúa usando el contexto vigente. La comprobación térmica se conserva como telemetría, pero no bloquea la asistencia.
- **Precedencia Manual ON:** cada candidato Manual ON renueva `input_datetime.ac_matriz_160_manual_on_hold_until` a `now + 3 min`. Mientras exista candidato, hold o aprendizaje Manual ON reciente, una decisión `turn_off` se cancela sin depender de la relación entre `Tin` y el `OFF` anterior.
- **Secado no bloqueante:** el apagado desde `cool` cambia a `fan_only/Low`, persiste un payload correlacionado en `input_text.ac_matriz_160_post_cool_dry_payload`, inicia `timer.ac_matriz_160_post_cool_dry` por dos minutos y finaliza la corrida principal.
- **Cierre revalidado:** `AC-Matriz 160 - Cierre secado post-cool` vuelve a leer modo, promedio de sensores, umbral vigente y evidencia manual. Solo apaga si el equipo continúa en `fan_only`, `Tin <= OFF` fresco y no hubo intervención o aprendizaje posterior. Un modo modificado, evidencia Manual ON o `Tin > OFF` cancela el apagado; solo se restaura `cool` cuando el equipo aún permanece en `fan_only`.
- **Cancelación temprana:** un nuevo candidato Manual ON cancela inmediatamente el timer y el payload pendientes, cambia la fase a `normal` y registra `hito=post_cool_dry_cancelled_by_manual_on`.
- **Observabilidad:** se agregan los hitos `manual_fan_only_assisted_started`, `post_cool_dry_scheduled`, `post_cool_dry_cancelled_by_manual_on`, `post_cool_dry_cancelled_by_fresh_contract` y `post_cool_dry_completed`.
- **Archivos afectados:** `automations.yaml`, `helpers/timer.yaml`, `helpers/input_text.yaml` y este documento.
