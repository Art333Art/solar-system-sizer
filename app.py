import streamlit as st

from solar_sizer import BatteryInputs, LoadInputs, SolarInputs, calculate_system
from solar_sizer.affiliates import affiliate_products_for_page
from solar_sizer.analytics import record_event
from solar_sizer.comparison import compare_system_scenarios
from solar_sizer.configuration import CONFIGURATION_OPTIONS, active_configuration
from solar_sizer.content import BUYING_GUIDES
from solar_sizer.consumer import calculate_consumer_result
from solar_sizer.leads import QuoteInterest, submit_quote_interest, validate_quote_interest
from solar_sizer.pvgis import SolarDataError, fallback_specific_yield, fetch_pvgis_yield, geocode_uk_postcode
from solar_sizer.smart_meter import SmartMeterCSVError, parse_smart_meter_csv

APP_RELEASE = "canonical-configuration-state-2026-08"

st.set_page_config(page_title="UK Solar Panel, Battery & EV Sizing Calculator", page_icon="☀️", layout="wide",
    menu_items={"About": "Independent UK solar, battery, inverter and EV feasibility calculator."})


@st.cache_data(ttl=86400, show_spinner=False)
def cached_location(postcode: str) -> tuple[float, float]:
    return geocode_uk_postcode(postcode)


@st.cache_data(ttl=86400, show_spinner=False)
def cached_yield(latitude: float, longitude: float, tilt: float, aspect: float):
    return fetch_pvgis_yield(latitude, longitude, tilt, aspect)


def persistent_number_input(label, min_value, max_value, default, step, *, state_key, disabled=False):
    """Keep user input when Streamlit removes a mode-specific widget from the tree."""
    stored_key = f"stored_{state_key}"
    widget_key = f"widget_{state_key}"
    if stored_key not in st.session_state:
        st.session_state[stored_key] = default

    def store_value():
        st.session_state[stored_key] = st.session_state[widget_key]

    return st.number_input(
        label, min_value, max_value, st.session_state[stored_key], step,
        disabled=disabled, key=widget_key, on_change=store_value,
    )


if "events" not in st.session_state:
    st.session_state.events = []
record_event(st.session_state.events, "calculator_started")

st.title("UK Solar & Battery System Sizer")
st.markdown("Estimate how many solar panels you may need, a sensible battery range, annual generation, grid import/export, savings and payback using local UK solar data.")
st.caption("Free independent early-stage estimate — not an installer quotation or final electrical design.")
mode = st.radio("Calculator mode", ["Simple", "Advanced"], horizontal=True,
                help="Simple uses homeowner-friendly assumptions. Advanced exposes datasheet and electrical limits.")
selected_configuration = st.selectbox(
    "System configuration",
    CONFIGURATION_OPTIONS,
    index=1,
    key="system_configuration",
    help="Choose what the selected result includes before entering detailed assumptions. All applicable configurations are compared below.",
)
configuration = active_configuration(selected_configuration)
selected_key = configuration.key
solar_active = configuration.solar
battery_active = configuration.battery
pv_inverter_active = configuration.pv_inverter_mppt
battery_inverter_active = configuration.battery_inverter_charger
inverter_charger_active = configuration.inverter_charger
tariff_active = configuration.tariff_optimisation
if mode == "Advanced":
    record_event(st.session_state.events, "advanced_opened")
recommendation_contexts = {"monitoring"}

