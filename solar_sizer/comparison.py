from dataclasses import dataclass


DEFAULT_CHARGE_EFFICIENCY = 0.95
DEFAULT_DISCHARGE_EFFICIENCY = 0.95
SOLAR_SHIFTING_CYCLES = 250
DAYS_PER_YEAR = 365


@dataclass(frozen=True)
class ScenarioResult:
    key: str
    title: str
    solar_kwp: float
    panels: int
    battery_low_kwh: float
    battery_high_kwh: float
    battery_usable_kwh: float
    annual_generation_kwh: float
    direct_solar_kwh: float
    solar_battery_charge_kwh: float
    grid_battery_charge_kwh: float
    battery_discharge_kwh: float
    self_consumed_kwh: float
    peak_rate_import_kwh: float
    offpeak_import_kwh: float
    grid_import_kwh: float
    export_kwh: float
    annual_electricity_cost_gbp: float
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
    tariff_optimisation_applicable: bool
    tariff_optimisation_reason: str | None


def compare_system_scenarios(*, annual_demand_kwh: float, ev_demand_kwh: float,
    solar_kwp: float, panels: int, specific_yield: float, import_tariff_p: float,
    export_tariff_p: float, offpeak_tariff_p: float | None,
    solar_installed_cost_gbp: float | None = None,
    battery_addon_cost_gbp: float | None = None,
    battery_usable_kwh: float | None = None,
    battery_charge_efficiency: float = DEFAULT_CHARGE_EFFICIENCY,
    battery_discharge_efficiency: float = DEFAULT_DISCHARGE_EFFICIENCY,
    battery_power_kw: float = 5.0,
    offpeak_window_hours: float = 4.0) -> ScenarioComparison:
    """Compare distinct grid, solar and battery operating configurations.

    EV demand is already included in ``annual_demand_kwh``. Its separate value
    only adjusts likely direct daytime use and is never added again.
    """
    if min(annual_demand_kwh, solar_kwp, panels, specific_yield, import_tariff_p,
           battery_charge_efficiency, battery_discharge_efficiency, battery_power_kw) <= 0:
        raise ValueError("Demand, equipment, efficiency and tariff inputs must be positive")
    if not 0 <= ev_demand_kwh <= annual_demand_kwh or export_tariff_p < 0:
        raise ValueError("EV demand and export tariff are outside the valid range")
    if not 0 < battery_charge_efficiency <= 1 or not 0 < battery_discharge_efficiency <= 1:
        raise ValueError("Battery efficiencies must be between zero and one")
    if offpeak_tariff_p is not None and (offpeak_tariff_p < 0 or offpeak_window_hours <= 0):
        raise ValueError("Off-peak tariff and charging window must be valid")

    generation = solar_kwp * specific_yield
    direct_fraction = 0.45 + min(0.10, ev_demand_kwh / annual_demand_kwh * 0.25)
    direct_solar = min(annual_demand_kwh, generation * direct_fraction)
    battery_low = annual_demand_kwh / DAYS_PER_YEAR * 0.4
    battery_high = annual_demand_kwh / DAYS_PER_YEAR * 0.8
    usable_capacity = battery_usable_kwh if battery_usable_kwh is not None else (battery_low + battery_high) / 2
    if usable_capacity <= 0:
        raise ValueError("Battery usable capacity must be positive")
    baseline_cost = annual_demand_kwh * import_tariff_p / 100
    round_trip_efficiency = battery_charge_efficiency * battery_discharge_efficiency

    def dispatch(*, use_solar: bool, use_battery: bool, grid_optimised: bool) -> dict[str, float]:
        scenario_generation = generation if use_solar else 0.0
        direct = direct_solar if use_solar else 0.0
        remaining_demand = annual_demand_kwh - direct
        solar_charge = 0.0
        solar_discharge = 0.0
        solar_stored = 0.0
        if use_solar and use_battery:
            surplus = max(0.0, scenario_generation - direct)
            solar_stored_limit = min(
                usable_capacity * SOLAR_SHIFTING_CYCLES,
                battery_power_kw * 6 * DAYS_PER_YEAR * battery_charge_efficiency,
            )
            solar_charge = min(surplus, remaining_demand / round_trip_efficiency,
                               solar_stored_limit / battery_charge_efficiency)
            solar_stored = solar_charge * battery_charge_efficiency
            solar_discharge = solar_stored * battery_discharge_efficiency
            remaining_demand -= solar_discharge

        grid_charge = 0.0
        grid_discharge = 0.0
        if use_battery and grid_optimised and offpeak_tariff_p is not None:
            economically_useful = offpeak_tariff_p / round_trip_efficiency < import_tariff_p
            if economically_useful:
                remaining_stored_capacity = max(0.0, usable_capacity * DAYS_PER_YEAR - solar_stored)
                stored_from_grid = min(
                    remaining_demand / battery_discharge_efficiency,
                    remaining_stored_capacity,
                    battery_power_kw * offpeak_window_hours * DAYS_PER_YEAR * battery_charge_efficiency,
                )
                grid_charge = stored_from_grid / battery_charge_efficiency
                grid_discharge = stored_from_grid * battery_discharge_efficiency
                remaining_demand -= grid_discharge

        peak_import = max(0.0, remaining_demand)
        export = max(0.0, scenario_generation - direct - solar_charge)
        total_import = peak_import + grid_charge
        net_cost = (peak_import * import_tariff_p + grid_charge * (offpeak_tariff_p or 0)) / 100
        net_cost -= export * export_tariff_p / 100
        return {
            "generation": scenario_generation,
            "direct": direct,
            "solar_charge": solar_charge,
            "grid_charge": grid_charge,
            "discharge": solar_discharge + grid_discharge,
            "peak_import": peak_import,
            "total_import": total_import,
            "export": export,
            "cost": net_cost,
        }

    def build(key: str, title: str, *, use_solar: bool, use_battery: bool,
              grid_optimised: bool) -> ScenarioResult:
        flow = dispatch(use_solar=use_solar, use_battery=use_battery, grid_optimised=grid_optimised)
        if use_solar and use_battery:
            installed_cost = (
                solar_installed_cost_gbp + battery_addon_cost_gbp
                if solar_installed_cost_gbp is not None and battery_addon_cost_gbp is not None else None
            )
        elif use_solar:
            installed_cost = solar_installed_cost_gbp
        elif use_battery:
            installed_cost = battery_addon_cost_gbp
        else:
            installed_cost = 0.0
        benefit = baseline_cost - flow["cost"]
        payback = installed_cost / benefit if installed_cost and benefit > 0 else None
        return ScenarioResult(
            key, title, solar_kwp if use_solar else 0.0, panels if use_solar else 0,
            battery_low if use_battery else 0.0, battery_high if use_battery else 0.0,
            usable_capacity if use_battery else 0.0, flow["generation"], flow["direct"],
            flow["solar_charge"], flow["grid_charge"], flow["discharge"],
            flow["direct"] + flow["solar_charge"], flow["peak_import"], flow["grid_charge"],
            flow["total_import"], flow["export"], flow["cost"], benefit, installed_cost, payback,
        )

    scenarios = [
        build("grid", "Grid only / baseline", use_solar=False, use_battery=False, grid_optimised=False),
        build("solar", "Solar only", use_solar=True, use_battery=False, grid_optimised=False),
        build("battery_only", "Battery only", use_solar=False, use_battery=True,
              grid_optimised=offpeak_tariff_p is not None),
        build("battery", "Solar + battery", use_solar=True, use_battery=True, grid_optimised=False),
    ]
    tariff_applicable = offpeak_tariff_p is not None
    tariff_reason = None
    if tariff_applicable:
        scenarios.append(build("tariff", "Solar + battery + tariff optimisation",
                               use_solar=True, use_battery=True, grid_optimised=True))
    else:
        tariff_reason = "Add an off-peak tariff and charging window to compare tariff optimisation."

    candidates = [item for item in scenarios if item.key != "grid"]
    payback_candidates = [item for item in candidates if item.payback_years is not None]
    if solar_installed_cost_gbp is not None and battery_addon_cost_gbp is not None and payback_candidates:
        strongest = min(payback_candidates, key=lambda item: item.payback_years or float("inf"))
        basis = "shortest simple payback"
    else:
        strongest = max(candidates, key=lambda item: item.annual_benefit_gbp)
        basis = "highest estimated annual financial benefit"
    solar_only = next(item for item in scenarios if item.key == "solar")
    solar_battery = next(item for item in scenarios if item.key == "battery")
    battery_improves = solar_battery.annual_benefit_gbp > solar_only.annual_benefit_gbp
    if solar_only.payback_years is not None and solar_battery.payback_years is not None:
        battery_improves = solar_battery.payback_years < solar_only.payback_years
    return ScenarioComparison(tuple(scenarios), strongest.key, basis, battery_improves,
                              tariff_applicable, tariff_reason)
