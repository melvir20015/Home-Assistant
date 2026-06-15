from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTOMATIONS = (ROOT / "automations.yaml").read_text()
NIGHT = AUTOMATIONS[AUTOMATIONS.index("id: ac_night_matrix_v1") :]
next_id = NIGHT.find("\n- id:", 1)
if next_id != -1:
    NIGHT = NIGHT[:next_id]


def night_contractual_setpoint(off_cool: float, hvac_min_sp: int = 17, hvac_max_sp: int = 23) -> int:
    """Contrato nocturno: floor(off_cool) - 1 con clamp del equipo."""
    return min(hvac_max_sp, max(hvac_min_sp, math.floor(off_cool) - 1))


def progressive_setpoint(contractual: int, due_count: int, hvac_min_sp: int = 17) -> int:
    return max(hvac_min_sp, contractual - min(3, due_count))


def confirm_setpoint(requested: int, reported_before: float | None, reports_after: list[float | None]) -> dict[str, object]:
    """Modelo pequeño del patrón transaccional usado en el YAML."""
    if reported_before == requested:
        return {
            "confirmed": True,
            "attempt": 0,
            "effective": reported_before,
            "terminal": "already_applied",
        }
    first = reports_after[0] if reports_after else None
    if first == requested:
        return {"confirmed": True, "attempt": 1, "effective": first, "terminal": "confirmed"}
    second = reports_after[1] if len(reports_after) > 1 else first
    if second == requested:
        return {"confirmed": True, "attempt": 2, "effective": second, "terminal": "confirmed_after_retry"}
    return {"confirmed": False, "attempt": 2, "effective": None, "terminal": "sp_no_confirmado"}


def reinforcement_count_after_confirmation(current: int, due: int, confirmed: bool) -> int:
    return due if confirmed else current


def should_reinforce(*, hvac_mode: str, presence: bool, tin: float, off_cool: float, elapsed_min: float, count: int) -> bool:
    due = min(3, int(elapsed_min // 30))
    return hvac_mode == "cool" and presence and tin > off_cool and due > count and count < 3


def should_turn_off_cool(*, hvac_mode: str, tin: float, off_cool: float) -> bool:
    return hvac_mode == "cool" and tin <= off_cool


def test_sp_already_applied_uses_reported_value_as_effective() -> None:
    result = confirm_setpoint(21, 21, [])
    assert result["confirmed"] is True
    assert result["effective"] == 21


def test_sp_misaligned_confirmed_on_first_attempt() -> None:
    result = confirm_setpoint(21, 22, [21])
    assert result["confirmed"] is True
    assert result["attempt"] == 1
    assert result["effective"] == 21


def test_sp_confirmed_after_retry() -> None:
    result = confirm_setpoint(21, 22, [22, 21])
    assert result["confirmed"] is True
    assert result["attempt"] == 2
    assert result["terminal"] == "confirmed_after_retry"


def test_sp_never_confirmed_has_no_effective_setpoint() -> None:
    result = confirm_setpoint(21, 22, [22, 22])
    assert result["confirmed"] is False
    assert result["effective"] is None
    assert result["terminal"] == "sp_no_confirmado"


def test_progressive_reinforcement_respects_contractual_floor_minus_one_and_minimum() -> None:
    contractual = night_contractual_setpoint(22.7, hvac_min_sp=18, hvac_max_sp=23)
    assert contractual == 21
    assert progressive_setpoint(contractual, 1, hvac_min_sp=18) == 20
    assert progressive_setpoint(contractual, 2, hvac_min_sp=18) == 19
    assert progressive_setpoint(contractual, 3, hvac_min_sp=18) == 18
    assert progressive_setpoint(contractual, 4, hvac_min_sp=18) == 18


def test_reinforcement_confirmed_advances_counter() -> None:
    result = confirm_setpoint(20, 21, [20])
    assert reinforcement_count_after_confirmation(0, 1, bool(result["confirmed"])) == 1


def test_reinforcement_not_confirmed_does_not_advance_counter() -> None:
    result = confirm_setpoint(20, 21, [21, 21])
    assert reinforcement_count_after_confirmation(0, 1, bool(result["confirmed"])) == 0


def test_cycle_terminated_when_reaching_off_cool() -> None:
    assert should_turn_off_cool(hvac_mode="cool", tin=22.7, off_cool=22.7)
    assert not should_reinforce(hvac_mode="cool", presence=True, tin=22.7, off_cool=22.7, elapsed_min=30, count=0)


def test_queued_runs_do_not_duplicate_same_reinforcement_count() -> None:
    assert should_reinforce(hvac_mode="cool", presence=True, tin=23.4, off_cool=22.7, elapsed_min=31, count=0)
    assert not should_reinforce(hvac_mode="cool", presence=True, tin=23.4, off_cool=22.7, elapsed_min=31, count=1)


def test_yaml_logs_real_reported_setpoint_and_confirmation_fields() -> None:
    for token in (
        "sp_contractual=",
        "sp_solicitado=",
        "sp_reportado_antes=",
        "sp_reportado_final=",
        "intento=",
        "confirmado=",
        "resultado_terminal={{ 'resync' if sp_confirmado else 'sp_no_confirmado' }}",
        "resultado_terminal={{ 'reinforcement' if sp_confirmado else 'sp_no_confirmado' }}",
        "SP_REPORTADO= {{ sp_reportado_equipo if sp_reportado_equipo is not none else 'none' }}°C",
    ):
        assert token in NIGHT