if mode == "Simple":
    st.subheader("Tell us about your home")
    c1, c2 = st.columns(2)
    with c1:
        postcode = st.text_input("UK postcode", placeholder="For example, M1 1AE", disabled=not solar_active,
            help="Used to obtain coordinates, which are sent to PVGIS for the solar estimate.")
        usage_basis = st.radio("Electricity usage", ["Annual", "Daily"], horizontal=True)
        usage_value = st.number_input("Usage (kWh/year)" if usage_basis == "Annual" else "Usage (kWh/day)",
            1.0, 50000.0 if usage_basis == "Annual" else 150.0, 3000.0 if usage_basis == "Annual" else 8.2, 10.0 if usage_basis == "Annual" else 0.1)
        annual_home_kwh = usage_value if usage_basis == "Annual" else usage_value * 365
        import_tariff = st.number_input("Electricity import tariff (p/kWh)", 0.1, 100.0, 25.0, 0.5)
        export_tariff = st.number_input("Export tariff (p/kWh)", 0.0, 100.0, 15.0, 0.5)
        if tariff_active:
            st.caption("Tariff optimisation selected: enter the required off-peak tariff and charging window below.")
            has_offpeak = True
        else:
            has_offpeak = st.checkbox("I have an off-peak import tariff", key="simple_has_offpeak")
        offpeak_tariff = st.number_input("Off-peak tariff (p/kWh)", 0.0, 100.0, 8.0, 0.5) if has_offpeak else None
        offpeak_window_hours = st.number_input("Off-peak charging window (hours/day)", 0.5, 12.0, 4.0, 0.5) if has_offpeak else 0.0
    with c2:
        orientation_label = st.selectbox("Main roof orientation", ["South", "South-east", "South-west", "East", "West", "North-east", "North-west", "North"], disabled=not solar_active)
        aspect_map = {"South": 0, "South-east": -45, "South-west": 45, "East": -90, "West": 90,
                      "North-east": -135, "North-west": 135, "North": 180}
        roof_description = st.selectbox("Roof pitch", ["Typical pitched roof (~35°)", "Shallow pitch (~20°)", "Steep pitch (~50°)", "Flat roof (~10°)", "Enter angle"], disabled=not solar_active)
        tilt_map = {"Typical pitched roof (~35°)": 35, "Shallow pitch (~20°)": 20,
                    "Steep pitch (~50°)": 50, "Flat roof (~10°)": 10}
        tilt = st.number_input("Roof tilt from horizontal (degrees)", 0, 90, 35, disabled=not solar_active) if roof_description == "Enter angle" else tilt_map[roof_description]
        roof_basis = st.radio("Available roof space", ["Usable area", "Approximate panel count"], horizontal=True, disabled=not solar_active)
        if roof_basis == "Usable area":
            roof_area = persistent_number_input("Usable unshaded roof area (m²)", 2.0, 300.0, 30.0, 1.0,
                disabled=not solar_active, state_key="simple_roof_area")
            max_panels = max(1, int(roof_area / 2.0))
            if solar_active:
                st.caption(f"Assuming about 2 m² per panel: space for roughly {max_panels} panels.")
            else:
                st.caption("Solar inputs are inactive for the selected configuration.")
        else:
            max_panels = st.number_input("Approximate maximum panel count", 1, 100, 12, disabled=not solar_active)
        st.markdown("#### Electric vehicle")
        ev_miles_week = st.number_input("EV driving (miles/week)", 0.0, 2000.0, 0.0, 10.0)
        knows_cost = st.checkbox("I have an estimated installed cost")
        installed_cost = st.number_input("Estimated solar-only installed cost (£)", 100.0, 100000.0, 7000.0, 100.0, disabled=not solar_active) if knows_cost else None

    simple_ev_kwh = ev_miles_week * 52 / 3.5 / 0.90
    simple_daily_kwh = (annual_home_kwh + simple_ev_kwh) / 365
    recommended_battery_low = simple_daily_kwh * 0.4
    recommended_battery_high = simple_daily_kwh * 0.8
    with st.container(border=True):
        st.markdown("### Home battery storage")
        if battery_active:
            st.caption(f"Enabled for {configuration.title}. Suggested usable range: {recommended_battery_low:.1f}–{recommended_battery_high:.1f} kWh.")
        else:
            st.caption(f"Disabled for {configuration.title}. Your stored battery settings are retained if you switch back.")
        battery_size_kwh = persistent_number_input(
            "Battery size (kWh usable)", 0.5, 100.0,
            round((recommended_battery_low + recommended_battery_high) * 2) / 4,
            0.5, disabled=not battery_active, state_key="simple_battery_size",
        )
        simple_battery_power_kw = persistent_number_input(
            "Battery inverter/charger power limit (kW)", 0.1, 50.0, 5.0, 0.1,
            disabled=not battery_inverter_active, state_key="simple_battery_power",
        )
        allow_battery_export = st.checkbox(
            "Allow battery export to grid", value=False, disabled=not battery_active,
            key="simple_allow_battery_export",
        )
        battery_addon_cost = st.number_input(
            "Estimated battery add-on cost (£)", 0.0, 50000.0, 5000.0, 100.0,
            disabled=not battery_active,
        ) if knows_cost else None
        if battery_active:
            st.caption("Battery export is modelled only when the entered tariff makes it viable. Supplier and export-tariff eligibility for grid-charged energy varies.")

    aspect = aspect_map[orientation_label]
    yield_source = "Conservative UK fallback"
    specific_yield = fallback_specific_yield(aspect, tilt)
    if solar_active and postcode.strip():
        try:
            with st.spinner("Checking local solar resource with PVGIS…"):
                lat, lon = cached_location(postcode)
                pvgis = cached_yield(lat, lon, float(tilt), float(aspect))
            specific_yield = pvgis.specific_yield_kwh_kwp
            yield_source = f"PVGIS 5.3 ({specific_yield:.0f} kWh/kWp/year)"
        except SolarDataError as exc:
            st.warning(f"{exc}. Using a conservative UK fallback; try again before making a purchase decision.")
    elif solar_active:
        st.info("Enter a complete postcode for an automatic location-specific PVGIS estimate. A conservative placeholder is shown meanwhile.")

    consumer = calculate_consumer_result(household_kwh=annual_home_kwh, ev_miles_year=ev_miles_week * 52,
        ev_miles_per_kwh=3.5, ev_charge_efficiency=0.90, specific_yield=specific_yield, panel_wp=440,
        max_panels=int(max_panels), wants_battery=battery_active, import_tariff_p=import_tariff,
        export_tariff_p=export_tariff, offpeak_tariff_p=offpeak_tariff,
        installed_cost_gbp=(installed_cost + battery_addon_cost if battery_active and installed_cost is not None else installed_cost))
    comparison_inputs = dict(
        annual_demand_kwh=consumer.annual_demand_kwh,
        ev_demand_kwh=consumer.ev_demand_kwh,
        solar_kwp=consumer.array_kwp,
        panels=consumer.panels,
        specific_yield=specific_yield,
        import_tariff_p=import_tariff,
        export_tariff_p=export_tariff,
        offpeak_tariff_p=offpeak_tariff,
        solar_installed_cost_gbp=installed_cost,
        battery_addon_cost_gbp=battery_addon_cost,
        battery_usable_kwh=battery_size_kwh,
        battery_charge_efficiency=0.95,
        battery_discharge_efficiency=0.95,
        battery_charge_power_kw=simple_battery_power_kw,
        battery_discharge_power_kw=simple_battery_power_kw,
        allow_battery_export=allow_battery_export,
        offpeak_window_hours=offpeak_window_hours or 4.0,
    )
    comparison = compare_system_scenarios(**comparison_inputs)
    selected_scenario = next(item for item in comparison.scenarios if item.key == selected_key)
    record_event(st.session_state.events, "calculator_completed")
    if ev_miles_week > 0:
        recommendation_contexts.add("ev")

    st.subheader("Your headline estimate")
    r1, r2, r3 = st.columns(3)
    r1.metric("Selected solar array", f"{selected_scenario.solar_kwp:.1f} kWp", f"about {selected_scenario.panels} × 440 W panels" if selected_scenario.panels else "solar disabled")
    r2.metric("Estimated annual generation", f"{selected_scenario.annual_generation_kwh:,.0f} kWh/year")
    r3.metric("Estimated annual benefit", f"£{selected_scenario.annual_benefit_gbp:,.0f}")
    r4, r5, r6 = st.columns(3)
    r4.metric("Selected battery", f"{selected_scenario.battery_usable_kwh:.1f} kWh usable" if battery_active else "Battery disabled")
    r5.metric("Simple payback", f"{selected_scenario.payback_years:.1f} years" if selected_scenario.payback_years else "Add installed costs")
    if solar_active:
        r6.metric("Inverter / charger", f"PV inverter {consumer.inverter_low_kw:.1f}–{consumer.inverter_high_kw:.1f} kW")
    elif battery_inverter_active:
        r6.metric("Inverter / charger", f"Battery inverter/charger ≤ {simple_battery_power_kw:.1f} kW")
    else:
        r6.metric("Inverter / charger", "Not applicable")
    st.caption("Annual saving is based on your entered tariffs and the assumptions described below; it is not a guaranteed bill reduction.")

    with st.expander("Energy and bill breakdown", expanded=True):
        rows = {
            "Annual demand (including EV)": f"{consumer.annual_demand_kwh:,.0f} kWh",
            "EV demand": f"{consumer.ev_demand_kwh:,.0f} kWh",
            "Solar used in the home": f"{selected_scenario.self_consumed_kwh:,.0f} kWh ({selected_scenario.self_consumption_pct:.0f}% of generation)",
            "Peak-rate grid import": f"{selected_scenario.peak_rate_import_kwh:,.0f} kWh",
            "Total grid import": f"{selected_scenario.grid_import_kwh:,.0f} kWh",
            "Solar export": f"{selected_scenario.solar_export_kwh:,.0f} kWh",
            "Battery energy used in the home": f"{selected_scenario.battery_discharge_kwh:,.0f} kWh",
            "Battery export": f"{selected_scenario.battery_export_kwh:,.0f} kWh",
            "Battery charging/discharging losses": f"{selected_scenario.battery_charge_loss_kwh + selected_scenario.battery_discharge_loss_kwh:,.0f} kWh",
            "Off-peak battery charging": f"{selected_scenario.offpeak_import_kwh:,.0f} kWh" if selected_scenario.offpeak_import_kwh else "Not used",
            "Import cost before solar": f"£{consumer.before_cost_gbp:,.0f}/year",
            "Export income": f"£{selected_scenario.export_income_gbp:,.0f}/year",
            "Grid import cost": f"£{(selected_scenario.peak_rate_import_kwh * import_tariff + selected_scenario.offpeak_import_kwh * (offpeak_tariff or 0)) / 100:,.0f}/year",
            "Net annual cost after export income": f"£{selected_scenario.annual_electricity_cost_gbp:,.0f}/year",
        }
        for label, value in rows.items():
            st.write(f"**{label}:** {value}")
        st.caption(f"Solar source: {yield_source}. Values are rounded screening estimates, not tariff or performance guarantees.")

    with st.expander("Assumptions and technical next steps"):
        st.markdown("""
- Array size aims to cover annual household and EV demand, limited by the roof-space answer.
- A 440 W, roughly 2 m² panel is assumed. Actual panel dimensions and roof exclusion zones vary.
- Self-consumption uses an annual heuristic (higher with a battery); half-hourly load and PV simulation is required for a firm forecast.
- Off-peak modelling shifts eligible import through the selected battery after charge/discharge losses. Battery export remains zero unless explicitly enabled, economically viable under the entered tariffs, and technically constrained by the selected capacity and power.
- The inverter range is an initial DC/AC screening range. Equipment, phases, DNO route, clipping and backup loads require a competent designer.
""")
    plan_inverter_low = consumer.inverter_low_kw
    plan_inverter_high = consumer.inverter_high_kw
