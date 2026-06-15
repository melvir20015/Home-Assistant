import math


def cool_setpoint(off: float, min_sp: int = 17, max_sp: int = 23) -> int:
    off_entero = math.floor(off)
    sp_objetivo = off_entero - 1
    return max(min_sp, min(max_sp, int(sp_objetivo)))


def cool_fan(tin: float, off: float, hin: float) -> str:
    delta = tin - off
    if delta >= 2.0:
        base = "high"
    elif delta >= 1.0:
        base = "medium"
    else:
        base = "low"

    if hin >= 65:
        if base == "high":
            return "medium"
        if base == "medium":
            return "low"
    return base


def should_cool(tin: float, on: float, horario_habilitado: bool) -> bool:
    return horario_habilitado and tin >= on


def test_off_decimal_floor_and_sp_integer_contract() -> None:
    assert math.floor(23.45) == 23
    assert cool_setpoint(23.45) == 22


def test_off_and_on_integer_case() -> None:
    assert cool_setpoint(23.0) == 22
    assert should_cool(tin=24.0, on=24.0, horario_habilitado=True)


def test_fan_delta_ranges() -> None:
    assert cool_fan(tin=25.6, off=23.4, hin=50) == "high"
    assert cool_fan(tin=24.6, off=23.4, hin=50) == "medium"
    assert cool_fan(tin=23.9, off=23.4, hin=50) == "low"


def test_fan_high_humidity_drops_one_level() -> None:
    assert cool_fan(tin=25.6, off=23.4, hin=65) == "medium"
    assert cool_fan(tin=24.6, off=23.4, hin=70) == "low"
    assert cool_fan(tin=23.9, off=23.4, hin=75) == "low"


def test_out_of_schedule_skips_control() -> None:
    assert not should_cool(tin=25.0, on=24.0, horario_habilitado=False)


def cool_cycle_ts_active(started_ts: float, now_ts: float, valid_after_ts: float = 946684800) -> bool:
    return valid_after_ts <= started_ts <= now_ts


def cool_elapsed_min(started_ts: float, now_ts: float) -> float:
    if not cool_cycle_ts_active(started_ts, now_ts):
        return 0
    return round((now_ts - started_ts) / 60, 1)


def cool_aggressive_setpoint(sp_cool_normal: int, min_sp: int = 17, max_sp: int = 23) -> int:
    return max(min_sp, min(max_sp, sp_cool_normal - 1))


def should_apply_cool_aggressive(
    *,
    cool_normal_active: bool,
    started_ts: float,
    now_ts: float,
    already_applied: bool,
    tin: float,
    off: float,
    sp_actual: float | None,
    sp_cool_normal: int,
) -> bool:
    aggressive_sp = cool_aggressive_setpoint(sp_cool_normal)
    return (
        cool_normal_active
        and cool_cycle_ts_active(started_ts, now_ts)
        and cool_elapsed_min(started_ts, now_ts) >= 40
        and not already_applied
        and tin >= off + 0.2
        and sp_actual is not None
        and sp_actual > aggressive_sp
    )


def ge_smart_hq_erd_temperature_from_celsius(celsius: int) -> int:
    """Mirror GE/SmartHQ integer Fahrenheit normalization for Celsius UI requests."""
    fahrenheit = (celsius * 9 / 5) + 32
    return math.ceil(fahrenheit)


def celsius_reported_from_ge_erd(fahrenheit: int) -> float:
    return (fahrenheit - 32) * 5 / 9


def test_cool_cycle_sentinel_1970_inactive() -> None:
    now_ts = 1_718_400_000
    assert not cool_cycle_ts_active(0, now_ts)
    assert not cool_cycle_ts_active(1, now_ts)
    assert not cool_cycle_ts_active(946_684_799, now_ts)
    assert cool_elapsed_min(0, now_ts) == 0


def test_new_cool_cycle_has_no_millions_of_elapsed_minutes() -> None:
    now_ts = 1_718_400_000
    assert cool_elapsed_min(now_ts, now_ts) == 0
    assert cool_elapsed_min(now_ts - 5, now_ts) == 0.1


def test_aggressive_blocked_before_40_real_minutes() -> None:
    now_ts = 1_718_400_000
    assert not should_apply_cool_aggressive(
        cool_normal_active=True,
        started_ts=now_ts - (39 * 60),
        now_ts=now_ts,
        already_applied=False,
        tin=24.0,
        off=23.0,
        sp_actual=22,
        sp_cool_normal=21,
    )


def test_aggressive_uses_contractual_normal_not_reported_sp() -> None:
    assert cool_aggressive_setpoint(sp_cool_normal=22, min_sp=17, max_sp=23) == 21
    # A reported/device SP of 19 must not accumulate another drop to 18.
    assert cool_aggressive_setpoint(sp_cool_normal=22, min_sp=17, max_sp=23) != 18


def test_ge_smart_hq_celsius_setpoints_do_not_round_down_systematically() -> None:
    for requested_c in (18, 19, 20, 21, 22, 23):
        erd_f = ge_smart_hq_erd_temperature_from_celsius(requested_c)
        assert celsius_reported_from_ge_erd(erd_f) >= requested_c
