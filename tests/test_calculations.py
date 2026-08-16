import pytest

from solar_sizer.calculations import calculate_cold_voc, calculate_system
from solar_sizer.models import BatteryInputs, LoadInputs, SolarInputs
from solar_sizer.affiliates import (
    AFFILIATE_OFFERS, affiliate_products_for_page, enabled_affiliate_offers,
)
from solar_sizer.consumer import calculate_consumer_result


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


def test_only_approved_amazon_affiliates_are_public():
    enabled = enabled_affiliate_offers()
    assert [offer.key for offer in enabled] == [
        "amazon_electricals", "amazon_ev_charger", "amazon_solar_tools",
        "amazon_energy_monitor",
    ]
    assert {offer.key: offer.url for offer in enabled} == {
        "amazon_electricals": "https://link.amazon/B05z6RNmr",
        "amazon_ev_charger": "https://link.amazon/B03Lpp2EH",
        "amazon_solar_tools": "https://link.amazon/B0f4YmGAU",
        "amazon_energy_monitor": "https://link.amazon/B0fdrsDTb",
    }
    disabled_cable = next(offer for offer in AFFILIATE_OFFERS if offer.product_id == "amazon_ev_cable")
    assert not disabled_cable.enabled
    assert disabled_cable.url == "https://link.amazon/B04LIcvRh"
    assert sum(not offer.enabled for offer in AFFILIATE_OFFERS) == 3
    assert len({offer.product_id for offer in AFFILIATE_OFFERS}) == len(AFFILIATE_OFFERS)


def test_affiliates_are_filtered_by_calculator_context():
    assert [offer.key for offer in enabled_affiliate_offers({"monitoring"})] == ["amazon_energy_monitor"]
    assert [offer.key for offer in enabled_affiliate_offers({"monitoring", "ev"})] == [
        "amazon_ev_charger", "amazon_energy_monitor",
    ]
    assert [offer.key for offer in enabled_affiliate_offers({"advanced", "monitoring"})] == [
        "amazon_energy_monitor",
    ]
    assert [offer.key for offer in enabled_affiliate_offers({"advanced", "diy", "monitoring"})] == [
        "amazon_electricals", "amazon_solar_tools", "amazon_energy_monitor",
    ]


def test_context_controls_prominence_while_mode_controls_discovery():
    simple = affiliate_products_for_page("Simple", {"monitoring"})
    assert [offer.product_id for offer in simple] == ["amazon_energy_monitor", "amazon_ev_charger"]
    simple_ev = affiliate_products_for_page("Simple", {"monitoring", "ev"})
    assert [offer.product_id for offer in simple_ev] == ["amazon_ev_charger", "amazon_energy_monitor"]
    advanced = affiliate_products_for_page("Advanced", {"advanced", "diy", "monitoring"})
    assert [offer.product_id for offer in advanced] == [
        "amazon_solar_tools", "amazon_electricals", "amazon_energy_monitor", "amazon_ev_charger",
    ]
    assert len({offer.product_id for offer in advanced}) == len(advanced)
    assert "amazon_ev_cable" not in {offer.product_id for offer in advanced}


def test_swa_remains_available_only_in_advanced_diy_context():
    assert "amazon_electricals" not in {
        offer.product_id for offer in affiliate_products_for_page("Advanced", {"advanced", "monitoring"})
    }
    swa = next(
        offer for offer in affiliate_products_for_page("Advanced", {"advanced", "diy", "monitoring"})
        if offer.product_id == "amazon_electricals"
    )
    assert swa.url == "https://link.amazon/B05z6RNmr"


def test_equivalent_simple_and_advanced_inputs_have_consistent_core_results():
    load = LoadInputs(10, 20, 3.5, 0.9)
    solar = inputs()
    advanced = calculate_system(load, solar, battery())
    simple = calculate_consumer_result(
        household_kwh=load.home_kwh_day * 365,
        ev_miles_year=load.ev_miles_day * 365,
        ev_miles_per_kwh=load.ev_efficiency_miles_per_kwh,
        ev_charge_efficiency=load.ev_charging_efficiency,
        specific_yield=solar.annual_specific_yield_kwh_kwp,
        panel_wp=solar.panel_wp,
        max_panels=solar.panels_series * solar.parallel_strings,
        wants_battery=True,
        import_tariff_p=25,
        export_tariff_p=15,
        offpeak_tariff_p=None,
        installed_cost_gbp=None,
        forced_array_kwp=advanced.array_kwp,
    )

    assert simple.ev_demand_kwh == pytest.approx(advanced.ev_kwh_day * 365)
    assert simple.annual_demand_kwh == pytest.approx(advanced.total_load_kwh_day * 365)
    assert simple.array_kwp == pytest.approx(advanced.array_kwp)
    assert simple.annual_generation_kwh == pytest.approx(advanced.annual_generation_kwh)
