import pytest

from solar_sizer.configuration import CONFIGURATION_OPTIONS, active_configuration


@pytest.mark.parametrize(
    ("title", "solar", "battery", "pv_inverter", "battery_inverter", "tariff"),
    (
        ("Grid only / baseline", False, False, False, False, False),
        ("Solar only", True, False, True, False, False),
        ("Battery only", False, True, False, True, False),
        ("Solar + battery", True, True, True, True, False),
        ("Solar + battery + tariff optimisation", True, True, True, True, True),
    ),
)
def test_canonical_configuration_matrix(title, solar, battery, pv_inverter, battery_inverter, tariff):
    state = active_configuration(title)
    assert state.solar is solar
    assert state.battery is battery
    assert state.pv_inverter_mppt is pv_inverter
    assert state.battery_inverter_charger is battery_inverter
    assert state.inverter_charger is (pv_inverter or battery_inverter)
    assert state.grid_tariffs
    assert state.tariff_optimisation is tariff


def test_configuration_options_and_unknown_value_are_centralised():
    assert len(CONFIGURATION_OPTIONS) == 5
    with pytest.raises(ValueError, match="Unknown system configuration"):
        active_configuration("not a configuration")
