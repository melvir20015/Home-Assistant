# Contrato funcional del aprendizaje por apagado manual del AC

## Objetivo

Cuando el AC se enciende por `AUTO ON` y el usuario lo apaga manualmente poco después, el sistema debe interpretar ese apagado como evidencia de que el encendido automático fue demasiado agresivo. El efecto esperado es que futuros `AUTO ON` exijan una condición térmica más extrema antes de volver a encender.

## Qué cuenta como apagado manual

Se considera **apagado manual** cualquier transición de `climate.0200009211c7_climate` a `off` que **no** ocurra mientras `input_boolean.ac_off_por_automatizacion` está en `on`.

Eso incluye apagados hechos desde:

- botón físico del AC;
- control IR;
- app nativa del AC;
- interfaz manual de Home Assistant, siempre que no provenga de una automatización.

La automatización `AC - Manual OFF guard + pausa 5 min` es la única responsable de registrar ese evento inicial en:

- `input_datetime.ac_last_manual_off_ts`;
- `input_text.ac_last_manual_event_type`;
- `input_text.ac_last_change_origin = manual_off`.

## Qué cuenta como apagado automático

Se considera **apagado automático** cualquier `OFF` provocado por una automatización propia del sistema mientras la bandera `input_boolean.ac_off_por_automatizacion` permanece activa.

Contrato operativo:

1. la bandera se enciende **antes** de emitir el `AUTO OFF`;
2. se mantiene activa durante toda la secuencia del apagado;
3. se limpia sólo después de una demora corta de protección, para que la entidad `climate` ya haya estabilizado el cambio;
4. mientras la bandera está activa, ningún flujo de `Manual OFF` ni de aprendizaje debe tratar el evento como manual.

## Aprendizaje esperado después de un `manual_off`

La automatización `AC - Learning - Manual OFF feedback` debe activarse **después** de que el evento manual ya quedó registrado en `input_datetime.ac_last_manual_off_ts`.

Sólo hay aprendizaje válido cuando se cumple todo esto:

- `input_boolean.ac_learning_enabled` está en `on`;
- `input_text.ac_last_change_origin` sigue indicando `manual_off`;
- la última acción automática registrada fue `auto_on`;
- el último modo automático aprendible fue `cool` o `heat`;
- el apagado manual ocurrió dentro de `input_number.ac_feedback_window_minutes`.

## Sesgos que deben cambiar

### Si el último `AUTO ON` fue `cool`

- subir `input_number.ac_bias_cool_on` en **`+0.25` fijo por evento válido** para retrasar futuros `AUTO ON` en frío;
- subir `input_number.ac_bias_cool_off` en **`+0.25` fijo por evento válido** para apagar antes bajo condiciones equivalentes, cuando ese criterio siga aplicando;
- subir `input_number.ac_bias_cool_setpoint` si el apagado manual fue rápido, para enfriar menos agresivamente.

Ese ajuste de `cool` debe tratarse como una **señal fuerte de “encender más tarde”** y, por lo tanto, no debe depender de `input_number.ac_learning_rate_small` ni de `input_number.ac_learning_rate_large`. Las tasas de aprendizaje generales pueden seguir modulando otras ramas, pero esta rama concreta debe producir siempre el mismo resultado real: `+0.25 on/off` por cada apagado manual válido en `cool`.

### Si el último `AUTO ON` fue `heat`

- bajar `input_number.ac_bias_heat_on` para retrasar futuros `AUTO ON` de calefacción;
- bajar `input_number.ac_bias_heat_off` para cortar antes el calentamiento, cuando corresponda;
- bajar `input_number.ac_bias_heat_setpoint` si el apagado manual fue rápido, para calentar menos agresivamente.

## Cómo esos sesgos retrasan futuros `AUTO ON`

La automatización `AC - Día dinámico aprendido (principal)` usa los sesgos aprendidos para modificar umbrales reales:

- `ac_bias_cool_on` se suma al cálculo de `cool_on`; un valor más alto obliga a una temperatura interior más alta antes de encender en `cool`.
- `ac_bias_heat_on` se suma al cálculo de `heat_on`; como el aprendizaje por `manual_off` lo vuelve más negativo, obliga a una temperatura interior más baja antes de encender en `heat`.
- los sesgos `*_off` y `*_setpoint` ajustan la agresividad de apagado y el setpoint final para acompañar la misma intención del usuario.

En consecuencia, la pausa anti-rebote de 5 minutos sólo evita reencendidos inmediatos, mientras que los sesgos aprendidos siguen afectando decisiones futuras incluso después de que esa pausa termina.

## Trazabilidad mínima requerida

Sin generar spam de notificaciones push, el sistema debe dejar trazabilidad suficiente en helpers/logbook para reconstruir:

