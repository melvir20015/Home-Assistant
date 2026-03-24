# Contexto operativo del aprendizaje del AC

## 1. Descripción física del entorno

El sistema de climatización que se quiere automatizar opera en un apartamento de una recámara. El aire acondicionado es un AC de ventana instalado en la recámara, pero el confort térmico real no depende únicamente de ese punto físico, porque la sala y la cocina están conectadas y forman parte del mismo volumen habitable.

### Distribución relevante

- **Recámara:** contiene el AC de ventana y un sensor de temperatura/humedad.
- **Sala:** contiene un segundo sensor de temperatura/humedad y además un sensor de movimiento.
- **Cocina conectada:** comparte la dinámica térmica general con la sala y la recámara, aunque no tenga un sensor dedicado descrito aquí.

### Implicación de diseño

El confort percibido por el usuario no debe modelarse como si todo el apartamento fuera equivalente al punto donde está instalado el AC. El aire se enfría o calienta primero en la recámara, pero el usuario vive el confort como una combinación de:

- la temperatura y humedad de la recámara;
- la temperatura y humedad de la sala;
- la diferencia entre ambos espacios;
- la presencia real detectada en la sala y el uso efectivo del apartamento.

Por eso, cualquier lógica de aprendizaje y decisión debe asumir que el confort térmico relevante surge del conjunto **recámara + sala**, y no solamente del sensor más cercano al equipo.

## 2. Objetivo general de la automatización

La automatización del AC debe perseguir un objetivo práctico de confort, no únicamente el cumplimiento rígido de umbrales aislados.

### Objetivos principales

- Encender y apagar el AC considerando, como mínimo, **temperatura interior**, **humedad**, **temperatura exterior**, **presencia** y **horario**.
- Tener en cuenta que la decisión correcta puede depender de la combinación de sensores interiores y del contexto ambiental exterior, no de una sola lectura.
- Aprender de las acciones manuales del usuario para refinar decisiones futuras.
- Ajustar con el tiempo la agresividad de encendido, apagado y setpoints según el feedback real observado.

### Intención funcional

El sistema no debe entenderse como una fórmula fija. La meta real es aproximarse al **confort percibido por el usuario**. En consecuencia:

- una automatización puede ser “correcta” técnicamente y aun así resultar incómoda;
- una acción manual del usuario puede contener información más valiosa que un umbral duro;
- el aprendizaje debe orientar la lógica hacia la experiencia real del usuario, no sólo hacia una regla abstracta.


## 3.1. Referencias complementarias del proyecto

Para evitar que este documento concentre todo el contrato operativo, conviene enlazar también la documentación complementaria ya existente del proyecto para automatizaciones del AC:

