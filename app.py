import streamlit as st

from solar_sizer import BatteryInputs, LoadInputs, SolarInputs, calculate_system
from solar_sizer.affiliates import enabled_affiliate_offers

st.set_page_config(page_title="UK Solar & Battery Sizer", page_icon="☀️", layout="wide")
st.title("UK Solar & Battery System Sizer")
st.caption("Early-stage feasibility checks for UK homes — not an electrical design or permission to connect.")

with st.sidebar:
    st.header("Your home and EV")
    home_kwh = st.number_input("Home electricity use (kWh/day)", 1.0, 100.0, 10.0, 0.5)
    ev_miles = st.number_input("EV driving (miles/day)", 0.0, 300.0, 20.0, 1.0)
    ev_efficiency = st.number_input("EV efficiency (miles/kWh at battery)", 1.0, 6.0, 3.5, 0.1)
    ev_charge_efficiency = st.slider("EV charging efficiency", 70, 100, 90) / 100
    st.header("PV array")
    panel_wp = st.number_input("Panel power (Wp)", 200, 800, 440, 5)
    series = st.number_input("Panels in each series string", 1, 40, 10)
    parallel = st.number_input("Parallel strings on this MPPT", 1, 10, 1)
    with st.expander("Module electrical data"):
        voc = st.number_input("Voc at STC (V)", 10.0, 100.0, 39.5, 0.1)
        vmp = st.number_input("Vmp at STC (V)", 10.0, 100.0, 33.2, 0.1)
        isc = st.number_input("Isc at STC (A)", 1.0, 30.0, 14.0, 0.1)
        imp = st.number_input("Imp at STC (A)", 1.0, 30.0, 13.25, 0.1)
        voc_coeff = st.number_input("Voc temperature coefficient (%/°C)", -1.0, -0.01, -0.25, 0.01)
        min_temp = st.number_input("Site design minimum temperature (°C)", -30.0, 10.0, -10.0, 1.0)
    st.header("Inverter and grid")
    inverter_kw = st.number_input("Rated AC output (kW)", 0.5, 50.0, 3.68, 0.1)
    phases = st.selectbox("Grid connection", [1, 3], format_func=lambda n: "Single phase" if n == 1 else "Three phase")
    with st.expander("Inverter DC/MPPT limits"):
        max_dc_v = st.number_input("Absolute maximum DC voltage (V)", 50.0, 1500.0, 600.0, 10.0)
        mppt_min = st.number_input("MPPT minimum voltage (V)", 20.0, 1200.0, 120.0, 10.0)
        mppt_max = st.number_input("MPPT maximum voltage (V)", 50.0, 1500.0, 550.0, 10.0)
        max_imp = st.number_input("Maximum operating current per MPPT (A)", 1.0, 100.0, 25.0, 1.0)
        max_isc = st.number_input("Maximum short-circuit current per MPPT (A)", 1.0, 150.0, 32.0, 1.0)
    st.header("Yield and battery")
    specific_yield = st.number_input("PVGIS annual yield (kWh/kWp/year)", 300.0, 1400.0, 900.0, 10.0,
        help="Use PVGIS for the location, roof slope and orientation. Its result already includes the entered system loss.")
    losses = st.slider("PVGIS system-loss assumption (%)", 0, 40, 14,
        help="Recorded for your assumptions; do not deduct it again from the PVGIS AC-yield result.")
    autonomy = st.slider("Battery coverage target (hours of average demand)", 1, 48, 12)
    usable = st.slider("Usable battery fraction (%)", 20, 100, 90) / 100
    discharge_efficiency = st.slider("Battery-to-AC discharge efficiency (%)", 70, 100, 94) / 100
    battery_v = st.number_input("Battery nominal voltage (V)", 12.0, 1000.0, 51.2, 1.0)
    battery_a = st.number_input("Battery/BMS continuous current (A)", 1.0, 1000.0, 100.0, 5.0)
    battery_inverter_kw = st.number_input("Inverter battery power limit (kW)", 0.1, 100.0, 5.0, 0.1)

result = calculate_system(
    LoadInputs(home_kwh, ev_miles, ev_efficiency, ev_charge_efficiency),
    SolarInputs(panel_wp, series, parallel, voc, vmp, isc, imp, voc_coeff, min_temp, max_dc_v,
        mppt_min, mppt_max, max_imp, max_isc, inverter_kw, phases, specific_yield, losses),
    BatteryInputs(autonomy, usable, discharge_efficiency, battery_v, battery_a, battery_inverter_kw),
)

cols = st.columns(4)
cols[0].metric("Total demand", f"{result.total_load_kwh_day:.1f} kWh/day", f"EV {result.ev_kwh_day:.1f} kWh/day")
cols[1].metric("PV array", f"{result.array_kwp:.2f} kWp", f"{series * parallel} panels")
cols[2].metric("Indicative annual generation", f"{result.annual_generation_kwh:,.0f} kWh", f"avg {result.average_generation_kwh_day:.1f} kWh/day")
cols[3].metric("Indicative battery", f"{result.battery_nominal_kwh:.1f} kWh nominal", f"continuous ≤ {result.battery_continuous_kw:.1f} kW")
st.info("Annual averages do not prove winter self-sufficiency. Use PVGIS monthly/hourly output and half-hourly consumption before buying equipment.")
st.subheader("Engineering checks")
for check in result.checks:
    message = f"**{check.title}:** {check.detail}"
    {"pass": st.success, "warn": st.warning, "fail": st.error}[check.level](message)

with st.expander("What this battery estimate means"):
    st.write(f"It covers {autonomy} hours of average combined demand, allowing for {usable:.0%} usable capacity and {discharge_efficiency:.0%} battery-to-AC efficiency. It does not model peak loads, tariffs, backup circuits, seasonal generation or scheduling.")

st.subheader("Before you buy")
st.markdown("""
- Ask an MCS-certified installer/designer to confirm roof structure, shading, fire access, cable routes, isolation, earthing, protection, inverter compatibility and the DNO process.
- Verify module and inverter datasheets together. Never mate incompatible DC connectors or work on live PV strings; daylight PV cannot simply be switched off.
- A domestic EV charge point is a dedicated electrical installation. Choose a compliant smart charger with load management and solar-diversion support where useful.
""")
st.subheader("Independent tools and guidance")
st.markdown("""
- [PVGIS generation modelling](https://re.jrc.ec.europa.eu/pvg_tools/en/) — location, slope and orientation-based estimates.
- [ENA connection guidance](https://www.energynetworks.org/industry/engineering-and-technical-programmes/connecting-to-the-networks) — G98/G99 and equipment registers.
- [MCS consumer guidance](https://mcscertified.com/consumers-communities/) — certified installers and consumer standards.
- [GOV.UK smart charge point rules](https://www.gov.uk/guidance/regulations-electric-vehicle-smart-charge-points).
""")
st.subheader("Product links")
st.write("Commercial links never affect the calculator's engineering results or safety warnings.")
for offer in enabled_affiliate_offers():
    st.markdown(f"**{offer.title}** — {offer.description} [View products]({offer.url})")
st.caption("As an Amazon Associate I earn from qualifying purchases. Affiliate links may earn us a commission at no extra cost to you.")
st.caption("Planning aid only. Results are estimates, not a quotation, electrical design, Building Regulations sign-off, MCS certificate or DNO approval.")
