import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="UK DIY Solar & Battery System Sizer",
    page_icon="⚡",
    layout="wide"
)

# App Title & Header
st.title("UK DIY Solar & Battery System Sizer")
st.markdown("Your all-in-one calculator for UK hybrid inverter limits, cold-weather string safety, seasonal solar yields, and custom battery storage sizing.")

# Sidebar Inputs
st.sidebar.header("1. System & Load Inputs")
daily_usage = st.sidebar.slider("Daily Home Usage (kWh)", 5.0, 30.0, 10.0, 0.5)
ev_commute = st.sidebar.slider("EV Commute / Daily Charging (kWh)", 0.0, 30.0, 3.5, 0.5)
panel_wattage_wp = st.sidebar.slider("Individual Panel Rating (Wp)", 300, 550, 400, 10)
panels_in_series = st.sidebar.slider("Panels in Series", 4, 24, 10, 1)
voc = st.sidebar.slider("Panel Open Circuit Voltage (Voc)", 30.0, 60.0, 37.0, 0.5)
isc = st.sidebar.slider("Panel Short Circuit Current (Isc)", 9.0, 15.0, 13.5, 0.1, help="Max panel current for cable & breaker sizing.")
inverter_max_mppt = st.sidebar.number_input("Inverter Max MPPT Voltage (V)", value=600.0, step=25.0, min_value=100.0, max_value=1000.0)

st.sidebar.markdown("---")
st.sidebar.header("2. Battery Chemistry & Storage")
battery_chemistry = st.sidebar.selectbox(
    "Primary Battery Chemistry / Type",
    [
        "New LFP (Lithium Iron Phosphate - 80% Safe DoD)",
        "Second-Life / Salvaged LFP (75% Safe DoD)",
        "NMC / High-Voltage EV Packs (65% Safe DoD)",
        "Lead-Acid / AGM (50% Safe DoD - Deep Cycle Limit)"
    ]
)

st.sidebar.markdown("---")
st.sidebar.header("3. Grid & Export Specs")
inverter_output_kw = st.sidebar.number_input("Inverter Max AC Output / Export Rating (kW)", value=3.68, step=0.25, min_value=1.0, max_value=15.0, help="Rated continuous AC output power for G98/G99 compliance checks.")

# Calculations
total_daily_energy = daily_usage + ev_commute

# Assign DoD factor based on user selection
if "New LFP" in battery_chemistry:
    dod_factor = 1.25  # 80% usable DoD
    chem_label = "New LFP Storage Capacity"
    chem_help = "Calculated using an 80% safe Depth of Discharge (DoD) for standard DIY rack builds."
elif "Second-Life" in battery_chemistry:
    dod_factor = 1.33  # ~75% usable DoD
    chem_label = "Second-Life LFP Storage Capacity"
    chem_help = "Calculated using a conservative 75% safe DoD for second-life modules."
elif "NMC" in battery_chemistry:
    dod_factor = 1.54  # ~65% usable DoD
    chem_label = "NMC / EV Pack Storage Capacity"
    chem_help = "Calculated using a stricter 65% safe DoD to protect cell health on salvaged or high-voltage packs."
else:
    dod_factor = 2.00  # 50% usable DoD for Lead-Acid
    chem_label = "Lead-Acid / AGM Storage Capacity"
    chem_help = "Calculated using a strict 50% safe DoD to prevent sulfation."

required_storage = total_daily_energy * dod_factor

# Array sizing & Seasonal estimates
total_array_kwp = (panel_wattage_wp * panels_in_series) / 1000.0
estimated_summer_daily = (total_array_kwp * 3.8)  # ~3.8 peak sun hours equivalent in summer
estimated_winter_daily = (total_array_kwp * 0.9)  # ~0.9 equivalent in deep winter

# Cold weather string voltage check (assuming ~ -15°C winter factor adding ~15% to Voc)
cold_voc = panels_in_series * voc * 1.15

# Results Section
st.markdown("---")
st.subheader("2. Results & Custom Storage Sizing")

col1, col2 = st.columns(2)
with col1:
    st.metric("Total Daily Energy Required", f"{total_daily_energy:.2f} kWh")
    st.metric(f"Required {chem_label}", f"{required_storage:.2f} kWh", help=chem_help)
with col2:
    st.metric("Total Array Peak Power", f"{total_array_kwp:.2f} kWp", 
              help="Combined peak DC rating based on panels in series.")
    st.metric("Selected Battery Profile", battery_chemistry.split(" - ")[0], 
              help="Active chemistry profile governing depth-of-discharge safety margin.")

# Seasonal Reality Check Section
st.markdown("---")
st.subheader("3. Seasonal Solar Yield Reality Check (UK)")
st.markdown("Due to short winter days and cloud cover, generation swings dramatically across the year:")

season_col1, season_col2 = st.columns(2)
with season_col1:
    st.info(f"☀️ **Estimated Summer Daily Generation (~June)**: ~**{estimated_summer_daily:.1f} kWh / day**\n\n*Abundant generation; highly likely to fill your battery and export surplus.*")
with season_col2:
    st.warning(f"❄️ **Estimated Winter Daily Generation (~December)**: ~**{estimated_winter_daily:.1f} kWh / day**\n\n*Heavy drop-off. Your battery will likely need cheap off-peak grid top-ups rather than solar charging alone.*")

st.markdown("---")
st.subheader("4. Hardware & Grid Compliance")

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

# Balance of System Quick Guide
st.markdown("---")
st.subheader("5. Balance of System (BoS) Specs")
st.info(f"💡 **DC String Short-Circuit Current ($I_{sc}$)**: ~**{isc} A**. Ensure your DC isolators, breakers, and solar cables (recommended minimum $6\text{mm}^2$ for runs under 20m) are rated to handle this current with a 1.25x safety margin.")

# --- AFFILIATE RECOMMENDATION SECTION ---
st.markdown("---")
st.subheader("6. Recommended UK DIY Hardware & Components")
st.markdown("Get your approved components and hardware from trusted UK suppliers:")

aff_col1, aff_col2, aff_col3 = st.columns(3)

with aff_col1:
    st.markdown("### Hybrid Inverters")
    st.markdown("Compatible with high-voltage strings, 48V/HV batteries, and G98 compliance limits.")
    st.markdown("[Shop Bimble Solar Inverters](https://www.bimblesolar.com/) *(Affiliate link)*")

with aff_col2:
    st.markdown("### Battery Storage Kits")
    st.markdown("Modular lithium iron phosphate rack batteries and DIY cells.")
    st.markdown("[Browse Second Life / New LFP Kits](https://www.bimblesolar.com/) *(Affiliate link)*")

with aff_col3:
    st.markdown("### Balance of System")
    st.markdown("16mm armoured cable, DC breakers, and consumer units.")
    st.markdown("[Check Amazon UK Electricals](https://link.amazon/B05z6RNmr) *(Affiliate link)*")
