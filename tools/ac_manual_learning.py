from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Mode = Literal["COOL", "HEAT"]
EventType = Literal["manual_off_during_active_cycle", "manual_on_after_auto_stop"]

STEP = 0.25
MIN_BAND = 0.1


@dataclass(frozen=True)
class Thresholds:
    on: float
    off: float


def apply_manual_learning(mode: Mode, event_type: EventType, thresholds: Thresholds) -> Thresholds:
    """Aplica aprendizaje manual AC-DDA con paso fijo y sin topes.

    Conserva invariantes de banda:
    - COOL: on > off
    - HEAT: on < off
    """
    if mode not in ("COOL", "HEAT"):
        raise ValueError(f"mode inválido: {mode}")
    if event_type not in ("manual_off_during_active_cycle", "manual_on_after_auto_stop"):
        raise ValueError(f"event_type inválido: {event_type}")

    direction = {
        ("COOL", "manual_off_during_active_cycle"): +1,
        ("COOL", "manual_on_after_auto_stop"): -1,
        ("HEAT", "manual_off_during_active_cycle"): -1,
        ("HEAT", "manual_on_after_auto_stop"): +1,
    }[(mode, event_type)]

    updated = Thresholds(
        on=round(thresholds.on + direction * STEP, 2),
        off=round(thresholds.off + direction * STEP, 2),
    )

    if mode == "COOL" and updated.on <= updated.off:
        updated = Thresholds(on=round(updated.off + MIN_BAND, 2), off=updated.off)
    if mode == "HEAT" and updated.on >= updated.off:
        updated = Thresholds(on=updated.on, off=round(updated.on + MIN_BAND, 2))

    return updated


def build_telemetry(mode: Mode, event_type: EventType, before: Thresholds, after: Thresholds) -> dict:
    return {
        "mode": mode,
        "eventType": event_type,
        "thresholds_before": {"on": before.on, "off": before.off},
        "thresholds_after": {"on": after.on, "off": after.off},
        "applied_step": STEP,
    }
