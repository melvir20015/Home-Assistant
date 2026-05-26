# AC Night — Reporte diagnóstico bajo demanda (solo lectura)

## Ubicación del botón
- Dashboard: **Mi Panel** (`lovelace/mi_panel.yaml`).
- Botón sugerido: **Reporte AC Night**.
- Acción: llama `script.ac_night_reporte_diagnostico`.

## Script dedicado
- Nombre: `ac_night_reporte_diagnostico` en `scripts.yaml`.
- Naturaleza: **solo lectura + notificación push**.
- Servicios usados:
  - `notify.mobile_app_samsung_s24`.
  - `logbook.log`.

## Ventana horaria válida
- Horario operativo Night: **22:00:00 → 07:00:00**.
- El script se considera válido cuando la hora actual cumple:
  - `>= 22:00:00` **o** `<= 07:00:00`.

## Comportamiento fuera de horario
- Si se invoca fuera de la ventana nocturna:
  - no ejecuta el cálculo completo del reporte;
  - envía notificación explícita: **“Fuera de horario nocturno (válido: 22:00:00 → 07:00:00)”**;
  - registra traza con `hito=night_diagnostico_bajo_demanda_fuera_horario`;
  - finaliza el script sin evaluar diagnóstico extenso.

## Snapshot y tendencia entre consultas
- Snapshot dedicado Night: `input_text.ac_night_diag_demanda_snapshot`.
- Formato persistido: `Tin|Hin|Tout|Hout`.
- En cada ejecución válida:
  - compara lectura actual vs snapshot previo;
  - muestra tendencias con flechas (`↑`/`↓`) para Tin/Hin/Tout/Hout;
  - actualiza snapshot para la próxima consulta bajo demanda.

## Filosofía de salida (espejo diurno)
- Mismo enfoque de resumen de estado:
  - estado HVAC (`Encendido`/`Apagado`),
  - condiciones interiores/exteriores,
  - demanda térmica y comparación contra umbral efectivo.
- Mensaje compacto para uso móvil, manteniendo lectura rápida y consistente con el reporte diurno.
