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
