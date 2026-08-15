from dataclasses import dataclass


@dataclass(frozen=True)
class LoadInputs:
    home_kwh_day: float
    ev_miles_day: float = 0.0
    ev_efficiency_miles_per_kwh: float = 3.5
    ev_charging_efficiency: float = 0.9


@dataclass(frozen=True)
class SolarInputs:
    panel_wp: float
    panels_series: int
    parallel_strings: int
    panel_voc: float
    panel_vmp: float
    panel_isc: float
    panel_imp: float
    voc_temp_coefficient_pct_c: float
    minimum_design_temp_c: float
    inverter_max_dc_v: float
    mppt_min_v: float
    mppt_max_v: float
    mppt_max_operating_a: float
    mppt_max_short_circuit_a: float
    inverter_ac_kw: float
    phases: int = 1
    annual_specific_yield_kwh_kwp: float = 900.0
    system_losses_pct: float = 14.0


@dataclass(frozen=True)
class BatteryInputs:
    desired_backup_hours: float
    usable_fraction: float
    discharge_path_efficiency: float
    battery_voltage: float
    max_continuous_current_a: float
    inverter_battery_power_kw: float


@dataclass(frozen=True)
class Check:
    level: str
    title: str
    detail: str


@dataclass(frozen=True)
class SystemResult:
    ev_kwh_day: float
    total_load_kwh_day: float
    array_kwp: float
    annual_generation_kwh: float
    average_generation_kwh_day: float
    battery_nominal_kwh: float
    battery_continuous_kw: float
    cold_string_voc: float
    string_vmp: float
    array_imp: float
    array_isc: float
    dc_ac_ratio: float
    checks: tuple[Check, ...]
