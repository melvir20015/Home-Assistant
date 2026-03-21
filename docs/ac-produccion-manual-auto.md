# AC en producción: contrato funcional manual vs automático

## Objetivo operativo

Este documento deja explícito cómo debe comportarse el sistema del AC en producción para que futuras revisiones no tengan que reconstruir el modelo mental desde cero.

## Qué cuenta como evento manual

Se considera **manual** cualquier cambio real del `climate.0200009211c7_climate` iniciado por el usuario desde:

- botón físico del equipo;
- control IR;
- app nativa del AC;
- interfaz manual de Home Assistant.

Ese cambio sólo cuenta como manual si **no** hay una bandera automática activa:

- `input_boolean.ac_on_por_automatizacion`;
- `input_boolean.ac_off_por_automatizacion`.

La clasificación de origen simple queda en `input_text.ac_last_change_origin` con uno de estos valores:

- `auto_on`
- `auto_off`
- `manual_on`
- `manual_off`

La clasificación semántica más detallada queda en `input_text.ac_last_manual_event_type`, por ejemplo:

- `manual_on_due_to_presence_gap`
- `manual_on_due_to_presence_gap_cool`
- `manual_on_due_to_comfort_gap_cool`
- `manual_off_detected_after_recent_auto_on_cool`

## Qué cuenta como evento automático

Se considera **automático** cualquier acción disparada por la lógica propia del sistema y envuelta por sus banderas:

- antes de cada `AUTO ON` se debe encender `input_boolean.ac_on_por_automatizacion`;
- antes de cada `AUTO OFF` se debe encender `input_boolean.ac_off_por_automatizacion`;
- al final de cada secuencia deben apagarse;
- si quedaran pegadas, la automatización de saneamiento defensivo debe limpiarlas.

Esto evita que un cambio provocado por la automatización contamine las detecciones de `manual_on` o `manual_off`.

## Helper crítico: `input_select.ac_ultimo_modo_no_fan`

Este helper es crítico y sólo admite estas opciones exactas:

- `off`
- `cool`
- `heat`
- `emergency_cool`

Reglas:

- `off` es el único estado de reposo válido;
- jamás deben persistirse `False`, `false`, `idle` ni valores equivalentes;
- si Home Assistant restaura un valor legacy inválido, debe normalizarse inmediatamente a `off`;
- `states('input_select.ac_ultimo_modo_no_fan')` debe devolver siempre texto válido del conjunto anterior.

Verificación y reconciliación en runtime/UI:

1. En **Developer Tools → States**, `input_select.ac_ultimo_modo_no_fan` debe exponer únicamente `off`, `cool`, `heat`, `emergency_cool`.
2. Si todavía aparece la opción legacy `False`, el runtime no quedó sincronizado con `input_select.yaml`; en ese caso hay que **recargar helpers YAML o recrear la entidad persistida** hasta que desaparezca `False`.
3. La automatización `AC - Normaliza helper último modo no fan` debe conservarse como red de seguridad, pero no sustituye la corrección del helper cargado: primero debe existir la opción `off` en runtime y sólo después esa automatización puede reparar estados restaurados inválidos.

## Presencia temporal por encendido manual

Si el usuario enciende manualmente el AC cuando `presence_effective` era falsa, eso se interpreta como señal válida de:

- presencia no detectada, o
- falta de confort no bien capturada por la rama automática.

En ese caso:

- se clasifica como `manual_on_due_to_presence_gap*`;
- se extiende `input_datetime.ac_manual_presence_until`;
- la automatización principal debe respetar esa presencia temporal;
- mientras esa presencia temporal siga vigente, el sistema no debe apagar enseguida el AC por ausencia.

## Ventana de estabilización tras `manual_on`

Después de un encendido manual hay una ventana corta de protección usando:

- `input_datetime.ac_last_manual_on_ts`;
- `input_datetime.ac_last_manual_final_ts`.

Durante esa ventana la automatización principal no debe:

- cambiar `hvac_mode`,
- corregir `fan_mode`,
- corregir setpoint térmico,
- ni apagar el equipo.

La intención es no “pisar” un encendido manual reciente mientras el usuario termina de ajustar el estado final del AC.

## Pausa operativa de 5 minutos tras `manual_off`

El único bloqueo corto tras apagado manual es una pausa anti-rebote de 5 minutos basada en:

- `input_datetime.ac_last_manual_off_ts`.

Su propósito es evitar que el sistema vuelva a hacer `AUTO ON` inmediatamente después de que el usuario acaba de apagar manualmente.

