from dataclasses import dataclass


BATTERY_ROUND_TRIP_EFFICIENCY = 0.90


@dataclass(frozen=True)
class ScenarioResult:
    key: str
    title: str
    solar_kwp: float
    panels: int
    battery_low_kwh: float
    battery_high_kwh: float
    annual_generation_kwh: float
    self_consumed_kwh: float
    grid_import_kwh: float
    export_kwh: float
    annual_benefit_gbp: float
    installed_cost_gbp: float | None
    payback_years: float | None

    @property
    def self_consumption_pct(self) -> float:
        return self.self_consumed_kwh / self.annual_generation_kwh * 100 if self.annual_generation_kwh else 0.0


@dataclass(frozen=True)
class ScenarioComparison:
    scenarios: tuple[ScenarioResult, ...]
    strongest_key: str
    ranking_basis: str
    battery_improves_economics: bool


def compare_system_scenarios(*, annual_demand_kwh: float, ev_demand_kwh: float,
    solar_kwp: float, panels: int, specific_yield: float, import_tariff_p: float,
    export_tariff_p: float, offpeak_tariff_p: float | None,
    solar_installed_cost_gbp: float | None = None,
    battery_addon_cost_gbp: float | None = None) -> ScenarioComparison:
    """Compare one demand/array across three operating scenarios.

    EV demand must already be included in ``annual_demand_kwh``; the separate EV
    value adjusts the direct-use heuristic only and is never added a second time.
    """
    if min(annual_demand_kwh, solar_kwp, panels, specific_yield, import_tariff_p) <= 0:
        raise ValueError("Demand, array, yield and import tariff must be positive")
    if not 0 <= ev_demand_kwh <= annual_demand_kwh or export_tariff_p < 0:
        raise ValueError("EV demand and export tariff are outside the valid range")
    generation = solar_kwp * specific_yield
    direct_fraction = 0.45 + min(0.10, ev_demand_kwh / annual_demand_kwh * 0.25)
    direct_use = min(annual_demand_kwh, generation * direct_fraction)
    battery_low = annual_demand_kwh / 365 * 0.4
    battery_high = annual_demand_kwh / 365 * 0.8
    before_cost = annual_demand_kwh * import_tariff_p / 100

    def build(key: str, title: str, *, battery: bool, tariff_optimised: bool) -> ScenarioResult:
        battery_charge = 0.0
        delivered_solar = 0.0
        if battery:
            available_surplus = max(0.0, generation - direct_use)
            remaining_load = max(0.0, annual_demand_kwh - direct_use)
            annual_throughput = battery_high * 250
            battery_charge = min(available_surplus, remaining_load / BATTERY_ROUND_TRIP_EFFICIENCY,
                                 annual_throughput)
            delivered_solar = battery_charge * BATTERY_ROUND_TRIP_EFFICIENCY
        export = max(0.0, generation - direct_use - battery_charge)
        grid_import = max(0.0, annual_demand_kwh - direct_use - delivered_solar)
        standard_import = grid_import
        offpeak_input = 0.0
        if tariff_optimised and offpeak_tariff_p is not None:
            if offpeak_tariff_p / BATTERY_ROUND_TRIP_EFFICIENCY < import_tariff_p:
                shifted_delivery = min(grid_import * 0.20, battery_high * 180)
                offpeak_input = shifted_delivery / BATTERY_ROUND_TRIP_EFFICIENCY
                standard_import -= shifted_delivery
        import_cost = standard_import * import_tariff_p / 100
        if offpeak_input:
            import_cost += offpeak_input * offpeak_tariff_p / 100
        annual_benefit = before_cost - (import_cost - export * export_tariff_p / 100)
        installed_cost = solar_installed_cost_gbp
        if battery:
            installed_cost = (
                solar_installed_cost_gbp + battery_addon_cost_gbp
                if solar_installed_cost_gbp is not None and battery_addon_cost_gbp is not None
                else None
            )
        payback = installed_cost / annual_benefit if installed_cost is not None and annual_benefit > 0 else None
        return ScenarioResult(
            key, title, solar_kwp, panels, battery_low if battery else 0.0,
            battery_high if battery else 0.0, generation,
            direct_use + battery_charge, standard_import + offpeak_input,
            export, annual_benefit, installed_cost, payback,
        )

    scenarios = (
        build("solar", "Solar only", battery=False, tariff_optimised=False),
        build("battery", "Solar + battery", battery=True, tariff_optimised=False),
        build("tariff", "Solar + battery + tariff optimisation", battery=True, tariff_optimised=True),
    )
    if all(item.payback_years is not None for item in scenarios):
        strongest = min(scenarios, key=lambda item: item.payback_years or float("inf"))
        basis = "shortest simple payback"
    else:
        strongest = max(scenarios, key=lambda item: item.annual_benefit_gbp)
        basis = "highest estimated annual financial benefit"
    solar_only, battery = scenarios[:2]
    battery_improves = battery.annual_benefit_gbp > solar_only.annual_benefit_gbp
    if solar_only.payback_years is not None and battery.payback_years is not None:
        battery_improves = battery.payback_years < solar_only.payback_years
    return ScenarioComparison(scenarios, strongest.key, basis, battery_improves)
