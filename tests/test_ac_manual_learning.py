from tools.ac_manual_learning import Thresholds, apply_manual_learning


def test_cool_manual_off_during_active_cycle():
    before = Thresholds(on=24.50, off=23.75)
    after = apply_manual_learning("COOL", "manual_off_during_active_cycle", before)
    assert after.on - before.on == 0.25
    assert after.off - before.off == 0.25
    assert after.on > after.off


def test_cool_manual_on_after_auto_stop():
    before = Thresholds(on=24.50, off=23.75)
    after = apply_manual_learning("COOL", "manual_on_after_auto_stop", before)
    assert after.on - before.on == -0.25
    assert after.off - before.off == -0.25
    assert after.on > after.off


def test_heat_manual_off_during_active_cycle():
    before = Thresholds(on=20.25, off=21.00)
    after = apply_manual_learning("HEAT", "manual_off_during_active_cycle", before)
    assert after.on - before.on == -0.25
    assert after.off - before.off == -0.25
    assert after.on < after.off


def test_heat_manual_on_after_auto_stop():
    before = Thresholds(on=20.25, off=21.00)
    after = apply_manual_learning("HEAT", "manual_on_after_auto_stop", before)
    assert after.on - before.on == 0.25
    assert after.off - before.off == 0.25
    assert after.on < after.off