else:
    recommendation_contexts.add("advanced")
    st.subheader("Advanced system-design workbench")
    st.caption("Adjust the grouped controls in the left sidebar; every result updates immediately.")
    with st.sidebar:
        st.header("Advanced controls")
        with st.expander("1. Demand and EV", expanded=True):
            home_kwh = st.number_input("Home electricity use (kWh/day)", 1.0, 100.0, 10.0, 0.5)
            ev_miles = st.number_input("EV driving (miles/day)", 0.0, 300.0, 20.0, 1.0)
            ev_efficiency = st.number_input("EV efficiency (miles/kWh)", 1.0, 6.0, 3.5, 0.1)
            ev_charge_efficiency = st.slider("EV charging efficiency", 70, 100, 90) / 100
        with st.expander("2. PV module and strings", expanded=solar_active):
            panel_wp = persistent_number_input("Panel power (Wp)", 200, 800, 440, 5,
                disabled=not solar_active, state_key="advanced_panel_wp")
            series = st.number_input("Panels per series string", 1, 40, 10, disabled=not solar_active)
            parallel = st.number_input("Parallel strings on this MPPT", 1, 10, 1, disabled=not solar_active)
            voc = st.number_input("Panel Voc at STC (V)", 10.0, 100.0, 39.5, 0.1, disabled=not solar_active)
            vmp = st.number_input("Panel Vmp at STC (V)", 10.0, 100.0, 33.2, 0.1, disabled=not solar_active)
            isc = st.number_input("Panel Isc at STC (A)", 1.0, 30.0, 14.0, 0.1, disabled=not solar_active)
            imp = st.number_input("Panel Imp at STC (A)", 1.0, 30.0, 13.25, 0.1, disabled=not solar_active)
            voc_coeff = st.number_input("Voc temperature coefficient (%/°C)", -1.0, -0.01, -0.25, 0.01, disabled=not solar_active)
            min_temp = st.number_input("Design minimum temperature (°C)", -30.0, 10.0, -10.0, 1.0, disabled=not solar_active)
        with st.expander("3. PV inverter and MPPT", expanded=pv_inverter_active):
            inverter_kw = st.number_input("PV inverter rated AC output (kW)", 0.5, 50.0, 3.68, 0.1, disabled=not pv_inverter_active)
            max_dc_v = st.number_input("Absolute maximum DC voltage (V)", 50.0, 1500.0, 600.0, 10.0, disabled=not solar_active)
            mppt_min = st.number_input("MPPT minimum voltage (V)", 20.0, 1200.0, 120.0, 10.0, disabled=not solar_active)
            mppt_max = st.number_input("MPPT maximum operating voltage (V)", 50.0, 1500.0, 550.0, 10.0, disabled=not solar_active)
            max_imp = st.number_input("Maximum operating current/MPPT (A)", 1.0, 100.0, 25.0, 1.0, disabled=not solar_active)
            max_isc = st.number_input("Maximum short-circuit current/MPPT (A)", 1.0, 150.0, 32.0, 1.0, disabled=not solar_active)
        with st.expander("4. Battery and inverter/charger", expanded=battery_active):
            chemistry = st.selectbox("Battery chemistry", ["LFP", "NMC", "Lead-acid / AGM", "Other / manufacturer-defined"], disabled=not battery_active)
            st.caption("Chemistry is recorded for context; use the selected battery datasheet for usable capacity and current limits.")
            advanced_recommended_usable = (home_kwh + ev_miles / ev_efficiency / ev_charge_efficiency) * 0.6
            battery_nominal_capacity = persistent_number_input(
                "Installed battery capacity (kWh nominal)", 0.5, 200.0,
                round(advanced_recommended_usable / 0.9 * 2) / 2, 0.5,
                disabled=not battery_active, state_key="advanced_battery_nominal",
            )
            autonomy = st.slider("Battery coverage target (hours)", 1, 48, 12, disabled=not battery_active)
            usable = st.slider("Usable battery fraction (%)", 20, 100, 90, disabled=not battery_active) / 100
            st.caption(f"Usable capacity at the selected DoD: {battery_nominal_capacity * usable:.1f} kWh.")
            charge_efficiency = st.slider("AC-to-battery efficiency (%)", 70, 100, 95, disabled=not battery_active) / 100
            discharge_efficiency = st.slider("Battery-to-AC efficiency (%)", 70, 100, 94, disabled=not battery_active) / 100
            battery_v = st.number_input("Battery nominal voltage (V)", 12.0, 1000.0, 51.2, 1.0, disabled=not battery_active)
            battery_a = st.number_input("Battery/BMS continuous current (A)", 1.0, 1000.0, 100.0, 5.0, disabled=not battery_active)
            st.markdown("##### Battery inverter/charger")
            battery_inverter_rating_kw = persistent_number_input(
                "Battery inverter/charger rated power (kW)", 0.1, 100.0, 8.0, 0.1,
                disabled=not battery_inverter_active, state_key="advanced_battery_inverter_rating",
            )
            battery_charge_limit_kw = persistent_number_input("Inverter/charger AC charge limit (kW)", 0.1, 100.0, 5.0, 0.1,
                disabled=not battery_inverter_active, state_key="advanced_battery_charge_power")
            battery_discharge_limit_kw = persistent_number_input("Inverter/charger AC discharge limit (kW)", 0.1, 100.0, 8.0, 0.1,
                disabled=not battery_inverter_active, state_key="advanced_battery_discharge_power")
            advanced_allow_battery_export = st.checkbox(
                "Allow battery export to grid", value=False, disabled=not battery_active,
                key="advanced_allow_battery_export",
            )
            st.caption("Export of grid-charged energy is opt-in. Supplier/export-tariff eligibility and metering terms must be confirmed.")
        with st.expander("5. Grid, yield and economics", expanded=False):
            phases = st.selectbox("Grid phases", [1, 3], disabled=not inverter_charger_active)
            export_limited = st.checkbox("Export limitation scheme proposed", disabled=not inverter_charger_active)
            active_ac_limit_kw = inverter_kw if pv_inverter_active else min(
                battery_inverter_rating_kw, battery_discharge_limit_kw
            )
            export_limit_kw = st.number_input("Proposed export limit (kW)", 0.0, 50.0, 3.68, 0.1, disabled=not inverter_charger_active) if export_limited else active_ac_limit_kw
            specific_yield = st.number_input("Manual PVGIS yield override (kWh/kWp/year)", 300.0, 1400.0, 900.0, 10.0, disabled=not solar_active)
            pvgis_losses = st.slider("PVGIS system-loss assumption (%)", 0, 40, 14, disabled=not solar_active,
                help="Recorded with the manual yield assumption; do not deduct it again from a PVGIS AC-yield result.")
            advanced_import_tariff = st.number_input("Import tariff (p/kWh)", 0.1, 100.0, 25.0, 0.5)
            advanced_export_tariff = st.number_input("Export tariff (p/kWh)", 0.0, 100.0, 15.0, 0.5)
            if tariff_active:
                st.caption("Tariff optimisation selected: configure its off-peak assumptions below.")
                advanced_has_offpeak = True
            else:
                advanced_has_offpeak = st.checkbox("Model off-peak battery charging", key="advanced_has_offpeak")
            advanced_offpeak_tariff = st.number_input("Off-peak tariff (p/kWh)", 0.0, 100.0, 8.0, 0.5) if advanced_has_offpeak else None
            advanced_offpeak_window = st.number_input("Off-peak charging window (hours/day)", 0.5, 12.0, 4.0, 0.5) if advanced_has_offpeak else 0.0
            advanced_has_cost = st.checkbox("Include installed cost for payback")
            advanced_cost = st.number_input("Solar-only installed cost (£)", 100.0, 100000.0, 7000.0, 100.0, disabled=not solar_active) if advanced_has_cost else None
            advanced_battery_cost = st.number_input("Battery add-on cost (£)", 0.0, 50000.0, 5000.0, 100.0, disabled=not battery_active) if advanced_has_cost else None
        with st.expander("6. Project context", expanded=False):
            diy_context = st.checkbox(
                "I am sourcing specialist solar/electrical installation materials",
                help="Only use specialist tools and cable after a competent designer has specified the exact products and installation method.",
            )
    result = calculate_system(LoadInputs(home_kwh, ev_miles, ev_efficiency, ev_charge_efficiency),
        SolarInputs(panel_wp, series, parallel, voc, vmp, isc, imp, voc_coeff, min_temp, max_dc_v,
            mppt_min, mppt_max, max_imp, max_isc, inverter_kw, phases, specific_yield, pvgis_losses),
        BatteryInputs(autonomy, usable, discharge_efficiency, battery_v, battery_a,
                      battery_inverter_rating_kw))
    advanced_finance = calculate_consumer_result(household_kwh=home_kwh * 365, ev_miles_year=ev_miles * 365,
        ev_miles_per_kwh=ev_efficiency, ev_charge_efficiency=ev_charge_efficiency,
        specific_yield=specific_yield, panel_wp=panel_wp, max_panels=series * parallel,
        wants_battery=battery_active, import_tariff_p=advanced_import_tariff, export_tariff_p=advanced_export_tariff,
        offpeak_tariff_p=advanced_offpeak_tariff,
        installed_cost_gbp=(advanced_cost + advanced_battery_cost if advanced_cost is not None else None),
        forced_array_kwp=result.array_kwp)
    comparison_inputs = dict(
        annual_demand_kwh=advanced_finance.annual_demand_kwh,
        ev_demand_kwh=advanced_finance.ev_demand_kwh,
        solar_kwp=result.array_kwp,
        panels=series * parallel,
        specific_yield=specific_yield,
        import_tariff_p=advanced_import_tariff,
        export_tariff_p=advanced_export_tariff,
        offpeak_tariff_p=advanced_offpeak_tariff,
        solar_installed_cost_gbp=advanced_cost,
        battery_addon_cost_gbp=advanced_battery_cost,
        battery_usable_kwh=battery_nominal_capacity * usable,
        battery_charge_efficiency=charge_efficiency,
        battery_discharge_efficiency=discharge_efficiency,
        battery_charge_power_kw=min(battery_v * battery_a / 1000, battery_inverter_rating_kw, battery_charge_limit_kw),
        battery_discharge_power_kw=min(battery_v * battery_a / 1000, battery_inverter_rating_kw, battery_discharge_limit_kw),
        allow_battery_export=advanced_allow_battery_export,
        offpeak_window_hours=advanced_offpeak_window or 4.0,
    )
    comparison = compare_system_scenarios(**comparison_inputs)
    selected_scenario = next(item for item in comparison.scenarios if item.key == selected_key)

    with st.container(border=True):
        st.markdown("#### System overview")
        cols = st.columns(3)
        cols[0].metric("Selected array", f"{selected_scenario.solar_kwp:.2f} kWp", f"{selected_scenario.panels} panels" if selected_scenario.panels else "solar disabled")
        cols[1].metric("Annual generation", f"{selected_scenario.annual_generation_kwh:,.0f} kWh")
        cols[2].metric("Selected battery", f"{selected_scenario.battery_usable_kwh:.1f} kWh usable" if selected_scenario.battery_usable_kwh else "Battery disabled", chemistry if selected_scenario.battery_usable_kwh else None)
        capability_cols = st.columns(3)
        raw_battery_limit_kw = battery_v * battery_a / 1000
        battery_selected = selected_scenario.battery_usable_kwh > 0
        capability_cols[0].metric(
            "Battery charge capability",
            f"≤ {min(raw_battery_limit_kw, battery_inverter_rating_kw, battery_charge_limit_kw):.1f} kW" if battery_selected else "Not applicable",
        )
        capability_cols[1].metric(
            "Battery discharge capability",
            f"≤ {min(raw_battery_limit_kw, battery_inverter_rating_kw, battery_discharge_limit_kw):.1f} kW" if battery_selected else "Not applicable",
        )
        capability_cols[2].metric(
            "Battery/BMS raw limit",
            f"{raw_battery_limit_kw:.1f} kW" if battery_selected else "Not applicable",
            "before inverter/charger limits" if battery_selected else None,
        )
    with st.container(border=True):
        st.markdown("#### PV string and inverter checks")
        if selected_scenario.solar_kwp:
            check_cols = st.columns(4)
            check_cols[0].metric("Cold string Voc", f"{result.cold_string_voc:.0f} V")
            check_cols[1].metric("Nominal string Vmp", f"{result.string_vmp:.0f} V")
            check_cols[2].metric("Array Imp / Isc", f"{result.array_imp:.1f} / {result.array_isc:.1f} A")
            check_cols[3].metric("DC/AC ratio", f"{result.dc_ac_ratio:.2f}")
            for check in result.checks:
                {"pass": st.success, "warn": st.warning, "fail": st.error}[check.level](f"**{check.title}:** {check.detail}")
        else:
            st.info("Solar is disabled in the selected configuration, so PV string and PV inverter/MPPT checks are not applicable.")
    with st.container(border=True):
        st.markdown("#### Energy flow and economics")
        flow_cols = st.columns(4)
        flow_cols[0].metric("Estimated self-use", f"{selected_scenario.self_consumed_kwh:,.0f} kWh/year")
        flow_cols[1].metric("Peak-rate grid import", f"{selected_scenario.peak_rate_import_kwh:,.0f} kWh/year")
        flow_cols[2].metric("Estimated export", f"{selected_scenario.export_kwh:,.0f} kWh/year")
        flow_cols[3].metric("Estimated benefit", f"£{selected_scenario.annual_benefit_gbp:,.0f}/year")
        st.caption("Savings use the entered tariffs and an annual self-consumption heuristic; half-hourly modelling is required for a firm forecast.")
        st.write(f"Total grid import: **{selected_scenario.grid_import_kwh:,.0f} kWh/year**; estimated annual electricity cost after export: **£{selected_scenario.annual_electricity_cost_gbp:,.0f}**.")
        if selected_scenario.payback_years:
            st.metric("Simple payback", f"{selected_scenario.payback_years:.1f} years")
    with st.container(border=True):
        st.markdown("#### Grid and export route")
        if not selected_scenario.solar_kwp:
            st.write("No solar generating installation is included in the selected configuration.")
            if selected_scenario.battery_usable_kwh and advanced_allow_battery_export:
                st.info("Battery export is enabled as a modelling assumption. Confirm that the supplier/export contract accepts grid-charged battery exports; SEG eligibility is not automatic.")
            elif selected_scenario.battery_usable_kwh:
                st.caption("Battery export is disabled; the battery may charge off-peak for later household use, but modelled battery export remains zero.")
        elif export_limited:
            st.info(f"Proposed export limit: {export_limit_kw:.2f} kW. An export limitation scheme requires appropriate design/commissioning and does not automatically change the G98/G99 application route.")
        else:
            st.write("No export limitation scheme selected; assess the complete generating installation against the DNO connection route.")
    record_event(st.session_state.events, "calculator_completed")
    if ev_miles > 0:
        recommendation_contexts.add("ev")
    if diy_context:
        recommendation_contexts.add("diy")

    plan_inverter_low = result.array_kwp * 0.75
    plan_inverter_high = result.array_kwp

