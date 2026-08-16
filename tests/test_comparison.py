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
    )
    values.update(overrides)
    return compare_system_scenarios(**values)


def test_solar_only_and_battery_scenarios_use_same_array_and_demand():
    result = comparison()
    solar, battery, tariff = result.scenarios
    assert solar.solar_kwp == battery.solar_kwp == tariff.solar_kwp == pytest.approx(4.4)
    assert solar.annual_generation_kwh == battery.annual_generation_kwh == tariff.annual_generation_kwh
    assert solar.battery_high_kwh == 0
    assert battery.battery_high_kwh > 0
    assert battery.grid_import_kwh < solar.grid_import_kwh
    assert battery.export_kwh < solar.export_kwh


def test_battery_can_improve_economics_when_import_value_exceeds_lost_export():
    result = comparison(import_tariff_p=30, export_tariff_p=5)
    solar, battery, _ = result.scenarios
    assert battery.annual_benefit_gbp > solar.annual_benefit_gbp
    assert result.battery_improves_economics


def test_battery_can_worsen_economics_when_export_is_more_valuable():
    result = comparison(import_tariff_p=20, export_tariff_p=30)
    solar, battery, _ = result.scenarios
    assert battery.annual_benefit_gbp < solar.annual_benefit_gbp
    assert not result.battery_improves_economics
    assert result.strongest_key == "solar"


def test_ev_energy_is_context_not_duplicate_demand():
    without_ev_timing = comparison(annual_demand_kwh=4000, ev_demand_kwh=0)
    with_ev_timing = comparison(annual_demand_kwh=4000, ev_demand_kwh=1000)
    assert with_ev_timing.scenarios[0].annual_generation_kwh == without_ev_timing.scenarios[0].annual_generation_kwh
    assert with_ev_timing.scenarios[1].battery_high_kwh == without_ev_timing.scenarios[1].battery_high_kwh
    assert with_ev_timing.scenarios[0].self_consumed_kwh > without_ev_timing.scenarios[0].self_consumed_kwh


def test_offpeak_tariff_is_used_only_when_it_beats_standard_import_after_losses():
    cheap = comparison(offpeak_tariff_p=8)
    expensive = comparison(offpeak_tariff_p=35)
    assert cheap.scenarios[2].annual_benefit_gbp > cheap.scenarios[1].annual_benefit_gbp
    assert expensive.scenarios[2].annual_benefit_gbp == pytest.approx(expensive.scenarios[1].annual_benefit_gbp)


def test_costs_enable_scenario_payback_comparison():
    result = comparison(solar_installed_cost_gbp=7000, battery_addon_cost_gbp=6000)
    assert all(item.payback_years is not None for item in result.scenarios)
    assert result.ranking_basis == "shortest simple payback"
    assert result.strongest_key == "solar"
