# Retención de traces en Home Assistant

## Estrategia final aplicada

Se **eliminó** el bloque global `trace:` de `configuration.yaml` para evitar ambigüedades entre versiones y mantener una configuración explícita por entidad.

A partir de este cambio, la retención se define **por automatización/script**:

- En `automations.yaml` se agregó en cada automatización versionada:

```yaml
trace:
  stored_traces: 50
```

- En `scripts.yaml` no se aplicaron cambios porque actualmente no hay scripts definidos en el repositorio (archivo vacío).

## Regla recomendada a futuro

1. No usar `trace:` a nivel global en `configuration.yaml`.
2. Configurar `trace.stored_traces` por automatización/script según criticidad.
3. Mantener `50` como valor base para automatizaciones críticas, ajustándolo sólo si hay una razón operativa documentada.

## Validación operativa en UI (pasos)

1. Ir a **Settings > System > Restart** (o recargar automatizaciones desde **Developer Tools > YAML**).
2. Ejecutar manualmente una automatización crítica varias veces.
3. Abrir la automatización y entrar a **Traces**.
4. Verificar que el historial retenido coincide con `stored_traces: 50` para esa automatización.

## Nota de validación en este entorno

En este entorno de trabajo (CLI/repositorio) sólo se pudo validar la configuración por archivos; la verificación visual en UI debe ejecutarse en tu instancia de Home Assistant.
