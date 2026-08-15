import pytest

from solar_sizer.calculations import calculate_cold_voc, calculate_system
from solar_sizer.models import BatteryInputs, LoadInputs, SolarInputs
from solar_sizer.affiliates import AFFILIATE_OFFERS, enabled_affiliate_offers


def inputs(**overrides):
    values = dict(panel_wp=440, panels_series=10, parallel_strings=1, panel_voc=39.5, panel_vmp=33.2,
        panel_isc=14, panel_imp=13.25, voc_temp_coefficient_pct_c=-0.25, minimum_design_temp_c=-10,
        inverter_max_dc_v=600, mppt_min_v=120, mppt_max_v=550, mppt_max_operating_a=25,
        mppt_max_short_circuit_a=32, inverter_ac_kw=3.68, phases=1,
        annual_specific_yield_kwh_kwp=900, system_losses_pct=14)
    values.update(overrides)
    return SolarInputs(**values)


def battery():
    return BatteryInputs(12, 0.9, 0.9, 51.2, 100, 5)


def test_cold_voc_uses_datasheet_temperature_coefficient():
    assert calculate_cold_voc(40, 10, -0.25, -15) == pytest.approx(440)


def test_ev_energy_includes_charging_losses():
    result = calculate_system(LoadInputs(10, 31.5, 3.5, 0.9), inputs(), battery())
    assert result.ev_kwh_day == pytest.approx(10)
    assert result.total_load_kwh_day == pytest.approx(20)


def test_array_and_yield_do_not_double_count_pvgis_losses():
    result = calculate_system(LoadInputs(10), inputs(), battery())
    assert result.array_kwp == pytest.approx(4.4)
    assert result.annual_generation_kwh == pytest.approx(3960)


def test_battery_accounts_for_coverage_usable_fraction_and_discharge_efficiency():
    result = calculate_system(LoadInputs(10), inputs(), battery())
    assert result.battery_nominal_kwh == pytest.approx(10 * 0.5 / 0.9 / 0.9)
    assert result.battery_continuous_kw == pytest.approx(5)


def test_current_checks_operating_and_short_circuit_limits_separately():
    result = calculate_system(LoadInputs(10), inputs(parallel_strings=3), battery())
    assert next(c for c in result.checks if c.title == "MPPT input current").level == "fail"


def test_g99_warning_is_based_on_16_amps_per_phase():
    result = calculate_system(LoadInputs(10), inputs(inverter_ac_kw=4), battery())
    assert "prior approval" in next(c for c in result.checks if "G99" in c.title).title


def test_invalid_positive_values_are_rejected():
    with pytest.raises(ValueError):
        calculate_system(LoadInputs(0), inputs(), battery())


def test_only_approved_amazon_affiliate_is_public():
    enabled = enabled_affiliate_offers()
    assert [offer.key for offer in enabled] == ["amazon_electricals"]
    assert enabled[0].url == "https://link.amazon/B05z6RNmr"
    assert sum(not offer.enabled for offer in AFFILIATE_OFFERS) == 2
