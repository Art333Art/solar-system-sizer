import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="UK DIY Solar & Battery System Sizer",
    page_icon="⚡",
    layout="wide"
)

# App Title & Header
st.title("UK DIY Solar & Battery System Sizer")
st.markdown("Your all-in-one calculator for UK hybrid inverter limits, string voltage/current safety, seasonal solar yields, and custom battery storage sizing.")

# Sidebar Inputs
st.sidebar.header("1. System & Load Inputs")
daily_usage = st.sidebar.slider("Daily Home Usage (kWh)", 5.0, 30.0, 10.0, 0.5)
ev_commute = st.sidebar.slider("EV Commute / Daily Charging (kWh)", 0.0, 30.0, 3.5, 0.5)

st.sidebar.markdown("---")
st.sidebar.subheader("Solar Array Configuration")
panel_wattage_wp = st.sidebar.slider("Individual Panel Rating (Wp)", 300, 550, 400, 10)
panels_in_series = st.sidebar.slider("Panels in Series (Per String)", 4, 24, 10, 1)
strings_in_parallel = st.sidebar.slider("Strings in Parallel", 1, 4, 1, 1, help="Number of parallel strings connected to the MPPT input.")
voc = st.sidebar.slider("Panel Open Circuit Voltage (Voc)", 30.0, 60.0, 37.0, 0.5)
isc = st.sidebar.slider("Panel Short Circuit Current (Isc)", 9.0, 15.0, 13.5, 0.1, help="Max panel current before parallel multiplication.")

inverter_max_mppt_v = st.sidebar.number_input("Inverter Max MPPT Voltage (V)", value=600.0, step=25.0, min_value=100.0, max_value=1000.0)
inverter_max_mppt_a = st.sidebar.number_input("Inverter Max MPPT Current (A)", value=25.0, step=5.0, min_value=10.0, max_value=60.0, help="Max DC current rating per MPPT input.")

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

# Battery DoD sizing factor
if "New LFP" in battery_chemistry:
    dod_factor = 1.25
    chem_label = "New LFP Storage Capacity"
    chem_help = "Calculated using an 80% safe Depth of Discharge (DoD)."
elif "Second-Life" in battery_chemistry:
    dod_factor = 1.33
    chem_label = "Second-Life LFP Storage Capacity"
    chem_help = "Calculated using a 75% safe DoD."
elif "NMC" in battery_chemistry:
    dod_factor = 1.54
    chem_label = "NMC / EV Pack Storage Capacity"
    chem_help = "Calculated using a 65% safe DoD."
else:
    dod_factor = 2.00
    chem_label = "Lead-Acid / AGM Storage Capacity"
    chem_help = "Calculated using a 50% safe DoD."

required_storage = total_daily_energy * dod_factor

# Array Sizing & Current Multipliers for Parallel Strings
total_panels = panels_in_series * strings_in_parallel
total_array_kwp = (panel_wattage_wp * total_panels) / 1000.0
total_string_isc = isc * strings_in_parallel  # Parallel strings sum current!

# Seasonal Estimates
estimated_summer_daily = (total_array_kwp * 3.8)
estimated_winter_daily = (total_array_kwp * 0.9)

# Cold weather voltage check (Voc increases in cold weather, ~15% safety buffer)
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
              help=f"Based on {total_panels} total panels ({panels_in_series} in series × {strings_in_parallel} in parallel).")
    st.metric("Selected Battery Profile", battery_chemistry.split(" - ")[0])

# Seasonal Reality Check Section
st.markdown("---")
st.subheader("3. Seasonal Solar Yield Reality Check (UK)")
season_col1, season_col2 = st.columns(2)
with season_col1:
    st.info(f"☀️ **Estimated Summer Daily Generation (~June)**: ~**{estimated_summer_daily:.1f} kWh / day**\n\n*Abundant generation; highly likely to fill your battery and export surplus.*")
with season_col2:
    st.warning(f"❄️ **Estimated Winter Daily Generation (~December)**: ~**{estimated_winter_daily:.1f} kWh / day**\n\n*Heavy drop-off. Your battery will likely need cheap off-peak grid top-ups.*")

st.markdown("---")
st.subheader("4. Hardware & Grid Compliance")

# Voltage & Current Safety Checks
if cold_voc <= inverter_max_mppt_v:
    st.success(f"✅ **String Voltage Safe**: Cold weather string Voc is {cold_voc:.1f}V (Within the {inverter_max_mppt_v:.1f}V inverter limit).")
else:
    st.error(f"⚠️ **DANGER**: Cold weather string Voc is {cold_voc:.1f}V, exceeding the {inverter_max_mppt_v:.1f}V limit! Reduce panels in series.")

if total_string_isc <= inverter_max_mppt_a:
    st.success(f"✅ **Array Current Safe**: Total parallel short-circuit current is {total_string_isc:.1f}A (Within the {inverter_max_mppt_a:.1f}A MPPT limit).")
else:
    st.error(f"⚠️ **DANGER**: Total parallel current ({total_string_isc:.1f}A) exceeds the inverter MPPT current limit ({inverter_max_mppt_a:.1f}A)! Reduce parallel strings or use a dual-MPPT input setup.")

# Dynamic G98 vs G99 Compliance Status
if inverter_output_kw <= 3.68:
    st.success(f"✅ **G98 Eligible ({inverter_output_kw} kW AC)**: Standard UK single-phase 'Fit & Inform' rules apply. No prior DNO approval needed.")
else:
    st.warning(f"⚠️ **G99 Approval Required ({inverter_output_kw} kW AC)**: Exceeds the standard 3.68kW single-phase limit. DNO approval required *before* commissioning.")

# Balance of System Quick Guide
st.markdown("---")
st.subheader("5. Balance of System (BoS) Specs")
st.info(f"💡 **Combined Parallel DC Current ($I_{sc}$)**: ~**{total_string_isc:.1f} A**. Ensure proper DC fusing/combiner boxes are used if combining more than 2 parallel strings, and use appropriately sized DC solar cables (min $6\text{mm}^2$).")

# --- AFFILIATE RECOMMENDATION SECTION ---
st.markdown("---")
st.subheader("6. Recommended UK DIY Hardware & Components")
aff_col1, aff_col2, aff_col3 = st.columns(3)

with aff_col1:
    st.markdown("### Hybrid Inverters")
    st.markdown("Compatible with high-voltage strings, dual MPPTs, and G98 limits.")
    st.markdown("[Shop Bimble Solar Inverters](https://www.bimblesolar.com/) *(Affiliate link)*")

with aff_col2:
    st.markdown("### Battery Storage Kits")
    st.markdown("Modular lithium iron phosphate rack batteries and DIY cells.")
    st.markdown("[Browse Second Life / New LFP Kits](https://www.bimblesolar.com/) *(Affiliate link)*")

with aff_col3:
    st.markdown("### Balance of System")
    st.markdown("Combiner boxes, DC breakers, and 16mm armoured cable.")
    st.markdown("[Check Amazon UK Electricals](https://link.amazon/B05z6RNmr) *(Affiliate link)*")
