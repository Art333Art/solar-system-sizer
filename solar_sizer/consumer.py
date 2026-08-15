from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class ConsumerResult:
    annual_demand_kwh: float
    ev_demand_kwh: float
    array_kwp: float
    panels: int
    inverter_low_kw: float
    inverter_high_kw: float
    battery_low_kwh: float
    battery_high_kwh: float
    annual_generation_kwh: float
    self_consumed_kwh: float
    export_kwh: float
    grid_import_kwh: float
    offpeak_charge_kwh: float
    before_cost_gbp: float
    self_consumed_value_gbp: float
    export_income_gbp: float
    after_import_cost_gbp: float
    after_net_cost_gbp: float
    annual_saving_gbp: float
    payback_years: float | None
    self_consumption_pct: float


def calculate_consumer_result(*, household_kwh: float, ev_miles_year: float, ev_miles_per_kwh: float,
    ev_charge_efficiency: float, specific_yield: float, panel_wp: float, max_panels: int,
    wants_battery: bool, import_tariff_p: float, export_tariff_p: float,
    offpeak_tariff_p: float | None, installed_cost_gbp: float | None,
    forced_array_kwp: float | None = None) -> ConsumerResult:
    if min(household_kwh, ev_miles_per_kwh, ev_charge_efficiency, specific_yield, panel_wp,
           import_tariff_p) <= 0 or max_panels < 1:
        raise ValueError("Energy, equipment and tariff inputs must be positive")
    ev_kwh = ev_miles_year / ev_miles_per_kwh / ev_charge_efficiency
    demand = household_kwh + ev_kwh
    target_kwp = demand / specific_yield
    panels = min(max_panels, max(1, ceil(target_kwp * 1000 / panel_wp)))
    if forced_array_kwp is not None:
        array_kwp = forced_array_kwp
        panels = max(1, round(array_kwp * 1000 / panel_wp))
    else:
        array_kwp = panels * panel_wp / 1000
    generation = array_kwp * specific_yield

    # Annual screening heuristic. Half-hourly consumption is needed for a firm
    # self-consumption forecast. Batteries increase the assumed useful share.
    direct_fraction = 0.45 + min(0.10, ev_kwh / max(demand, 1) * 0.25)
    useful_fraction = min(0.75 if wants_battery else 0.55, direct_fraction + (0.25 if wants_battery else 0))
    self_used = min(demand, generation * useful_fraction)
    export = max(0.0, generation - self_used)
    grid_import = max(0.0, demand - self_used)

    battery_low = demand / 365 * 0.4 if wants_battery else 0.0
    battery_high = demand / 365 * 0.8 if wants_battery else 0.0
    offpeak_charge = 0.0
    standard_import = grid_import
    if wants_battery and offpeak_tariff_p is not None and offpeak_tariff_p < import_tariff_p:
        shifted_delivered = min(grid_import * 0.20, battery_high * 180)
        offpeak_charge = shifted_delivered / 0.90
        standard_import -= shifted_delivered

    before = demand * import_tariff_p / 100
    import_cost = standard_import * import_tariff_p / 100
    if offpeak_tariff_p is not None:
        import_cost += offpeak_charge * offpeak_tariff_p / 100
    self_consumed_value = self_used * import_tariff_p / 100
    export_income = export * export_tariff_p / 100
    after = import_cost - export_income
    saving = max(0.0, before - after)
    payback = installed_cost_gbp / saving if installed_cost_gbp and saving > 0 else None
    return ConsumerResult(demand, ev_kwh, array_kwp, panels, array_kwp * 0.75, array_kwp,
        battery_low, battery_high, generation, self_used, export, grid_import, offpeak_charge,
        before, self_consumed_value, export_income, import_cost, after, saving, payback,
        self_used / generation * 100 if generation else 0)
