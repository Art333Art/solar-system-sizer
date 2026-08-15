import pytest

from solar_sizer import BatteryInputs, LoadInputs, SolarInputs, calculate_system
from solar_sizer.consumer import calculate_consumer_result


def result(**overrides):
    values = dict(household_kwh=3000, ev_miles_year=0, ev_miles_per_kwh=3.5,
        ev_charge_efficiency=0.9, specific_yield=900, panel_wp=450, max_panels=20,
        wants_battery=False, import_tariff_p=25, export_tariff_p=15,
        offpeak_tariff_p=None, installed_cost_gbp=8000)
    values.update(overrides)
    return calculate_consumer_result(**values)


def test_financial_components_reconcile():
    item = result()
    expected_after = item.grid_import_kwh * 0.25 - item.export_kwh * 0.15
    assert item.after_net_cost_gbp == pytest.approx(expected_after)
    assert item.self_consumed_value_gbp == pytest.approx(item.self_consumed_kwh * 0.25)
    assert item.export_income_gbp == pytest.approx(item.export_kwh * 0.15)
    assert item.after_import_cost_gbp - item.export_income_gbp == pytest.approx(item.after_net_cost_gbp)
    assert item.annual_saving_gbp == pytest.approx(item.before_cost_gbp - expected_after)
    assert item.payback_years == pytest.approx(8000 / item.annual_saving_gbp)


def test_offpeak_tariff_shifts_import_and_accounts_for_losses():
    flat = result(wants_battery=True)
    cheap = result(wants_battery=True, offpeak_tariff_p=8)
    assert cheap.offpeak_charge_kwh > 0
    assert cheap.after_net_cost_gbp < flat.after_net_cost_gbp


def test_offpeak_more_expensive_than_standard_is_not_used():
    item = result(wants_battery=True, offpeak_tariff_p=30)
    assert item.offpeak_charge_kwh == 0


def test_ev_mileage_includes_charging_loss():
    item = result(ev_miles_year=3150)
    assert item.ev_demand_kwh == pytest.approx(1000)
    assert item.annual_demand_kwh == pytest.approx(4000)


def test_battery_range_is_zero_unless_requested():
    assert result().battery_high_kwh == 0
    assert result(wants_battery=True).battery_low_kwh > 0


def test_simple_and_advanced_generation_are_consistent_for_same_array_and_yield():
    simple = result(forced_array_kwp=4.5)
    advanced = calculate_system(LoadInputs(3000 / 365), SolarInputs(450, 10, 1, 40, 34, 14, 13,
        -0.25, -10, 600, 120, 550, 25, 32, 3.68, 1, 900, 14),
        BatteryInputs(12, 0.9, 0.94, 51.2, 100, 5))
    assert simple.annual_generation_kwh == advanced.annual_generation_kwh