- cuándo se detectó el `manual_off`;
- qué tipo de evento manual se clasificó;
- cuál fue el último `auto_on` relacionado;
- qué `learning_type` final resultó;
- qué sesgos cambiaron cuando hubo aprendizaje válido.

## Política de notificaciones

En producción sólo deben existir notificaciones breves cuando hubo aprendizaje válido real, por ejemplo:

- `AC aprendió: OFF manual tras AUTO COOL | +0.25 on/off | +0.5 setpoint`
- `AC aprendió: OFF manual tras AUTO HEAT | -0.10 on/off`

## Límites máximos de seguridad

Los sesgos aprendidos deben permanecer acotados para evitar que varios eventos seguidos vuelvan al sistema excesivamente pasivo o inestable.

- `input_number.ac_bias_cool_on` debe seguir limitado a un máximo de `+3.00`.
- `input_number.ac_bias_cool_off` debe seguir limitado a un máximo de `+3.00`.
- Si un nuevo evento intenta superar ese tope, el valor debe saturarse en el límite y no crecer más.

Con ese límite, incluso usando un paso fijo de `+0.25`, el sistema conserva memoria útil del feedback manual sin desbordar la lógica base ni desplazar indefinidamente los umbrales.

No deben enviarse notificaciones push de debug para `AUTO ON evaluado`, `AUTO ON abortado` ni para aprendizajes ignorados.

## Capa unificada de resultado de aprendizaje manual (ON/OFF)

Desde esta versión, tanto `AC - Learning - Manual OFF feedback` como `AC - Learning - Manual ON feedback`
usan una capa común de resultado con dos estados mutuamente excluyentes:

1. `evaluated_not_applied`: el evento manual se evaluó, pero no hubo cambios reales en umbrales/sesgos.
2. `applied_with_real_changes`: el evento manual sí produjo cambios reales.

El helper `input_text.ac_last_manual_learning_type` ahora persiste el resultado en formato:

- `applied_with_real_changes:<detalle>`
- `evaluated_not_applied:<detalle>`

Ejemplos:

- `applied_with_real_changes:manual_off_learning_applied`
- `evaluated_not_applied:manual_on_learning_ignored_antirebote`

### Contrato del mensaje estructurado

Cuando el aprendizaje es **aplicado** (`applied_with_real_changes`), se emite push móvil estructurado
con título:

- `AC aprendizaje manual OFF` (rama OFF)
- `AC aprendizaje manual ON` (rama ON)

Campos obligatorios del mensaje (una línea por campo):

1. `accion_manual_detectada` (`ON`/`OFF`)
2. `resultado_aprendizaje_efectivo` (`sí`/`no`)
3. `peso_aplicado` (si no aplica: valor calculado igualmente reportado)
4. `cambio_aplicado` (ej: `Off +0.25 | On +0.25 | Setpoint +0.0`)
5. `umbral_antes_despues` (ej: `Off 24.00→24.25 | On 24.50→24.75`)
6. `contexto` (bucket/rama/franja/presencia/humedad y origen de humedad)
7. `motivo_descarte` (`n/a` si aplicó; código explícito si no aplicó)

Ejemplo OFF aplicado:

```text
accion_manual_detectada=OFF
resultado_aprendizaje_efectivo=sí
peso_aplicado=1.00
cambio_aplicado=Off +0.25 | On +0.25 | Setpoint +0.0
umbral_antes_despues=Off 24.00→24.25 | On 24.50→24.75
contexto=exterior_templado:humedad_normal:franja_1001_1500:desconocido:presencia | rama=cool_normal_on | franja_auto=franja_1001_1500 | franja_actual=franja_1001_1500 | presencia_auto=presencia | presencia_actual=presencia | humedad_auto=humedad_normal | humedad_actual=humedad_normal | humedad_fuente=promedio_h1_h2
motivo_descarte=n/a
```

Ejemplo ON no aplicado (para trazabilidad en helpers/logbook, sin push obligatorio):

```text
accion_manual_detectada=ON
resultado_aprendizaje_efectivo=no
peso_aplicado=0.42
cambio_aplicado=ninguno
umbral_antes_despues=sin cambio
contexto=exterior_templado:humedad_normal:franja_1001_1500:desconocido:presencia | rama=cool_normal_on | franja_auto=franja_1001_1500 | franja_actual=franja_1801_2059 | presencia_auto=presencia | presencia_actual=sin_presencia | humedad_auto=humedad_normal | humedad_actual=humedad_alta | humedad_fuente=promedio_h1_h2
motivo_descarte=antirebote
```

### Cuándo se emite

- **Push estructurado:** sólo cuando `applied_with_real_changes` (hay aprendizaje efectivo con cambios reales).
- **Estado de resultado en helper:** siempre, tanto para aplicado como para evaluado sin aplicación.
