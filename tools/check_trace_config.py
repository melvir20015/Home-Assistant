#!/usr/bin/env python3
"""Valida usos de `trace`/`stored_traces` en la configuración YAML del repo.

Reglas verificadas:
- No se permite un bloque global `trace:` en archivos de configuración raíz.
- `stored_traces` sólo debe aparecer dentro de un bloque `trace:` de una automatización/script.

La validación es intencionalmente conservadora y basada en indentación para no requerir
Home Assistant ni dependencias externas en este repositorio.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
YAML_FILES = sorted(
    p for p in ROOT.rglob("*.yaml") if ".git" not in p.parts
)


@dataclass
class Violation:
    path: Path
    line_no: int
    message: str


def iter_lines(path: Path):
    for idx, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        yield idx, raw, raw.strip(), len(raw) - len(raw.lstrip(" "))


violations: list[Violation] = []
found_trace = False
found_stored = False

for path in YAML_FILES:
    lines = list(iter_lines(path))
    for pos, (line_no, raw, stripped, indent) in enumerate(lines):
        if not stripped or stripped.startswith("#"):
            continue

        if stripped == "trace:" or stripped.startswith("trace: "):
            found_trace = True
            if indent == 0:
                violations.append(
                    Violation(
                        path,
                        line_no,
                        "bloque global `trace:` no soportado en esta configuración; use `trace` sólo dentro de una automatización/script.",
                    )
                )

        if stripped.startswith("stored_traces:"):
            found_stored = True
            in_trace_block = False
            for back_line_no, _, back_stripped, back_indent in reversed(lines[:pos]):
                if not back_stripped or back_stripped.startswith("#"):
                    continue
                if back_indent < indent:
                    if back_stripped == "trace:" or back_stripped.startswith("trace: "):
                        in_trace_block = True
                    break
            if not in_trace_block:
                violations.append(
                    Violation(
                        path,
                        line_no,
                        "`stored_traces` sólo es válido dentro de un bloque `trace:` por automatización/script.",
                    )
                )

if violations:
    print("Se detectaron configuraciones de trace incompatibles:\n")
    for violation in violations:
        rel = violation.path.relative_to(ROOT)
        print(f"- {rel}:{violation.line_no}: {violation.message}")
    sys.exit(1)

print("Validación OK: no hay bloques globales `trace:` ni usos inválidos de `stored_traces`.")
if not found_trace and not found_stored:
    print("Nota: el repositorio no define retención de traces; si se necesita, configúrela por automatización/script compatible con la versión activa de Home Assistant.")