strongest = next(item for item in comparison.scenarios if item.key == comparison.strongest_key)

st.subheader("Compare system options")
st.success(f"Strongest financial result under these assumptions: **{strongest.title}** ({comparison.ranking_basis}).")
if comparison.battery_improves_economics:
    st.caption("Under these assumptions, adding storage improves the modelled financial result. This is not a recommendation without interval data and firm installed costs.")
else:
    st.warning("Under these assumptions, a battery does not improve the financial result versus solar only. Storage may still have non-financial value, but the calculator does not recommend it on economics alone.")
comparison_rows = []
for scenario in comparison.scenarios:
    scenario_prefix = ("✓ Selected " if scenario.key == selected_key else "") + ("★ " if scenario.key == comparison.strongest_key else "")
    comparison_rows.append({
        "Scenario": scenario_prefix + scenario.title,
        "Solar": f"{scenario.solar_kwp:.1f} kWp",
        "Battery": (f"{scenario.battery_usable_kwh:.1f} kWh usable" if scenario.battery_usable_kwh else "None"),
        "Generation": f"{scenario.annual_generation_kwh:,.0f} kWh",
        "Self-consumption": f"{scenario.self_consumption_pct:.0f}%",
        "Peak import": f"{scenario.peak_rate_import_kwh:,.0f} kWh",
        "Off-peak charge": f"{scenario.offpeak_import_kwh:,.0f} kWh",
        "Battery home use": f"{scenario.battery_discharge_kwh:,.0f} kWh",
        "Battery export": f"{scenario.battery_export_kwh:,.0f} kWh",
        "Battery losses": f"{scenario.battery_charge_loss_kwh + scenario.battery_discharge_loss_kwh:,.0f} kWh",
        "Total import": f"{scenario.grid_import_kwh:,.0f} kWh",
        "Export": f"{scenario.export_kwh:,.0f} kWh",
        "Annual electricity cost": f"£{scenario.annual_electricity_cost_gbp:,.0f}",
        "Annual benefit": f"£{scenario.annual_benefit_gbp:,.0f}",
        "Installed cost": (f"£{scenario.installed_cost_gbp:,.0f}" if scenario.installed_cost_gbp is not None else "Not supplied"),
        "Simple payback": (f"{scenario.payback_years:.1f} years" if scenario.payback_years is not None else "Not available"),
    })
