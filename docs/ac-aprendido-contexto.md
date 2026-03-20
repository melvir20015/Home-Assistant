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
- `input_boolean.ac_off_por_automatizacion`: debe encenderse inmediatamente antes de cada `AUTO OFF`, mantenerse durante toda la secuencia y limpiarse sólo al final con una demora breve para que un cambio provocado por la automatización no dispare `Manual OFF` ni `Learning - Manual OFF feedback`.
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

Semántica funcional vigente del helper:

- `off` significa **reposo explícito del helper**: no hay un modo térmico recordado que convenga conservar. No es un sinónimo de `idle`; `idle` no debe usarse como valor de este helper.
- Nunca deben persistirse booleanos como `False` o `false` en `input_select.ac_ultimo_modo_no_fan`. Si aparece un valor legacy de ese tipo tras una restauración de estado, debe normalizarse inmediatamente a `off` antes de que cualquier automatización compare o escriba el helper.
- `cool` debe guardarse cuando una automatización o una intervención manual deja al AC operando efectivamente en enfriamiento y ese enfriamiento sí debe quedar como último modo térmico útil.
- `heat` debe guardarse cuando una automatización o una intervención manual deja al AC operando efectivamente en calefacción y esa calefacción sí debe quedar como último modo térmico útil.
- `emergency_cool` debe guardarse únicamente cuando entra en acción la rama de enfriamiento de emergencia por calor severo y se necesita distinguir ese contexto del flujo normal de `cool`.
- El helper debe resetearse a `off` cuando el sistema entra en reposo y ya no conviene conservar memoria operativa, por ejemplo tras apagados manuales, auto-off por ausencia, limpiezas de latch de emergencia o cualquier otra rama que explícitamente descarte el modo recordado.

## 6. Principios de diseño que no deben romperse

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
