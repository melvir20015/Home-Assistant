# Documentación operativa

- [`ac-aprendido-contexto.md`](./ac-aprendido-contexto.md): contexto físico, criterios de aprendizaje y principios que deben respetarse al modificar la automatización del AC.
- [`ac-produccion-manual-auto.md`](./ac-produccion-manual-auto.md): contrato operativo en producción, incluyendo la reconciliación runtime/UI del helper `input_select.ac_ultimo_modo_no_fan` para impedir el valor legacy inválido `False`.
- [`ac-validacion-funcional-2026-03-20.md`](./ac-validacion-funcional-2026-03-20.md): validación funcional reproducible de los escenarios críticos del AC aprendido, con hallazgos, límites y siguiente paso para cerrar la brecha runtime.
- [`ha-traces-retencion.md`](./ha-traces-retencion.md): regla operativa para retención de traces y validación para evitar reintroducir `trace/stored_traces` en niveles no soportados.
