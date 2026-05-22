# AC-Matriz 160 — Reporte diagnóstico bajo demanda (solo lectura)

## Ubicación del botón
- Dashboard: **Mi Panel** (`lovelace/mi_panel.yaml`).
- Botón visible: **Reporte AC-Matriz 160**.
- Acción: llama `script.ac_matriz_160_reporte_diagnostico`.

## Script dedicado
- Nombre: `ac_matriz_160_reporte_diagnostico` en `scripts.yaml`.
- Naturaleza: **solo lectura + notificación push**.
- Servicios usados:
  - `notify.mobile_app_samsung_s24`.
  - `logbook.log` (traza informativa mínima, no intrusiva).

## Variables leídas
- HVAC: `climate.0200009211c7_climate`.
- Condiciones interiores:
  - `sensor.lumi_lumi_weather_cuarto_temperatura`
  - `sensor.lumi_lumi_weather_coco_temperatura`
  - `sensor.lumi_lumi_weather_cuarto_humedad`
  - `sensor.lumi_lumi_weather_coco_humedad`
- Condiciones exteriores: `weather.openweathermap` (`temperature`, `humidity`).
- Presencia/bloqueos:
  - `binary_sensor.presencia_movimiento_estable`
  - `device_tracker.samsung_s24`
  - `person.ivan`
  - `input_datetime.ac_matriz_160_manual_presence_override_until`
  - `input_datetime.ac_matriz_160_manual_off_block_until`
- Umbrales efectivos:
  - `input_number.ac_matriz_160_t_on_cool`
  - `input_number.ac_matriz_160_t_off_cool`
  - `input_number.ac_matriz_160_t_on_heat`
  - `input_number.ac_matriz_160_t_off_heat`

## Reglas de diagnóstico
- Si HVAC está `off`:
  - explica si hay bloqueo manual activo;
  - o ausencia de presencia efectiva;
  - o condición térmica no cumplida para encendido (`Tin` vs `cool_on/heat_on`).
- Si HVAC está `cool`/`heat`:
  - explica por qué continúa encendido en función de la condición de apagado correspondiente.
- Siempre incluye condición exacta de apagado (`Tin <= cool_off` en cool, `Tin >= heat_off` en heat).

## Estimación de apagado
- Solo se entrega valor numérico cuando hay base segura (actualmente: ya en condición de apagado => `0 min`).
- En el resto de casos: **“estimación no disponible”** para evitar inferencias débiles.

## Garantía explícita de solo lectura
- No se usan servicios de escritura de control térmico (`climate.turn_on/off`, `climate.set_*`).
- No se escriben helpers (`input_*`, `timer`, `toggle`, `marker`, etc.).
- No se altera ninguna automatización de control existente de AC‑Matriz 160.
