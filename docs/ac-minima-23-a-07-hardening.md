# Endurecimiento de `sensor.minima_23_a_07`

## Hallazgos

- En este repositorio versionado no existe ninguna definición literal de `sensor.minima_23_a_07` en YAML, plantillas, estadísticas, helpers `min/max` ni entidades exportadas desde UI.
- Tampoco hay consumidores directos del entity id en `automations.yaml`.
- La ausencia de definición en el árbol versionado indica que, si el sensor existe en runtime, muy probablemente fue creado desde la UI de Home Assistant o vive en un archivo no incluido en este repositorio.

## Riesgo observado

La automatización nocturna sí consumía sensores de temperatura base con `| float(0)`. Tras un reinicio o una restauración de estado, un `unknown`/`unavailable` podía convertirse silenciosamente en `0` y sesgar decisiones nocturnas:

- registrar muestras falsas en la tendencia de 19:00-21:59;
- alterar la decisión de modo a las 22:00;
- mover el selector dinámico de 23:00-07:00 con datos inválidos.

## Contrato defensivo aplicado

Se dejó explícito en `automations.yaml` que cualquier mínimo/agregado nocturno —incluyendo un futuro `sensor.minima_23_a_07` creado desde la UI— debe cumplir uno de estos contratos antes de ser consumido:

1. entregar un estado numérico real; o
2. marcarse como no disponible y hacer que el consumidor salte el cálculo.

En consecuencia, la lógica nocturna ahora:

- convierte a número con `float(none)` en lugar de `float(0)`;
- valida `sensores_validos` / `temps_validas` antes de calcular;
- omite la muestra o la decisión cuando la entrada no es numérica;
- deja trazas en logbook para facilitar diagnóstico posterior.

## Recomendación para la definición real si está en la UI

Si `sensor.minima_23_a_07` existe fuera de este repo y es un template, conviene usar un patrón como este:

```yaml
template:
  - sensor:
      - name: "Minima 23 a 07"
        unique_id: minima_23_a_07
        unit_of_measurement: "°C"
        availability: >-
          {{ states('sensor.origen') not in ['unknown','unavailable','none',''] }}
        state: >-
          {{ states('sensor.origen') | float }}
```

Si en cambio es un sensor estadístico o `min/max`, la fuente que lo alimenta debe validarse primero para no pasarle estados no numéricos.
