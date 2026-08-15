import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="UK DIY Solar & Battery System Sizer",
    page_icon="⚡",
    layout="wide"
)

# App Title & Header
st.title("UK DIY Solar & Battery System Sizer")
st.markdown("Calculate your hybrid inverter limits, cold-weather string safety, and required battery storage for UK homes and garages.")

# Sidebar Inputs
st.sidebar.header("1. System Inputs")
daily_usage = st.sidebar.slider("Daily Home Usage (kWh)", 5.0, 30.0, 10.0, 0.5)
ev_commute = st.sidebar.slider("EV Commute / Daily Charging (kWh)", 0.0, 30.0, 3.5, 0.5)
panels_in_series = st.sidebar.slider("Panels in Series", 4, 24, 10, 1)
voc = st.sidebar.slider("Panel Open Circuit Voltage (Voc)", 30.0, 60.0, 37.0, 0.5)
inverter_max_mppt = st.sidebar.number_input("Inverter Max MPPT Voltage (V)", value=600.0, step=25.0, min_value=100.0, max_value=1000.0)

st.sidebar.markdown("---")
st.sidebar.header("2. Grid & Export Specs")
inverter_output_kw = st.sidebar.number_input("Inverter Max AC Output / Export Rating (kW)", value=3.68, step=0.25, min_value=1.0, max_value=15.0, help="Rated continuous AC output power for G98/G99 compliance checks.")

# Calculations
total_daily_energy = daily_usage + ev_commute
required_lfp = total_daily_energy * 1.25  # Safe DoD for longevity
required_nmc = total_daily_energy * 1.50  # Stricter safe DoD for salvaged packs

# Cold weather string voltage check (assuming ~ -15°C winter factor adding ~15% to Voc)
cold_voc = panels_in_series * voc * 1.15

# Results Section
st.markdown("---")
st.subheader("2. Results & Safety Checks")

col1, col2 = st.columns(2)
with col1:
    st.metric("Total Daily Energy Required", f"{total_daily_energy:.2f} kWh")
    st.metric("Required New LFP Storage Capacity", f"{required_lfp:.2f} kWh", 
              help="Recommended for safety, longevity, and standard DIY builds.")
with col2:
    st.metric("Daily Load + EV Factor", f"{total_daily_energy:.2f} kWh/day")
    st.metric("Required Salvaged NMC Storage Capacity", f"{required_nmc:.2f} kWh", 
              help="Required physical capacity if sourcing packs from donor EVs due to stricter safe DoD limits.")

st.markdown("---")
st.subheader("3. Hardware & Grid Compliance")

# Safety checks display
if cold_voc <= inverter_max_mppt:
    st.success(f"String Voltage Safe: Cold weather string Voc is {cold_voc:.1f}V (Within the {inverter_max_mppt:.1f}V inverter limit).")
else:
    st.error(f"⚠️ DANGER: Cold weather string Voc is {cold_voc:.1f}V, exceeding the {inverter_max_mppt:.1f}V inverter limit! Reduce panels in series.")

# Dynamic G98 vs G99 Compliance Status
if inverter_output_kw <= 3.68:
    st.success(f"✅ **G98 Eligible ({inverter_output_kw} kW AC)**: Falls under standard UK single-phase 'Fit & Inform' rules. No prior DNO approval needed (notify within 28 days of commissioning).")
else:
    st.warning(f"⚠️ **G99 Approval Required ({inverter_output_kw} kW AC)**: Exceeds the standard 3.68kW (16A) single-phase limit. You must submit a G99 application to your DNO and receive approval *before* connecting/exporting.")

# --- AFFILIATE RECOMMENDATION SECTION ---
st.markdown("---")
st.subheader("4. Recommended UK DIY Hardware & Components")
st.markdown("Get your approved components and hardware from trusted UK suppliers:")

aff_col1, aff_col2, aff_col3 = st.columns(3)

with aff_col1:
    st.markdown("### Hybrid Inverters")
    st.markdown("Compatible with high-voltage strings, 48V/HV batteries, and G98 compliance limits.")
    st.markdown("[Shop Bimble Solar Inverters](https://www.bimblesolar.com/) "
                "*(Affiliate link)*")

with aff_col2:
    st.markdown("### LFP Battery Storage")
    st.markdown("Modular lithium iron phosphate rack batteries and DIY cells.")
    st.markdown("[Browse Second Life / New LFP Kits](https://www.bimblesolar.com/) "
                "*(Affiliate link)*")

with aff_col3:
    st.markdown("### Balance of System")
    st.markdown("16mm armoured cable, DC breakers, and consumer units.")
    st.markdown("[Check Amazon UK Electricals](https://link.amazon/B05z6RNmr) *(Affiliate link)*")
