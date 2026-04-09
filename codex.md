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
