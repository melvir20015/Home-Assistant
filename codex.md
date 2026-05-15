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
- `timer.hvac_post_cool_dry` — secado post-cool (3 min).

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
5. Si hay persistencia incompleta previa al trigger, validar que exista `Resultado=error_controlado` (sin cierre silencioso).

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

Al terminar ciclo de `cool`, activar `fan_only` por **3 minutos** para secado post-cool y reducción de humedad residual del sistema.

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