st.dataframe(comparison_rows, hide_index=True, use_container_width=True)
if not comparison.tariff_optimisation_applicable:
    st.info(comparison.tariff_optimisation_reason)
    st.info("Battery only matches the grid baseline because no off-peak charging tariff is configured; an uncharged battery cannot shift grid import.")
else:
    battery_only_scenario = next(item for item in comparison.scenarios if item.key == "battery_only")
    if battery_only_scenario.grid_battery_charge_kwh == 0:
        st.info("Battery only matches the grid baseline because the configured off-peak price is not economical after battery losses, so no grid charging is scheduled.")
    tariff_scenario = next(item for item in comparison.scenarios if item.key == "tariff")
    if tariff_scenario.grid_battery_charge_kwh == 0:
        st.info("Tariff optimisation matches Solar + battery because the off-peak price is not cheaper after battery losses, so no grid charging is scheduled.")
st.caption("Comparison includes EV demand once and constrains battery charging by usable capacity, charge/discharge efficiency, battery power and the entered off-peak window. Solar shifting uses up to 250 equivalent cycles/year. This remains an annual screening model, not a half-hourly dispatch forecast.")

with st.expander("Optional half-hourly smart-meter CSV", expanded=False):
    st.write("Upload a CSV with `timestamp` and `consumption_kWh` columns. Octopus-style `Start` and `Consumption (kWh)` columns are also supported.")
    smart_meter_file = st.file_uploader("Half-hourly consumption CSV", type=["csv"])
    st.caption("The file is parsed locally in this Streamlit session and is not persisted or transmitted by this app.")
    if smart_meter_file is not None:
        try:
            meter_data = parse_smart_meter_csv(smart_meter_file.getvalue())
            st.success(f"Validated {len(meter_data.readings):,} consecutive half-hourly readings ({meter_data.total_kwh:,.1f} kWh) from {meter_data.start} to {meter_data.end}.")
            st.info("Interval battery dispatch is intentionally not enabled in this release. The comparison above continues to use the labelled annual timing heuristic until the dispatch model has dedicated validation.")
        except SmartMeterCSVError as exc:
            st.error(str(exc))

