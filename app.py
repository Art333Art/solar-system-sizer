import streamlit as st

st.title("UK DIY Solar & Battery System Sizer")
st.write("Calculate your hybrid inverter limits, cold-weather string safety, and required battery storage for UK homes and garages.")

st.sidebar.header("1. System Inputs")
home_usage = st.sidebar.slider("Daily Home Usage (kWh)", min_value=5.0, max_value=30.0, value=10.0, step=0.5)
ev_commute = st.sidebar.slider("EV Commute / Daily Charging (kWh)", min_value=0.0, max_value=15.0, value=3.5, step=0.5)
panels_in_series = st.sidebar.slider("Panels in Series", min_value=4, max_value=14, value=8, step=1)
panel_voc = st.sidebar.slider("Panel Open Circuit Voltage (Voc)", min_value=30.0, max_value=50.0, value=37.0, step=0.5)
inverter_max_v = st.sidebar.number_input("Inverter Max MPPT Voltage (V)", value=450.0)

# Calculations
total_daily_load_wh = (home_usage + ev_commute) * 1000

# Battery Calculations (LFP vs NMC)
lfp_capacity_wh = total_daily_load_wh / (0.90 * 0.90)
lfp_capacity_kwh = lfp_capacity_wh / 1000

nmc_capacity_wh = total_daily_load_wh / (0.75 * 0.90)
nmc_capacity_kwh = nmc_capacity_wh / 1000

# Cold weather string voltage check (-10°C multiplier = 1.15)
cold_string_voc = (panels_in_series * panel_voc) * 1.15

st.subheader("2. Results & Safety Checks")

col1, col2 = st.columns(2)

with col1:
    st.metric("Total Daily Energy Required", f"{(total_daily_load_wh/1000):.2f} kWh")
    st.metric("Required New LFP Storage Capacity", f"{lfp_capacity_kwh:.2f} kWh")
    st.markdown("*Recommended for safety, longevity, and standard DIY builds.*")

with col2:
    st.metric("Daily Load + EV Factor", f"{home_usage + ev_commute:.2f} kWh/day")
    st.metric("Required Salvaged NMC Storage Capacity", f"{nmc_capacity_kwh:.2f} kWh")
    st.markdown("*Required physical capacity if sourcing packs from donor EVs due to stricter safe DoD limits.*")

st.divider()

st.subheader("3. Hardware & Grid Compliance")

# String Voltage Warning
if cold_string_voc > inverter_max_v:
    st.error(f"**DANGER / WARNING:** Cold weather string Voc is **{cold_string_voc:.1f}V**, which exceeds your inverter's max limit of **{inverter_max_v}V**. Reduce the number of panels in series to avoid destroying the charge controller.")
else:
    st.success(f"**String Voltage Safe:** Cold weather string Voc is **{cold_string_voc:.1f}V** (Within the {inverter_max_v}V inverter limit).")

# G98 Grid Check
st.info("**UK G98 Grid Regulation Note:** For a standard single-phase domestic supply, export limits up to 3.68kW (16A) fall under 'fit and inform'. Anything larger requires pre-approval (G99) from your DNO.")

st.divider()
st.subheader("Sourcing & Affiliate Recommendations")
st.markdown("* Ready to buy your gear? Check components via trusted UK suppliers like [Bimble Solar](https://www.bimblesolar.com) or source heavy-duty 16mm wiring and enclosures via [Amazon UK](https://www.amazon.co.uk).")
