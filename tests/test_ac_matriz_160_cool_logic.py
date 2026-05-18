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