- [`ac-produccion-manual-auto.md`](./ac-produccion-manual-auto.md): contrato operativo en producción para distinguir eventos manuales vs automáticos, presencia temporal y telemetría mínima.
- [`ac-manual-off-learning-contract.md`](./ac-manual-off-learning-contract.md): reglas específicas del aprendizaje por `manual_off` tras `AUTO ON`.
- [`ac-cool-off-transaccional.md`](./ac-cool-off-transaccional.md): secuencia transaccional esperada para `cool_off` y emisión de `Cool↓`.
- [`ac-validacion-funcional-2026-03-20.md`](./ac-validacion-funcional-2026-03-20.md): validación funcional reproducible de escenarios críticos.
- [`ac-produccion-manual-auto.md`](./ac-produccion-manual-auto.md#presencia-temporal-por-encendido-manual): referencia operativa para la presencia temporal disparada por `manual_on`.

Estas referencias no sustituyen este documento: lo complementan. `ac-aprendido-contexto.md` debe seguir siendo la explicación de alto nivel del modelo mental, mientras que los otros documentos detallan contratos concretos o validaciones reproducibles.

## 3. Interpretación esperada de acciones manuales

Las acciones manuales son señales de retroalimentación. Deben interpretarse sólo cuando exista suficiente contexto para distinguirlas de eventos automáticos o ambiguos. En particular, un **apagado manual** debe tratarse como **feedback de confort** del usuario: indica que la automatización probablemente sostuvo el equipo más tiempo del deseado, o que la decisión automática previa ya no coincide con el confort percibido.

Tras detectar ese apagado manual, el sistema debe **aprender de ese feedback** mediante la telemetría y la lógica de aprendizaje correspondientes, pero la protección operativa inmediata debe ser mínima: **únicamente una pausa anti-rebote de 5 minutos** basada en `input_datetime.ac_last_manual_off_ts` dentro de la automatización principal `AC - Día dinámico aprendido (principal)`. No debe reintroducirse una pausa larga separada de 1 hora salvo que el diseño funcional cambie explícitamente y la documentación se actualice al mismo tiempo.

### Cuando el AC está en `cool`

- Si el AC estaba en `cool` y el usuario lo **apaga manualmente** por un medio distinto a una rama automática, se debe interpretar como una señal probable de que **ya había demasiado frío**, de que el apagado automático debió ocurrir antes o de que la automatización fue demasiado agresiva.
- Cuando ese apagado manual califica como feedback válido después de un `AUTO ON` en `cool`, debe considerarse una **señal fuerte de “encender más tarde”**: `input_number.ac_bias_cool_on` y `input_number.ac_bias_cool_off` deben subir **`+0.25` fijos por evento** y no quedar atados a las tasas generales `ac_learning_rate_small` o `ac_learning_rate_large`.
- Si el usuario **enciende manualmente** el AC después de un **apagado automático**, se debe interpretar como una señal probable de que el sistema **apagó demasiado pronto**, perdió el confort deseado o no sostuvo suficientemente las condiciones que el usuario esperaba.

### Cuando el AC está en `heat`

La intención conceptual debe ser simétrica para `heat`:

- un apagado manual tras operar en `heat` sugiere que probablemente ya había demasiado calor o que la lógica calentó más de lo necesario;
- un encendido manual posterior a un apagado automático sugiere que el sistema dejó enfriar demasiado el ambiente o dejó de sostener el confort esperado.

La calibración concreta de cuánto ajustar en `heat` puede diferir de `cool`, pero la interpretación de alto nivel debe conservarse: **las acciones manuales expresan correcciones del usuario sobre el confort percibido**.

## 4. Datos que deben registrarse al aprender

Cuando el sistema detecte una señal manual que sí sea válida para aprendizaje, debe registrar suficiente contexto para que la interpretación futura no dependa de memoria implícita ni de una sola variable.

### Datos mínimos a persistir

- Hora y fecha del evento.
- Temperatura interior del sensor de recámara.
- Temperatura interior del sensor de sala.
- Promedio interior entre ambos sensores.
- Humedad del sensor de recámara.
- Humedad del sensor de sala.
- Promedio de humedad interior.
- Temperatura exterior aparente.
- Velocidad del viento, si el modelo o la lógica la usa en esa decisión.
- Modo del AC en el momento relevante.
- Setpoint vigente.
- `fan mode` vigente.
- Diferencia entre sensores interiores.
- Tipo de evento manual detectado.
- Relación entre el evento manual y la última acción automática conocida.

### Criterio de calidad del registro

Registrar estos datos permite distinguir, por ejemplo, entre:

- una queja por exceso de frío en recámara con sala todavía templada;
- un apagado manual porque ya todo el apartamento estaba confortable;
- un reencendido manual porque la automatización apagó pronto;
- una acción manual que en realidad no aporta aprendizaje claro.

Sin este contexto, cualquier ajuste futuro corre el riesgo de sobrecorregir o aprender una conclusión equivocada.

## 5. Relación con helpers clave

Los helpers existentes forman la memoria operativa mínima del sistema. Este documento define el propósito conceptual que futuras automatizaciones deben respetar.

### `input_boolean.ac_off_por_automatizacion`

Este helper funciona como **bandera explícita** para indicar que un apagado reciente fue provocado por la lógica automática y no por el usuario. Su papel principal es evitar que el sistema confunda un apagado automático con una señal manual de descontento térmico.

Debe usarse para responder preguntas como:

- “¿El estado `off` actual proviene de una decisión automática?”
- “¿Un encendido manual posterior debe interpretarse como feedback contra un apagado automático?”


### `input_boolean.ac_on_por_automatizacion` y `input_boolean.ac_off_por_automatizacion`

Estas banderas separan el **origen operativo** de los cambios del AC durante una ventana anti-rebote corta.

- `input_boolean.ac_on_por_automatizacion`: debe encenderse inmediatamente antes de cada `AUTO ON`, mantenerse durante toda la secuencia y limpiarse sólo al final con una demora breve para que un cambio provocado por la automatización no dispare `Manual ON` ni `Learning - Manual ON feedback`.
- `input_boolean.ac_off_por_automatizacion`: debe encenderse inmediatamente antes de cada `AUTO OFF`, mantenerse durante toda la secuencia y limpiarse sólo al final con una demora breve para que un cambio provocado por la automatización no dispare `Manual OFF` ni `Learning - Manual OFF feedback`. En las ramas `COOL` que pasan por `fan_only`, la notificación `Cool↓` debe emitirse dentro de la misma transacción que hace `fan_only -> off`, idealmente después de confirmar `hvac_mode: off` con una espera corta y determinística. Así se evita depender de una automatización separada que observe cambios de estado y se eliminan falsos positivos o pérdidas por desincronización.
- Si un usuario enciende o apaga desde el botón físico del AC, control IR, app propia del AC o desde la UI manual de Home Assistant **sin pasar por una automatización**, ese evento sigue siendo manual.
- Si Home Assistant ejecuta el cambio desde una automatización, aunque el cambio termine reflejándose en la misma entidad `climate`, el evento debe clasificarse como automático y nunca debe contaminar aprendizaje manual.

### Helpers `input_text.ac_last_auto_*`, `input_number.ac_last_auto_*`, `input_datetime.ac_last_auto_ts`

Estos helpers guardan el **contexto de la última acción automática relevante**. Su objetivo es preservar una fotografía operativa del momento en que la automatización actuó.

Deben representar, como mínimo:

- qué rama automática actuó;
- qué acción ejecutó;
- qué modo y `fan mode` quedaron establecidos;
- en qué instante ocurrió;
- cuáles eran las temperaturas interiores, la humedad, la temperatura exterior, el setpoint y la diferencia entre sensores.

Su utilidad principal es permitir que un evento manual posterior pueda compararse contra una acción automática específica y reciente, en vez de ser interpretado de forma aislada.

### Helpers `input_datetime.ac_last_manual_*`, `input_text.ac_last_manual_*`, `input_number.ac_last_manual_*`

Estos helpers deben almacenar la **traza estructurada de los eventos manuales** reconocidos por el sistema, separando con claridad cada momento semántico.

Contrato recomendado:

- `input_datetime.ac_last_manual_off_ts`: instante de **detección de apagado manual** y referencia para la **única pausa breve anti-rebote de 5 minutos** que bloquea un `auto_on` inmediato dentro de `AC - Día dinámico aprendido (principal)`. No sustituye ni representa una pausa larga independiente.
- `input_datetime.ac_last_manual_on_ts`: instante de **detección de encendido manual**.
- `input_datetime.ac_last_manual_feedback_ts`: instante del último **feedback manual válido para aprendizaje**; no debe usarse para detección inicial ni para estado final.
- `input_datetime.ac_last_manual_final_ts`: instante en que quedó consolidado el **estado final manual elegido por el usuario**.
- `input_text.ac_last_manual_event_type`: detalle semántico del evento manual detectado (`manual_off_detected`, `manual_on_due_to_presence_gap`, etc.). No debe reutilizarse como clasificación simple del origen.
- `input_text.ac_last_manual_learning_type`: resultado semántico del análisis de aprendizaje manual (`*_feedback_valid_*`, `*_feedback_ignored_*`, etc.).
- `input_text.ac_last_manual_final_mode` y `input_text.ac_last_manual_final_fan`: modo y ventilación finales elegidos por el usuario tras estabilizarse el equipo.
- `input_text.ac_last_manual_feedback_mode` y `input_text.ac_last_manual_feedback_fan`: modo y ventilación que efectivamente sirvieron como evidencia de aprendizaje cuando hubo feedback válido.

Su función incluye:

- registrar cuándo ocurrió cada momento manual relevante;
- distinguir entre detección manual, aprendizaje válido y estado final manual;
- guardar modo, `fan mode`, setpoint y snapshot ambiental asociado;
- permitir auditoría y recalibración posterior;
- evitar ambigüedad para otra IA o para un humano que inspeccione la telemetría.

En términos prácticos, son la base para aprender del usuario sin depender exclusivamente del historial crudo de estados del clima.

### `input_boolean.ac_learning_enabled`

Este helper es el **interruptor maestro del aprendizaje**. Mientras permanezca en `on`, los eventos manuales válidos pueden traducirse en ajustes sobre `ac_bias_cool_*` y `ac_bias_heat_*`.

Criterio operativo recomendado:

- en producción, si se espera que los apagados o encendidos manuales del usuario **sí ajusten sesgos**, este helper debe permanecer en `on`;
- si está en `off`, la automatización todavía puede clasificar el evento como ignorado, pero **bloquea cualquier ajuste de sesgos**;
- antes de concluir que “no está aprendiendo”, debe revisarse explícitamente este helper.

### `input_boolean.ac_learning_debug`

Este helper controla la **telemetría visible del aprendizaje**: notificaciones, mensajes de depuración y evidencia operativa para validar por qué un feedback sí o no produjo cambios.

Criterio operativo recomendado:

- en producción debe limitarse a telemetría de depuración y nunca habilitar notificaciones de aprendizaje ignorado;
- si está en `off`, se oculta la telemetría de depuración, pero las notificaciones breves de aprendizaje válido siguen siendo las únicas visibles;
- antes de concluir que “no está aprendiendo”, también debe revisarse este helper, porque una ausencia de mensajes de depuración no implica por sí sola ausencia de evaluación o de aprendizaje.


### Notificaciones de producción

Contrato operativo de notificaciones:

- Sólo deben notificarse aprendizajes **válidos**.
- No deben notificarse eventos ignorados, ambiguos, expirados o con `ac_learning_enabled` apagado.
- Las detecciones crudas de `Manual ON` y `Manual OFF` deben quedar sólo en logbook/auditoría, no como notificación normal de producción.
- El formato visible debe ser corto y consistente, por ejemplo: `AC aprendió: OFF manual tras AUTO COOL | +0.25 on/off | +0.5 setpoint | 7.5 min`.
- Los únicos push normales de producción deben limitarse a:
  - `AC AUTO ON: ...`
  - `AC AUTO OFF: ...`
  - `AC aprendió: ...`
  - `AC aprendió: ON manual por ausencia | presencia temporal activada`
- La telemetría detallada, los abortos, los ignorados y las limpiezas defensivas deben permanecer en logbook/helpers y no en notificación push masiva.

### Sesgos `ac_bias_cool_*` y `ac_bias_heat_*`

Estos helpers representan el **aprendizaje acumulado** que modifica la decisión base del sistema.

Conceptualmente:

- `ac_bias_cool_on` y `ac_bias_heat_on` ajustan qué tan pronto o qué tan tarde conviene encender;
- `ac_bias_cool_off` y `ac_bias_heat_off` ajustan qué tan pronto o qué tan tarde conviene apagar;
- `ac_bias_cool_setpoint` y `ac_bias_heat_setpoint` ajustan el setpoint preferido cuando existe evidencia consistente.

Para evitar sobrecorrecciones, los sesgos deben permanecer saturados dentro de sus topes operativos. En particular, `ac_bias_cool_on` y `ac_bias_cool_off` deben seguir acotados a `+3.00` como máximo, incluso cuando acumulen varios apagados manuales válidos consecutivos en `cool`.

No deben verse como valores arbitrarios, sino como la memoria resumida de un patrón de feedback manual repetido.

### `input_select.ac_ultimo_modo_no_fan`

Este helper cumple el papel de **memoria operativa del último modo térmico significativo** distinto de un estado puramente de ventilación.

Debe preservar cuál fue el último modo útil para confort (`cool`, `heat`, u otro modo térmicamente relevante definido por la lógica) para que el sistema pueda:

- reanudar contexto después de transiciones a `off` o a estados auxiliares;
- interpretar correctamente eventos manuales posteriores;
- distinguir entre “último modo térmico del usuario” y un estado transitorio que no expresa intención térmica.

En otras palabras, ayuda a mantener continuidad semántica entre acciones automáticas, acciones manuales y decisiones de aprendizaje.

Opciones válidas exactas del helper (siempre como texto, nunca como booleanos):

- `off`
- `cool`
- `heat`
- `emergency_cool`

Semántica funcional vigente del helper:

- `off` significa **reposo explícito del helper**: no hay un modo térmico recordado que convenga conservar. No es un sinónimo de `idle`; `idle` no debe usarse como valor de este helper.
- Nunca deben persistirse booleanos como `False` o `false` en `input_select.ac_ultimo_modo_no_fan`. Si aparece un valor legacy de ese tipo tras una restauración de estado, debe normalizarse inmediatamente a `off` antes de que cualquier automatización compare o escriba el helper.
- `cool` debe guardarse cuando una automatización o una intervención manual deja al AC operando efectivamente en enfriamiento y ese enfriamiento sí debe quedar como último modo térmico útil.
- `heat` debe guardarse cuando una automatización o una intervención manual deja al AC operando efectivamente en calefacción y esa calefacción sí debe quedar como último modo térmico útil.
- `emergency_cool` debe guardarse únicamente cuando entra en acción la rama de enfriamiento de emergencia por calor severo y se necesita distinguir ese contexto del flujo normal de `cool`.
- El helper debe resetearse a `off` cuando el sistema entra en reposo y ya no conviene conservar memoria operativa, por ejemplo tras apagados manuales, auto-off por ausencia, limpiezas de latch de emergencia o cualquier otra rama que explícitamente descarte el modo recordado.

Regla operativa que no debe romperse:

- `off` es el único estado de reposo permitido para este helper y debe observarse exactamente como texto en `states('input_select.ac_ultimo_modo_no_fan')`.
- No debe existir ninguna opción booleana como `False`/`false` ni ningún flujo que intente escribirla.
- Si en la UI/estado runtime reaparece una opción legacy como `False`, primero hay que confirmar que el selector acepta `off` y que en **Helpers** sólo se ven `off`, `cool`, `heat`, `emergency_cool`; después debe corregirse la definición cargada del helper (recarga de `input_select`, reinicio y, si aún persiste, recreación/reparación de la persistencia runtime) antes de volver a confiar en la automatización de normalización.
- Después de `cool_normal_off`, `cool_emergency_off` y de cualquier limpieza de latch de emergencia, el helper debe quedar en `off`.
- Tras corregir el runtime del helper, la validación mínima exigible es repetir un ciclo `COOL` completo y comprobar que la rama ya no rompe en `input_select.select_option`, que la ejecución no termina en `error` y que la notificación final se emite después del apagado.

Prioridad operativa correcta dentro del `choose` principal de `AC - Día dinámico aprendido (principal)`:

1. **Apagados**: primero deben evaluarse `cool_emergency_off`, `cool_normal_off`, `heat_normal_off` y cualquier otra rama de apagado equivalente. Si el equipo ya cumple condición de apagado, debe apagarse antes de cualquier otra corrección fina.
2. **Encendidos**: después se evalúan los `auto_on` normales o de emergencia cuando el sistema todavía decidió permanecer apagado y corresponde arrancar.
3. **Ajustes finos de operación**: sólo al final deben ejecutarse correcciones no terminales, como ajuste de `setpoint` o `fan`, y únicamente cuando el sistema ya decidió permanecer encendido.

Caso de validación que no debe romperse:

- Si `cur_mode = cool`, `emergency_latched = false`, `tin <= cool_off` **o** algún sensor relevante está en `<= cool_sensor_off`, y además `ac_set != cool_setpoint`, la rama que debe ganar es `cool_normal_off`.
- En ese escenario no debe ejecutarse la corrección fina de `setpoint`, porque el sistema ya decidió apagar el AC.

### Contrato operativo latcheado del ciclo `cool`

Desde el momento en que entra `cool_normal_on`, la automatización debe **latchear** y persistir el contrato operativo completo del ciclo en helpers dedicados:

- `cool_on` real del ciclo;
- `cool_off` real del ciclo;
- `cool_sensor_off` real del ciclo;
- `cool_setpoint` teórico comprometido para ese arranque;
- `cool_setpoint_effective` realmente aplicado al equipo;
- bucket contextual del ciclo;
- motivo del cálculo: `base_contextual` o `aprendizaje`.

Ese snapshot persistente pasa a ser la referencia canónica del ciclo activo para tres usos obligatorios:

1. **Notificación de encendido**: lo mostrado al arrancar debe reflejar los valores efectivamente comprometidos para ese ciclo, no una re-evaluación posterior del contexto.
2. **Apagado normal del mismo ciclo**: `cool_normal_off` debe comparar primero contra el `cool_off` latcheado del ciclo, no contra un `cool_off` recalculado en vivo.
3. **Auditoría posterior**: logbook/helpers deben permitir reconstruir exactamente con qué contrato arrancó el ciclo y por qué.

Reglas adicionales que no deben romperse:

- el par `cool_on` / `cool_off` mostrado al encender es el **contrato operativo del ciclo**;
- la histéresis entre ambos se mantiene en **0.5 °C**;
- si el apagado ocurre porque `t1` o `t2` cae por debajo de `cool_sensor_off`, la causa debe quedar registrada como **corte preventivo** separado y no como `meta_alcanzada`.

### Campos visibles en la notificación `Cool↑` del encendido normal

Cuando `cool_normal_on` ya guardó el snapshot contractual del ciclo, la notificación `Cool↑` debe construirse **exclusivamente** leyendo esos helpers persistidos y no recalculando valores en vivo dentro del mismo mensaje.

Campos visibles y significado exacto:

- `Encendido en`: valor de `input_number.ac_cool_cycle_contract_on`. Es la temperatura promedio (`tin`) comprometida para habilitar el encendido de ese ciclo. Corresponde al `cool_on` latcheado, no a una re-evaluación posterior.
- `Apagado en`: valor de `input_number.ac_cool_cycle_contract_off`. Es la temperatura promedio contractual que autoriza el apagado normal por meta alcanzada durante ese mismo ciclo.
- `Corte preventivo sensor`: valor de `input_number.ac_cool_cycle_contract_sensor_off`. Es el umbral protector aplicado a sensores puntuales (`t1`/`t2`); si uno de ellos baja hasta ese valor, el ciclo puede cortarse preventivamente aunque el promedio aún no haya llegado a `Apagado en`.
- `Setpoint teórico`: valor de `input_number.ac_cool_cycle_contract_setpoint`. Es el setpoint calculado y comprometido por la lógica para ese arranque antes de considerar la resolución o normalización final exigida por el equipo.
- `Setpoint efectivo`: valor de `input_number.ac_cool_cycle_contract_setpoint_effective`. Es el setpoint finalmente enviado al equipo para ese ciclo después de aplicar la normalización operativa correspondiente.

Interpretación funcional obligatoria:

- `Apagado en` y `Corte preventivo sensor` son condiciones de salida del ciclo y **no** deben confundirse con el setpoint del equipo.
- `Setpoint teórico` y `Setpoint efectivo` describen la consigna de operación del AC y **no** sustituyen el umbral contractual de apagado.
- Si cambia el contexto exterior después del arranque, la notificación histórica debe seguir reflejando el snapshot persistido del ciclo original.

## 6. Clasificación operativa de origen y protección tras intervención manual

### Origen canónico del último cambio

`input_text.ac_last_change_origin` debe guardar siempre una clasificación simple y estable del origen del último cambio:

- `auto_on`
- `auto_off`
- `manual_on`
- `manual_off`

Ese helper no sustituye a `input_text.ac_last_manual_event_type`; ambos deben coexistir:

- `ac_last_change_origin` responde **quién originó el cambio**;
- `ac_last_manual_event_type` responde **cómo debe interpretarse semánticamente** ese evento manual.

### Qué cuenta como evento manual

Debe tratarse como manual cualquier cambio real del `climate` que no ocurra mientras una bandera automática correspondiente siga activa:

- botón físico del AC;
- control IR;
- app nativa del AC;
- cambio manual desde la interfaz de Home Assistant.

Si el cambio fue emitido desde una automatización propia del sistema y la bandera automática seguía activa en ese instante, el evento **no** debe entrar en los flujos manuales ni de aprendizaje.

### Ventana de estabilización tras `manual_on`

Después de detectar un `manual_on`, la automatización principal debe respetar una ventana corta de estabilización/manual override basada en `input_datetime.ac_last_manual_on_ts` e `input_datetime.ac_last_manual_final_ts`.

Durante esa ventana:

- no debe cambiar inmediatamente el `hvac_mode`;
- no debe corregir `fan_mode`;
- no debe apagar el AC por ramas automáticas de `presence_off`, `cool_normal_off`, `cool_emergency_off`, `heat_normal_off` o equivalentes.

La finalidad es permitir que el equipo termine de estabilizar el estado elegido manualmente antes de que la lógica principal vuelva a intervenir.

### Semántica de presencia: teléfono, presencia real y memoria operativa

La lógica del AC debe separar explícitamente tres conceptos:

- **`presence_phone_home` / presencia del teléfono en casa**: `true` cuando `person.ivan == home` **o** `device_tracker.samsung_s24` reporta `home/on`. Esta señal **sí puede** habilitar `AUTO ON`.
- **`presence_real_now` / presencia real ahora**: `true` sólo cuando el movimiento estable está activo y además `presence_ok` valida ese sensor. En código esto equivale al gate estricto `presence_sensor_strict = presence_ok and presence_real_now`. Esta señal **sí puede** habilitar `AUTO ON`.
- **`presence_effective` / presencia efectiva histórica**: memoria operativa que agrega `presence_phone_home`, `presence_sensor_strict` y la excepción temporal `presence_temp_from_manual`. Sirve para contexto, buckets y para no apagar/rebloquear inmediatamente después de un `manual_on`, pero **no debe autorizar por sí sola un `AUTO ON`**.

Regla obligatoria para el encendido automático:

- si `person.ivan != home` **y** `device_tracker.samsung_s24` no está en `home/on`, el `AUTO ON` queda bloqueado salvo que exista `presence_sensor_strict`;
- aunque `presence_effective` siga en `true` por memoria operativa, si `presence_real_now == false` y no hay presencia telefónica válida, el `AUTO ON` debe permanecer bloqueado.

### Presencia temporal por encendido manual durante ausencia

Si no existe presencia estricta para `AUTO ON` y el usuario enciende manualmente el AC, el sistema debe interpretarlo como señal válida de presencia real o brecha de confort.

Contrato:

- clasificar el evento como `manual_on_due_to_presence_gap`, `manual_on_due_to_presence_gap_cool` o `manual_on_due_to_presence_gap_heat`, según el modo final, usando la semántica estricta (`presence_phone_home` o `presence_sensor_strict`) y **no** una `presence_effective` rezagada;
- extender `input_datetime.ac_manual_presence_until` con una presencia temporal coherente;
- usar esa presencia temporal sólo como memoria operativa para evitar apagar o rebloquear inmediatamente tras el encendido manual;
- no reutilizar esa presencia temporal para habilitar `AUTO ON` cuando ya no hay presencia real actual ni presencia telefónica válida;
- permitir que el aprendizaje posterior siga funcionando normalmente.

## 7. Emergency cool: dominancia y límites

`emergency_cool` existe para calor realmente severo, no como reemplazo permanente del flujo normal de `cool`.

Principios:

- `emergency_on_avg` debe ser claramente más exigente que `cool_on`;
- `emergency_off_avg` debe liberar antes el latch sólo cuando ya se alivió el calor fuerte;
- `emergency_latched` sirve para mantener continuidad semántica de la emergencia, pero debe limpiarse cuando el equipo ya está en `off` y el contexto extremo desapareció;
- un `manual_on` reciente no debe quedar inmediatamente pisado por una secuencia de `emergency_cool` que lo mande a `fan_only` u `off` sin dar tiempo a estabilizar la intervención del usuario.

## 8. Helpers críticos que deben existir también en runtime

Además de estar definidos en el repositorio, en runtime deben existir al menos estos helpers de telemetría:

- `ac_last_auto_branch`
- `ac_last_auto_action`
- `ac_last_auto_mode`
- `ac_last_auto_fan`
- `ac_last_manual_event_type`
- `ac_last_manual_learning_type`
- `ac_last_manual_feedback_mode`
- `ac_last_change_origin`

Si uno falta en runtime, la causa más probable no es la lógica del AC sino un problema de carga parcial del paquete/configuración de Home Assistant. Desde el repositorio puede verificarse que los helpers están declarados; la comprobación contra la instancia viva requiere revisar **Estados / Helpers** o el arranque real de HA.

## 9. Principios de diseño que no deben romperse

Cualquier modificación futura debe preservar estos principios:

1. **No confundir acciones automáticas con acciones manuales.** Si el origen del cambio no está claro, no debe inferirse aprendizaje fuerte.
2. **No aprender de eventos ambiguos.** Un evento sin contexto suficiente o sin relación clara con la última acción automática debe considerarse no confiable.
3. **No depender de un único sensor para representar todo el apartamento.** El modelo de confort debe considerar al menos recámara y sala, así como su diferencia.
4. **Priorizar el confort percibido del usuario por encima de umbrales rígidos cuando exista feedback manual consistente.**
5. **Mantener trazabilidad.** Cada ajuste aprendido debería poder explicarse en función de un evento manual y su contexto.
6. **Evitar sobreajustes por una sola observación.** El aprendizaje debe ser gradual, especialmente cuando las condiciones exteriores cambian.

## 7. Supuestos importantes para futuras modificaciones

Antes de cambiar la lógica, debe asumirse que estos supuestos siguen siendo válidos salvo evidencia explícita en contrario:

- El AC está físicamente en la recámara, pero el confort objetivo es del apartamento habitable y no sólo del punto de instalación.
- La sala aporta información crítica porque refleja ocupación y equilibrio térmico fuera de la recámara.
- Un apagado manual en `cool` o `heat` suele indicar exceso respecto al confort esperado, salvo que el contexto demuestre otra cosa; por diseño vigente debe interpretarse como **feedback de confort** y no como disparador de una pausa larga separada.
- Tras ese apagado manual, la única contención operativa inmediata debe ser el bloqueo anti-rebote de **5 minutos** basado en `input_datetime.ac_last_manual_off_ts` dentro de la automatización principal.
- Un encendido manual tras apagado automático suele indicar que el sistema se quedó corto para sostener confort.
- La diferencia entre sensores interiores importa; no es un dato accesorio.
- Los helpers de última acción automática y último evento manual son parte del contrato operativo del sistema.
- Si no puede distinguirse con suficiente confianza entre evento manual y automático, es mejor no aprender.

## 8. Preguntas de validación antes de cambiar la lógica

Toda IA o programador que modifique esta automatización debería responder, como mínimo, estas preguntas:

- ¿La nueva lógica sigue diferenciando de forma confiable entre acciones automáticas y manuales?
- ¿La propuesta usa información de recámara y sala, o volvió a depender implícitamente de un solo sensor?
- ¿El cambio conserva la relación entre un evento manual y la última acción automática relevante?
- ¿Se siguen registrando fecha, contexto ambiental, modo, setpoint, `fan mode` y diferencia entre sensores?
- ¿El cambio evita aprender de eventos ambiguos o demasiado lejanos en el tiempo?
- ¿La modificación mejora el confort percibido o sólo endurece umbrales?
- ¿Los sesgos de `cool` y `heat` siguen representando aprendizaje acumulado y no parches aislados?
- ¿`input_select.ac_ultimo_modo_no_fan` continúa funcionando como memoria semántica del último modo térmico útil?

## 9. Uso recomendado de este documento

Este archivo debe tomarse como referencia operativa cuando se modifiquen:

- automatizaciones de encendido y apagado del AC;
- reglas de aprendizaje por feedback manual;
- helpers de memoria de contexto;
- criterios para interpretar presencia, horario o clima exterior en decisiones de confort.

Si en el futuro cambia la distribución del apartamento, la ubicación de sensores o la estrategia de aprendizaje, este documento debe actualizarse antes o junto con la lógica correspondiente.


### `input_text.ac_last_change_origin`

Este helper guarda la clasificación simple del último cambio confirmado del equipo: `auto_on`, `auto_off`, `manual_on` o `manual_off`. Debe actualizarse tanto en automatizaciones automáticas como manuales y sirve para auditoría rápida, para evitar aprendizaje ambiguo y para recordar que la UI manual de Home Assistant cuenta como manual sólo cuando el cambio no fue lanzado por otra automatización.

## 6. Contrato de persistencia para aprendizaje contextual en `cool`

Para `cool`, la persistencia del aprendizaje contextual **no debe volver a usar** `input_text` como almacén de mapas JSON largos. Home Assistant limita `input_text` a un máximo de **255 caracteres**, por lo que un diccionario serializado por bucket termina truncado o rechazado cuando el aprendizaje crece.

### Diseño vigente

- Los valores efectivos de aprendizaje contextual viven en helpers numéricos dedicados por bucket, por ejemplo `input_number.ac_cool_learning_bucket_*` y `input_number.ac_cool_effective_sp_bucket_*`.
- `input_text.ac_cool_contextual_learning_map` sólo conserva un **resumen corto del último bucket escrito**, con formato `bucket=valor`.
- `input_text.ac_cool_effective_setpoint_map` sólo conserva un **resumen corto del último setpoint efectivo persistido**, también con formato `bucket=valor`.
- El helper `input_number.ac_manual_setpoint_override_hold_minutes` define la **ventana de respeto del SP manual aprendido en el ciclo actual**; su rango operativo quedó en `45-60 min` con valor inicial `50 min`, y durante esa ventana deben quedar bloqueadas la sincronización automática, los `cool_cycle_step` y cualquier reescritura/eco del dispositivo.
- Las plantillas operativas deben leer el valor real desde el `input_number` del bucket correspondiente; los `input_text` se consideran únicamente telemetría resumida o ayuda de auditoría rápida.

### Contrato actual de buckets `cool`

La clave contextual activa de `cool` tiene ahora esta forma estable:

`<bucket_exterior>:<bucket_humedad>:<bucket_franja>:<bucket_clima>:<bucket_presencia>`

Y el detalle extendido agrega la tendencia térmica:

`<bucket_exterior>:<bucket_humedad>:<bucket_franja>:<bucket_clima>:<bucket_presencia>:<bucket_tendencia>`

#### Buckets canónicos

- **Exterior aparente (`tout`)**
  - `exterior_templado`
  - `exterior_caliente`
  - `exterior_muy_caliente`
- **Humedad interior (`hin`)**
  - `humedad_normal`
  - `humedad_alta`
  - `humedad_muy_alta`
- **Franja horaria**
  - `franja_0700_1000`
  - `franja_1001_1500`
  - `franja_1501_1800`
  - `franja_1801_2059`
  - `franja_fuera_rango`
- **Condición meteorológica descriptiva** a partir de `weather.openweathermap`
  - `soleado`
  - `parcial`
  - `nublado`
  - `lluvia`
  - `niebla`
  - `tormenta`
  - `desconocido`
- **Presencia**
  - `presencia`
  - `ausencia`
- **Tendencia térmica**
  - `subiendo`
  - `estable`
  - `bajando`

#### Normalización del clima exterior

Antes de formar la clave contextual, la automatización normaliza el estado real de `weather.openweathermap` a una categoría canónica:

- `sunny` y `clear-night` → `soleado`
- `partlycloudy`, `windy`, `windy-variant` → `parcial`
- `cloudy`, `overcast` → `nublado`
- `rainy`, `pouring`, `hail`, `snowy-rainy`, `snowy` → `lluvia`
- `fog` → `niebla`
- `lightning`, `lightning-rainy` → `tormenta`
- cualquier otro estado → `desconocido`

#### Ejemplos de claves completas

- Bucket base: `exterior_caliente:humedad_alta:franja_1001_1500:soleado:presencia`
- Bucket detallado: `exterior_caliente:humedad_alta:franja_1001_1500:soleado:presencia:subiendo`
- Helper de aprendizaje derivado: `input_number.ac_cool_learning_bucket_exterior_caliente_humedad_alta_franja_1001_1500_soleado_presencia`
- Helper de setpoint efectivo derivado: `input_number.ac_cool_effective_sp_bucket_exterior_caliente_humedad_alta_franja_1001_1500_soleado_presencia`

#### Impacto operativo del nuevo contexto

- `cool_contextual_base_off` pondera simultáneamente:
  - temperatura aparente exterior,
  - promedio interior,
  - humedad interior,
  - franja horaria,
  - condición meteorológica descriptiva,
  - tendencia térmica,
  - presencia.
- `cool_off_target` sigue derivándose del bucket contextual aprendido, pero ahora aplica un ajuste fino de demanda sin romper los límites existentes.
- `cool_on_target` sigue saliendo de `cool_off_target`, preservando la geometría del sistema, aunque el diferencial ahora también se modula por franja, clima, tendencia y presencia.
- Regla contractual de decisión para `cool`: **`SP = Off - 0.5 °C`** y luego saturado a límites operativos (`21.0 °C` a `24.0 °C`).
- La lógica interna debe usar siempre ese valor en °C como fuente única de verdad (`SP_logic_c` / `cool_setpoint_effective_c`).
- Si el equipo obliga setpoint entero en °F, ese valor de actuación debe mantenerse aparte (`SP_sent_f`) y **no** debe reingresar para recalcular la lógica.
- El aprendizaje contextual y la memoria de setpoint efectivo ya no deben asumir una clave de cuatro dimensiones; cualquier helper o resumen debe tratar la dimensión climática como obligatoria dentro de la clave base.

### Regla de evolución

Si en el futuro se necesita guardar más contexto de `cool`, se debe elegir una de estas rutas compatibles:

1. más helpers pequeños por bucket o por dimensión;
2. un resumen corto adicional en `input_text`;
3. una persistencia alternativa fuera de `input_text` si realmente se requiere una estructura amplia.

No se debe reintroducir un patrón de “mapa JSON completo en `input_text`”, aunque parezca temporal, porque rompe el contrato de tamaño y hace frágiles las plantillas que dependen de esa memoria.


## 10. Contexto específico de `cool normal`

La rama `cool normal` debe documentarse como un flujo distinto de `emergency_cool`, porque representa el escenario diario esperado de enfriamiento y concentra la mayor parte del aprendizaje contextual.

### 10.1. Las 4 franjas horarias exactas

Para `cool normal`, el contexto horario debe clasificarse siempre en una de estas **4 franjas exactas**:

- **`night`**: de **23:00:00** a **06:59:59**.
- **`morning`**: de **07:00:00** a **11:59:59**.
- **`afternoon`**: de **12:00:00** a **17:59:59**.
- **`evening`**: de **18:00:00** a **22:59:59**.

No deben introducirse ventanas “aproximadas” ni nombres alternos para el mismo bucket, porque el aprendizaje contextual depende de que las claves sean estables entre eventos automáticos y manuales.

### 10.2. Uso del estado externo descriptivo

Además del tramo horario, `cool normal` debe incluir el **estado externo descriptivo** derivado de la condición térmica exterior real. La intención es evitar que el sistema aprenda igual un `cool_on` ocurrido con calor moderado que otro ocurrido con calor muy severo.

Ese estado externo descriptivo debe ser legible y auditable, por ejemplo con etiquetas como:

- `mild_outside`
- `warm_outside`
- `hot_outside`
- `very_hot_outside`

La etiqueta exacta usada por la automatización debe persistirse siempre igual en las claves de contexto. Lo importante no es el nombre elegido, sino que sea **descriptivo, estable y común** para `cool_on`, `cool_off`, `cool_setpoint` y aprendizaje.

### 10.3. Compuerta de presencia estricta

En `cool normal` la **presencia estricta** debe actuar como compuerta dura de encendido automático: si no hay presencia efectiva válida, la rama no debe hacer `AUTO ON` aunque la condición térmica sea favorable.

Esa compuerta estricta existe para que el aprendizaje no derive en enfriar una vivienda vacía sólo porque el contexto térmico “parece” compatible con un encendido previo exitoso.

### 10.4. Diferencia entre presencia real, presencia del teléfono y presencia efectiva

Para evitar confusiones futuras, la documentación debe separar tres conceptos:

- **Presencia real**: evidencia fuerte de ocupación humana observada en el hogar, por ejemplo movimiento reciente o actividad consistente en sensores físicos.
- **Presencia del teléfono**: señal indirecta basada en el dispositivo del usuario; ayuda, pero puede fallar por batería, geolocalización o latencia.
- **Presencia efectiva**: resultado final que usa la automatización. Combina presencia real, presencia del teléfono y, cuando aplique, presencia temporal activada por `manual_on`.

La automatización de `cool normal` debe decidir con **presencia efectiva**, pero la documentación y el aprendizaje deben poder distinguir si esa presencia efectiva provenía de ocupación observada, del teléfono o de una retención temporal por acción manual del usuario.

## 11. Bucket contextual completo

El bucket contextual es la clave semántica completa con la que el sistema agrupa decisiones comparables. Debe ser suficientemente expresivo para que dos eventos del mismo bucket realmente representen un contexto parecido, y suficientemente estable para que el aprendizaje no se fragmente en cientos de combinaciones irrepetibles.

### 11.1. Componentes mínimos del bucket

Para `cool normal`, el bucket contextual completo debe incluir como mínimo:

- modo térmico principal: `cool_normal`;
- franja horaria exacta: `night`, `morning`, `afternoon` o `evening`;
- estado externo descriptivo: por ejemplo `warm_outside`, `hot_outside` o `very_hot_outside`;
- estado de presencia efectiva: por ejemplo `presence_effective_on` o `presence_effective_off`;
- si el origen de presencia efectiva fue real, teléfono o temporal manual, cuando ese detalle sea relevante para aprendizaje.

### 11.2. Ejemplos reales de claves

Ejemplos de claves narrativamente realistas y suficientemente explícitas:

- `cool_normal|night|hot_outside|presence_effective_on|presence_real`
- `cool_normal|afternoon|very_hot_outside|presence_effective_on|phone_present`
- `cool_normal|evening|warm_outside|presence_effective_on|manual_presence_hold`
- `cool_normal|morning|hot_outside|presence_effective_off`

Si el sistema usa un formato distinto —por ejemplo JSON serializado o prefijos como `ctx:`— debe mantener la misma semántica. Lo obligatorio es que la clave capture el mismo contexto operativo.

### 11.3. Uso del bucket para `cool_on`

El bucket debe permitir contestar: “¿en este contexto exacto suele convenir encender en `cool normal`?”.

Ejemplo:

- clave: `cool_normal|afternoon|very_hot_outside|presence_effective_on|presence_real`
- uso: registrar que en tardes muy calurosas, con presencia efectiva real, el sistema sí llegó a `AUTO ON` y qué umbral interior disparó el encendido.

Ese historial alimenta la calibración de `cool_on` para el mismo contexto, evitando mezclarlo con noches o con tardes sin presencia efectiva.

### 11.4. Uso del bucket para `cool_off`

El mismo bucket contextual debe permitir evaluar si, una vez encendido, el apagado automático fue oportuno o se sostuvo demasiado tiempo.

Ejemplo:

- clave: `cool_normal|night|hot_outside|presence_effective_on|manual_presence_hold`
- uso: asociar un `AUTO OFF` o un `manual_off` posterior con el contexto completo en el que el equipo estaba enfriando.

Así el sistema puede aprender que en noches con presencia temporal por `manual_on` quizá conviene sostener menos o más el enfriamiento, sin contaminar el comportamiento de una noche con presencia real confirmada.

### 11.5. Uso del bucket para `cool_setpoint`

El bucket contextual también debe servir para aprender qué setpoint resulta aceptable en ese contexto.

Ejemplo:

- clave: `cool_normal|evening|warm_outside|presence_effective_on|phone_present`
- uso: registrar que el setpoint efectivo aprendido para esa combinación termina siendo, por ejemplo, `24.0 °C`, mientras que otro bucket parecido pero con `very_hot_outside` podría converger a `23.0 °C`.

### 11.6. Uso del bucket para aprendizaje de apagado/encendido

El aprendizaje de encendido y apagado debe colgarse del mismo bucket para que el feedback manual no quede huérfano del contexto donde ocurrió.

Ejemplos:

- `manual_off` válido tras `AUTO ON` en `cool_normal|afternoon|very_hot_outside|presence_effective_on|presence_real` → retrasa futuros `cool_on` y/o adelanta `cool_off` para ese mismo bucket o para su agregación compatible.
- `manual_on` válido tras `AUTO OFF` en `cool_normal|night|hot_outside|presence_effective_on|manual_presence_hold` → indica que el sistema apagó demasiado pronto en ese contexto.

### 11.7. Uso del bucket para aprendizaje de setpoint efectivo

El bucket debe almacenar también el **setpoint efectivo aprendido**, no sólo el pedido automáticamente. Esto permite responder: “en este contexto, ¿qué temperatura final tolera realmente el usuario?”.

Ejemplo:

- `cool_normal|night|hot_outside|presence_effective_on|presence_real`
- setpoint automático inicial: `23.0 °C`
- ajuste manual estable del usuario: `24.0 °C`
- resultado aprendido: el bucket conserva `24.0 °C` como setpoint efectivo preferido para la próxima activación automática comparable.

## 12. Contrato del setpoint manual

El setpoint manual es una señal de alta calidad porque expresa una preferencia térmica explícita del usuario. Sin embargo, sólo debe aprenderse cuando quede claro que el valor final ya se estabilizó y no fue un toque accidental o transitorio.

### 12.1. Cuándo se considera aprendizaje válido

El cambio manual de setpoint se considera aprendizaje válido cuando se cumple todo esto:

- hubo un cambio manual explícito del usuario, no una corrección automática de la propia automatización;
- el AC quedó operando en un contexto aprendible, típicamente `cool normal` con bucket contextual identificable;
- el nuevo setpoint se mantuvo estable durante la ventana de retención definida para consolidar el estado final manual;
- no fue invalidado por un apagado inmediato, un cambio de modo incompatible o una nueva corrección manual contradictoria antes de cerrar la retención.

### 12.2. Cuándo se respeta inmediatamente

Cuando el usuario cambia manualmente el setpoint, ese nuevo valor debe respetarse **de inmediato**. Durante la ventana de estabilización/retención, la automatización principal no debe sobrescribirlo con el setpoint automático calculado para ese mismo contexto.

La lógica correcta es:

1. respetar el setpoint manual ahora;
2. consolidar si el cambio fue estable;
3. aprenderlo para la próxima vez si siguió siendo válido al final de la retención.

### 12.3. Cuánto dura la retención

La retención del setpoint manual debe durar **hasta que termine la misma ventana corta de estabilización del estado manual final** que protege un `manual_on` reciente. En términos operativos, esa retención se apoya en `input_datetime.ac_last_manual_on_ts` y `input_datetime.ac_last_manual_final_ts` y debe cubrir el periodo en que el usuario todavía está ajustando el AC.

La duración exacta implementada debe permanecer única y consistente en automatizaciones y helpers; este documento no debe duplicar un número distinto si la lógica ya usa una sola ventana centralizada. Lo importante del contrato es que la retención sea **inmediata, temporal y suficientemente larga para consolidar el estado final manual**, pero no tan larga como para secuestrar la automatización durante horas.

### 12.4. Cómo alimenta el siguiente encendido automático del mismo contexto

Una vez consolidado como válido, el setpoint manual debe alimentar el siguiente `AUTO ON` del **mismo bucket contextual**.

Ejemplo:

- contexto: `cool_normal|evening|warm_outside|presence_effective_on|phone_present`
- setpoint automático inicial: `23.0 °C`
- usuario lo mueve manualmente a `24.0 °C`
- el valor se mantiene hasta cerrar la retención
- próximo `AUTO ON` del mismo contexto: la automatización usa `24.0 °C` como referencia aprendida o como setpoint efectivo preferido

Ese aprendizaje no debe aplicarse ciegamente a todos los contextos; debe reutilizarse primero en el mismo bucket o en una agregación explícitamente compatible.

## 13. Política de notificaciones de producción en español

La política de notificaciones debe ser consistente, breve y completamente en español para producción.

### 13.1. Qué sí se notifica

Sí deben notificarse únicamente eventos de alto valor operativo para el usuario:

- `AC AUTO ON: ...`
- `AC AUTO OFF: ...`
- `AC aprendió: OFF manual tras AUTO COOL ...`
- `AC aprendió: ON manual por ausencia | presencia temporal activada`
- `AC aprendió setpoint: ...` cuando el cambio manual de setpoint se consolidó como aprendizaje válido y útil para el siguiente contexto comparable.

### 13.2. Qué no se notifica

No deben notificarse en producción:

- evaluaciones internas de ramas automáticas;
- abortos por guardas o compuertas;
- detecciones manuales crudas sin aprendizaje válido final;
- aprendizajes ignorados, expirados o ambiguos;
- depuración técnica de helpers, waits, retries o saneamientos defensivos.

### 13.3. Qué queda sólo en logbook

Deben quedar sólo en logbook, traces o helpers de auditoría:

- `manual_on` detectado;
- `manual_off` detectado;
- clasificación detallada en `input_text.ac_last_manual_event_type`;
- clasificación final en `input_text.ac_last_manual_learning_type` cuando no produjo push;
- limpiezas de banderas automáticas;
- retención temporal de presencia o consolidación del estado manual final;
- snapshots contextuales usados para aprendizaje.

## 14. Casos narrativos clave

### 14.1. `manual_on` porque faltó detección de presencia

Son las 19:40. El apartamento está caliente, el teléfono del usuario aparece fuera de casa y no hubo movimiento reciente en sala, así que `presence_effective` quedó en `off`. El usuario en realidad sí llegó, pero la detección de presencia no se actualizó a tiempo. Como la compuerta de presencia estricta bloqueó `cool normal`, el AC no hizo `AUTO ON`.

El usuario enciende el AC manualmente desde la app o desde Home Assistant. Ese evento debe clasificarse como `manual_on_due_to_presence_gap`, no como simple “uso manual sin contexto”. La automatización debe activar presencia temporal, respetar el estado manual inmediato y dejar trazabilidad de que el problema principal fue una **brecha de presencia**, no necesariamente un error térmico.

Resultado esperado:

- el AC se mantiene encendido porque la presencia efectiva ahora incluye la retención temporal manual;
- no se envía spam técnico;
- en producción puede notificarse algo breve como `AC aprendió: ON manual por ausencia | presencia temporal activada`;
- el caso queda documentado para futuras revisiones del modelo de presencia.

### 14.2. Cambio manual de setpoint que debe mantenerse ahora y aprenderse para la próxima vez

Son las 22:15. El sistema hace `AUTO ON` en `cool normal` con la clave `cool_normal|evening|warm_outside|presence_effective_on|phone_present` y fija `23.0 °C`. A los pocos minutos el usuario siente que enfría de más y sube manualmente el setpoint a `24.0 °C`.

La automatización no debe pisar ese `24.0 °C` durante la retención manual. Debe respetarlo inmediatamente, esperar a que el estado final manual se estabilice y, si el valor sigue siendo `24.0 °C` al cerrar la ventana, guardarlo como aprendizaje válido del bucket.

Resultado esperado:

- ahora: el AC sigue operando con `24.0 °C` porque el ajuste manual se respeta;
- después: el bucket contextual aprende que ese contexto tolera mejor `24.0 °C` que `23.0 °C`;
- próxima vez en el mismo contexto: el `AUTO ON` usa el setpoint efectivo aprendido sin exigir que el usuario vuelva a corregirlo manualmente.
