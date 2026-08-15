from .models import BatteryInputs, Check, LoadInputs, SolarInputs, SystemResult


def _positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")


def calculate_cold_voc(voc_stc: float, panels: int, coefficient_pct_c: float, minimum_temp_c: float) -> float:
    """String open-circuit voltage at design temperature, referenced to STC (25 C)."""
    _positive("panel Voc", voc_stc)
    if panels < 1:
        raise ValueError("panels must be at least one")
    if coefficient_pct_c >= 0:
        raise ValueError("Voc temperature coefficient must be negative")
    multiplier = 1 + (coefficient_pct_c / 100.0) * (minimum_temp_c - 25.0)
    return voc_stc * panels * multiplier


def calculate_system(load: LoadInputs, solar: SolarInputs, battery: BatteryInputs) -> SystemResult:
    for name, value in (("home demand", load.home_kwh_day), ("EV efficiency", load.ev_efficiency_miles_per_kwh),
        ("EV charging efficiency", load.ev_charging_efficiency), ("panel rating", solar.panel_wp),
        ("inverter AC rating", solar.inverter_ac_kw), ("specific yield", solar.annual_specific_yield_kwh_kwp),
        ("battery usable fraction", battery.usable_fraction), ("battery discharge-path efficiency", battery.discharge_path_efficiency),
        ("battery voltage", battery.battery_voltage)):
        _positive(name, value)
    if not 0 < battery.usable_fraction <= 1 or not 0 < battery.discharge_path_efficiency <= 1:
        raise ValueError("battery fractions must be between zero and one")
    if not 0 < load.ev_charging_efficiency <= 1:
        raise ValueError("EV charging efficiency must be between zero and one")

    ev_kwh = load.ev_miles_day / load.ev_efficiency_miles_per_kwh / load.ev_charging_efficiency
    total_load = load.home_kwh_day + ev_kwh
    array_kwp = solar.panels_series * solar.parallel_strings * solar.panel_wp / 1000
    annual_generation = array_kwp * solar.annual_specific_yield_kwh_kwp
    backup_energy = total_load * battery.desired_backup_hours / 24
    battery_nominal = backup_energy / battery.usable_fraction / battery.discharge_path_efficiency
    battery_kw = min(battery.battery_voltage * battery.max_continuous_current_a / 1000, battery.inverter_battery_power_kw)
    cold_voc = calculate_cold_voc(solar.panel_voc, solar.panels_series, solar.voc_temp_coefficient_pct_c, solar.minimum_design_temp_c)
    vmp = solar.panel_vmp * solar.panels_series
    imp = solar.panel_imp * solar.parallel_strings
    isc = solar.panel_isc * solar.parallel_strings
    ratio = array_kwp / solar.inverter_ac_kw
    checks: list[Check] = []
    checks.append(Check("pass" if cold_voc < solar.inverter_max_dc_v else "fail", "Cold-weather Voc",
        f"{cold_voc:.0f} V versus {solar.inverter_max_dc_v:.0f} V absolute DC limit. Use the module datasheet coefficient and the site's design minimum temperature."))
    checks.append(Check("pass" if solar.mppt_min_v <= vmp <= solar.mppt_max_v else "fail", "MPPT operating voltage",
        f"Nominal string Vmp {vmp:.0f} V; inverter window {solar.mppt_min_v:.0f}–{solar.mppt_max_v:.0f} V. Hot-module Vmp can be lower and needs final datasheet verification."))
    current_ok = imp <= solar.mppt_max_operating_a and isc <= solar.mppt_max_short_circuit_a
    checks.append(Check("pass" if current_ok else "fail", "MPPT input current",
        f"Operating {imp:.1f} A / short-circuit {isc:.1f} A; limits {solar.mppt_max_operating_a:.1f} A / {solar.mppt_max_short_circuit_a:.1f} A. Confirm whether limits apply per input or per MPPT."))
    checks.append(Check("pass" if 0.8 <= ratio <= 1.5 else "warn", "DC/AC ratio",
        f"{ratio:.2f}. Clipping and manufacturer oversizing limits need hourly modelling and the selected inverter datasheet."))
    amps_per_phase = solar.inverter_ac_kw * 1000 / (230 * solar.phases)
    if amps_per_phase <= 16:
        checks.append(Check("warn", "G98 / G99 route", f"Approx. {amps_per_phase:.1f} A per phase. G98 may apply only when the complete generating installation is within 16 A/phase and uses applicable fully type-tested equipment; notify the DNO after commissioning."))
    else:
        checks.append(Check("warn", "G99 prior approval", f"Approx. {amps_per_phase:.1f} A per phase exceeds 16 A/phase. Seek DNO approval before installation/connection. Export limiting does not automatically make a larger installation G98."))
    return SystemResult(ev_kwh, total_load, array_kwp, annual_generation, annual_generation / 365, battery_nominal,
                        battery_kw, cold_voc, vmp, imp, isc, ratio, tuple(checks))