st.subheader("Your solar plan")
plan_text = "\n".join((
    "Your solar plan",
    f"Selected configuration: {selected_scenario.title}",
    f"Solar: {selected_scenario.solar_kwp:.1f} kWp (approximately {selected_scenario.panels} panels)" if selected_scenario.solar_kwp else "Solar: disabled",
    f"Inverter range: {plan_inverter_low:.1f}–{plan_inverter_high:.1f} kW" if selected_scenario.solar_kwp else "Solar inverter range: not applicable",
    f"Battery: {selected_scenario.battery_usable_kwh:.1f} kWh usable" if selected_scenario.battery_usable_kwh else "Battery: disabled",
    f"Annual generation: {selected_scenario.annual_generation_kwh:,.0f} kWh",
    f"Estimated annual financial benefit: £{selected_scenario.annual_benefit_gbp:,.0f}",
    f"Estimated simple payback: {selected_scenario.payback_years:.1f} years" if selected_scenario.payback_years is not None else "Estimated simple payback: add installed costs to calculate",
    "Early-stage estimate only; verify design, costs and permissions with competent professionals.",
))
with st.container(border=True):
    st.code(plan_text, language=None)
    st.caption("Use the copy control on the result card to share this text. No registration or external sharing service is used.")

st.divider()
st.subheader("Would a future installer quote service be useful?")
st.caption("We are assessing interest only. There is no installer matching service or installer connection yet, and this form sends and stores nothing.")
quote_open = st.checkbox("I'd like to register interest in a future quote service")
if quote_open:
    record_event(st.session_state.events, "quote_opened")
    st.info("This only validates the form on your device. It does not contact an installer or send us your details.")
    with st.form("quote_interest"):
        lead_name = st.text_input("Name")
        lead_email = st.text_input("Email")
        lead_district = st.text_input("Postcode district (optional)", placeholder="For example, SW1A")
        consent = st.checkbox("I consent to being contacted about a solar quote when this service is activated.")
        submitted = st.form_submit_button("Register interest")
    if submitted:
        lead = QuoteInterest(lead_name, lead_email, lead_district, consent)
        errors = validate_quote_interest(lead)
        if errors:
            st.error(" ".join(errors.values()))
        elif submit_quote_interest(lead):
            record_event(st.session_state.events, "quote_submitted")
            st.success("Validated. Nothing was stored or sent because the lead service is not yet enabled.")

