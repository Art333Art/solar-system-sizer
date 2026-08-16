import pytest

from solar_sizer.comparison import compare_system_scenarios


def comparison(**overrides):
    values = dict(
        annual_demand_kwh=4000,
        ev_demand_kwh=1000,
        solar_kwp=4.4,
        panels=10,
        specific_yield=900,
        import_tariff_p=30,
        export_tariff_p=5,
        offpeak_tariff_p=None,
        solar_installed_cost_gbp=None,
        battery_addon_cost_gbp=None,
        battery_usable_kwh=6,
        battery_charge_efficiency=0.95,
        battery_discharge_efficiency=0.95,
        battery_power_kw=3.6,
        offpeak_window_hours=4,
    )
    values.update(overrides)
    return compare_system_scenarios(**values)


def by_key(result, key):
    return next(item for item in result.scenarios if item.key == key)


def test_grid_only_uses_no_solar_or_battery():
    grid = by_key(comparison(), "grid")
    assert grid.solar_kwp == grid.annual_generation_kwh == 0
    assert grid.battery_usable_kwh == grid.battery_discharge_kwh == 0
    assert grid.grid_import_kwh == pytest.approx(4000)
    assert grid.annual_electricity_cost_gbp == pytest.approx(1200)
    assert grid.annual_benefit_gbp == pytest.approx(0)


def test_solar_only_uses_no_battery():
    solar = by_key(comparison(), "solar")
    assert solar.solar_kwp == pytest.approx(4.4)
    assert solar.battery_usable_kwh == 0
    assert solar.grid_battery_charge_kwh == solar.battery_discharge_kwh == 0
    assert solar.annual_generation_kwh == pytest.approx(3960)


def test_battery_only_uses_no_solar_and_charges_offpeak():
    battery = by_key(comparison(offpeak_tariff_p=8), "battery_only")
    assert battery.solar_kwp == battery.annual_generation_kwh == 0
    assert battery.battery_usable_kwh == pytest.approx(6)
    assert battery.grid_battery_charge_kwh > 0
    assert battery.offpeak_import_kwh == pytest.approx(battery.grid_battery_charge_kwh)
    assert battery.peak_rate_import_kwh < 4000
    assert battery.annual_electricity_cost_gbp < 1200


def test_solar_plus_battery_shifts_solar_without_grid_charging():
    result = comparison(offpeak_tariff_p=8)
    solar = by_key(result, "solar")
    battery = by_key(result, "battery")
    assert battery.solar_battery_charge_kwh > 0
    assert battery.grid_battery_charge_kwh == 0
    assert battery.grid_import_kwh < solar.grid_import_kwh
    assert battery.export_kwh < solar.export_kwh


def test_tariff_optimisation_changes_grid_charging_peak_import_and_cost():
    result = comparison(offpeak_tariff_p=8)
    battery = by_key(result, "battery")
    tariff = by_key(result, "tariff")
    assert tariff.grid_battery_charge_kwh > battery.grid_battery_charge_kwh
    assert tariff.peak_rate_import_kwh < battery.peak_rate_import_kwh
    assert tariff.grid_import_kwh > battery.grid_import_kwh  # charging losses add import
    assert tariff.annual_electricity_cost_gbp < battery.annual_electricity_cost_gbp
    assert tariff.annual_benefit_gbp > battery.annual_benefit_gbp


def test_tariff_optimisation_is_not_a_scenario_without_offpeak_tariff():
    result = comparison(offpeak_tariff_p=None)
    assert "tariff" not in {item.key for item in result.scenarios}
    assert not result.tariff_optimisation_applicable
    assert "Add an off-peak tariff" in result.tariff_optimisation_reason


def test_expensive_offpeak_tariff_does_not_trigger_grid_charging():
    result = comparison(offpeak_tariff_p=35)
    battery = by_key(result, "battery")
    tariff = by_key(result, "tariff")
    assert tariff.grid_battery_charge_kwh == 0
    assert tariff.annual_electricity_cost_gbp == pytest.approx(battery.annual_electricity_cost_gbp)


def test_ev_is_not_added_twice():
    without_ev_timing = comparison(annual_demand_kwh=4000, ev_demand_kwh=0)
    with_ev_timing = comparison(annual_demand_kwh=4000, ev_demand_kwh=1000)
    assert by_key(with_ev_timing, "grid").grid_import_kwh == by_key(without_ev_timing, "grid").grid_import_kwh
    assert by_key(with_ev_timing, "solar").annual_generation_kwh == by_key(without_ev_timing, "solar").annual_generation_kwh


def test_energy_flows_and_financial_totals_reconcile():
    result = comparison(offpeak_tariff_p=8)
    for item in result.scenarios:
        assert item.annual_generation_kwh == pytest.approx(
            item.direct_solar_kwh + item.solar_battery_charge_kwh + item.export_kwh
        )
        assert 4000 == pytest.approx(
            item.direct_solar_kwh + item.battery_discharge_kwh + item.peak_rate_import_kwh
        )
        assert item.grid_import_kwh == pytest.approx(item.peak_rate_import_kwh + item.offpeak_import_kwh)
        expected_cost = item.peak_rate_import_kwh * 0.30 + item.offpeak_import_kwh * 0.08 - item.export_kwh * 0.05
        assert item.annual_electricity_cost_gbp == pytest.approx(expected_cost)
        assert item.annual_benefit_gbp == pytest.approx(1200 - expected_cost)


def test_battery_can_worsen_economics_when_export_is_more_valuable():
    result = comparison(import_tariff_p=20, export_tariff_p=30)
    assert by_key(result, "battery").annual_benefit_gbp < by_key(result, "solar").annual_benefit_gbp
    assert not result.battery_improves_economics


def test_costs_enable_payback_ranking():
    result = comparison(offpeak_tariff_p=8, solar_installed_cost_gbp=7000, battery_addon_cost_gbp=6000)
    assert by_key(result, "solar").payback_years is not None
    assert by_key(result, "battery_only").payback_years is not None
    assert result.ranking_basis == "shortest simple payback"