No debe reintroducirse la lógica vieja de pausa larga con `timer.ac_pausa_manual_off_1h`.

## Aprendizaje por `manual_off`

Si el usuario apaga manualmente después de un `AUTO ON` reciente y válido:

- eso debe quedar registrado como feedback manual real;
- el aprendizaje debe ser perceptible en producción;
- para `cool`, cada `manual_off` válido tras `AUTO ON cool` debe sumar `+0.25` a:
  - `input_number.ac_bias_cool_on`
  - `input_number.ac_bias_cool_off`

Eso hace que futuros `AUTO ON cool` requieran una condición más exigente antes de volver a encender.

## Aprendizaje por `manual_on`

Si el usuario vuelve a encender manualmente poco después de un `AUTO OFF` válido:

- eso cuenta como feedback manual útil;
- se clasifica en `input_text.ac_last_manual_learning_type`;
- los sesgos del modo correspondiente se ajustan para retrasar apagados automáticos futuros mal calibrados.

## Papel de `emergency_cool`

`emergency_cool` no es el flujo normal de enfriamiento.

Debe reservarse para calor realmente severo y no debe dominar escenarios que todavía corresponden a `cool` normal. En especial:

- no debe atrapar un `manual_on` reciente en una secuencia automática que lo pase a `fan_only` y luego a `off`;
- el latch de emergencia debe limpiarse cuando ya no corresponda;
- el sistema debe preferir `cool` normal cuando las condiciones no justifican emergencia.

## Telemetría mínima obligatoria

La trazabilidad debe quedar en helpers o logbook, no en spam de notificaciones push.

Helpers especialmente útiles:

- `input_text.ac_last_auto_branch`
- `input_text.ac_last_auto_action`
- `input_text.ac_last_auto_mode`
- `input_text.ac_last_auto_fan`
- `input_text.ac_last_manual_event_type`
- `input_text.ac_last_manual_learning_type`
- `input_text.ac_last_manual_feedback_mode`
- `input_text.ac_last_change_origin`

También son críticos:

- `input_select.ac_ultimo_modo_no_fan`
- `input_boolean.ac_on_por_automatizacion`
- `input_boolean.ac_off_por_automatizacion`
- `input_datetime.ac_last_auto_ts`
- `input_datetime.ac_last_manual_on_ts`
- `input_datetime.ac_last_manual_final_ts`
- `input_datetime.ac_last_manual_off_ts`
- `input_datetime.ac_manual_presence_until`

## Notificaciones de producción

En producción deben ser pocas, cortas y sólo útiles. Ejemplos válidos:

- `AC aprendió: OFF manual tras AUTO COOL | +0.25 on/off`
- `AC aprendió: ON manual por ausencia | presencia temporal activada`
- `AC AUTO OFF: ausencia 30m`

No se deben enviar notificaciones por:

- evaluaciones internas;
- abortos de ramas automáticas;
- detecciones manuales sin aprendizaje válido;
- debug técnico que ya queda en logbook.

## Snapshots JSON recomendados para diagnóstico futuro

Para futuras sesiones de análisis, el usuario puede aportar un **snapshot JSON de Home Assistant**. Es una entrada válida y recomendada porque acelera mucho el diagnóstico sin reconstruir todo manualmente.

El snapshot ideal debería incluir:

- estados actuales;
- helpers;
- entidades `climate`;
- automatizaciones relacionadas;
- timers;
- contexto operativo general.

Partes especialmente útiles del snapshot:

- `input_select.ac_ultimo_modo_no_fan`
- `input_boolean.ac_on_por_automatizacion`
- `input_boolean.ac_off_por_automatizacion`
- helpers `ac_last_auto_*`
- helpers `ac_last_manual_*`
- entidades de presencia
- `climate` del AC
- `weather`
- automatizaciones AC relacionadas

## Qué debe verificar cualquier revisión futura

1. Un `manual_on` desde la UI de HA sigue contando como manual cuando no hay bandera automática activa.
2. Un `manual_on` reciente no es convertido enseguida a `fan_only`, `low` ni `off`.
3. Un `manual_on` en ausencia activa presencia temporal coherente.
4. Un `manual_off` tras `AUTO ON cool` retrasa perceptiblemente futuros `AUTO ON`.
5. Las banderas automáticas no quedan pegadas.
6. `input_select.ac_ultimo_modo_no_fan` nunca vuelve a `False`/`false`.