st.subheader("Learn before you buy")
for guide_title, guide_body in BUYING_GUIDES.items():
    with st.expander(guide_title):
        st.markdown(guide_body)

page_products = affiliate_products_for_page(mode, recommendation_contexts)
with st.expander("Useful solar & EV products", expanded=False):
    for offer in page_products:
        st.markdown(f"**{offer.title}**")
        st.write(offer.description)
        st.markdown(f"[Check on Amazon UK →](?out={offer.product_id})")
    st.caption("Check product compatibility and installation requirements before buying. Electrical installation may require a qualified installer.")
    st.caption("As an Amazon Associate I earn from qualifying purchases. Affiliate links may earn us a commission at no extra cost to you.")

outbound_key = st.query_params.get("out")
enabled_by_key = {offer.product_id: offer for offer in page_products}
if outbound_key in enabled_by_key:
    record_event(st.session_state.events, "affiliate_clicked")
    outbound_offer = enabled_by_key[outbound_key]
    st.info("You are leaving this calculator for an Amazon UK product page. Check the listing and compatibility before buying.")
    st.link_button("Continue to Amazon UK", outbound_offer.url, type="primary")

with st.expander("Methodology, sources, privacy and disclosures"):
    st.markdown("""
- [PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/en/) supplies location, orientation and tilt-aware generation estimates; its output includes the configured system losses.
- [ENA connection guidance](https://www.energynetworks.org/industry/engineering-and-technical-programmes/connecting-to-the-networks) covers G98/G99 and type-tested equipment.
- [MCS consumer guidance](https://mcscertified.com/consumers-communities/) explains certified installation and consumer protection.
- [GOV.UK smart charge point rules](https://www.gov.uk/guidance/regulations-electric-vehicle-smart-charge-points) cover relevant domestic EV-charger requirements.
- [Energy Saving Trust battery guidance](https://energysavingtrust.org.uk/advice/battery-storage/) explains why storage size depends on how much electricity a home uses, when it uses it, available solar surplus and time-of-use charging.
- [GOV.UK Smart Export Guarantee guidance](https://www.gov.uk/government/publications/smart-export-guarantee-seg-earn-money-for-exporting-the-renewable-electricity-you-have-generated) and [Ofgem generator guidance](https://www.ofgem.gov.uk/environmental-and-social-schemes/smart-export-guarantee-seg/smart-export-guarantee-seg-generators) explain that storage may be eligible, but the chosen supplier sets its application, metering and payment terms.
- A postcode is sent to Postcodes.io for coordinates; coordinates and roof inputs are sent to the European Commission PVGIS service. Quote details are not persisted or transmitted.
- Privacy policy, cookie notice, terms and commercial disclosure require final owner/legal review before public deployment.
""")
    st.caption(f"Release: {APP_RELEASE}")
st.warning("Final electrical design, structural suitability, product compatibility, Building Regulations work, DNO approval and installation must be verified by competent professionals.")
