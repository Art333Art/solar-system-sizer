import streamlit as st

from solar_sizer import BatteryInputs, LoadInputs, SolarInputs, calculate_system
from solar_sizer.affiliates import enabled_affiliate_offers
from solar_sizer.analytics import record_event
from solar_sizer.content import BUYING_GUIDES
from solar_sizer.consumer import calculate_consumer_result
from solar_sizer.leads import QuoteInterest, submit_quote_interest, validate_quote_interest
from solar_sizer.pvgis import SolarDataError, fallback_specific_yield, fetch_pvgis_yield, geocode_uk_postcode

APP_RELEASE = "conversion-ready-2026-08"

st.set_page_config(page_title="UK Solar Panel, Battery & EV Sizing Calculator", page_icon="☀️", layout="wide",
    menu_items={"About": "Independent UK solar, battery, inverter and EV feasibility calculator."})


@st.cache_data(ttl=86400, show_spinner=False)
def cached_location(postcode: str) -> tuple[float, float]:
    return geocode_uk_postcode(postcode)


@st.cache_data(ttl=86400, show_spinner=False)
def cached_yield(latitude: float, longitude: float, tilt: float, aspect: float):
    return fetch_pvgis_yield(latitude, longitude, tilt, aspect)


if "events" not in st.session_state:
    st.session_state.events = []
record_event(st.session_state.events, "calculator_started")

st.title("UK Solar & Battery System Sizer")
st.markdown("Estimate how many solar panels you may need, a sensible battery range, annual generation, grid import/export, savings and payback using local UK solar data.")
st.caption("Free independent early-stage estimate — not an installer quotation or final electrical design.")
mode = st.radio("Calculator mode", ["Simple", "Advanced"], horizontal=True,
                help="Simple uses homeowner-friendly assumptions. Advanced exposes datasheet and electrical limits.")
if mode == "Advanced":
    record_event(st.session_state.events, "advanced_opened")
recommendation_contexts = {"monitoring"}

if mode == "Simple":
    st.subheader("Tell us about your home")
    c1, c2 = st.columns(2)
    with c1:
        postcode = st.text_input("UK postcode", placeholder="For example, M1 1AE",
            help="Used to obtain coordinates, which are sent to PVGIS for the solar estimate.")
        usage_basis = st.radio("Electricity usage", ["Annual", "Daily"], horizontal=True)
        usage_value = st.number_input("Usage (kWh/year)" if usage_basis == "Annual" else "Usage (kWh/day)",
            1.0, 50000.0 if usage_basis == "Annual" else 150.0, 3000.0 if usage_basis == "Annual" else 8.2, 10.0 if usage_basis == "Annual" else 0.1)
        annual_home_kwh = usage_value if usage_basis == "Annual" else usage_value * 365
        import_tariff = st.number_input("Electricity import tariff (p/kWh)", 0.1, 100.0, 25.0, 0.5)
        export_tariff = st.number_input("Export tariff (p/kWh)", 0.0, 100.0, 15.0, 0.5)
        has_offpeak = st.checkbox("I have an off-peak import tariff")
        offpeak_tariff = st.number_input("Off-peak tariff (p/kWh)", 0.0, 100.0, 8.0, 0.5) if has_offpeak else None
    with c2:
        orientation_label = st.selectbox("Main roof orientation", ["South", "South-east", "South-west", "East", "West", "North-east", "North-west", "North"])
        aspect_map = {"South": 0, "South-east": -45, "South-west": 45, "East": -90, "West": 90,
                      "North-east": -135, "North-west": 135, "North": 180}
        roof_description = st.selectbox("Roof pitch", ["Typical pitched roof (~35°)", "Shallow pitch (~20°)", "Steep pitch (~50°)", "Flat roof (~10°)", "Enter angle"])
        tilt_map = {"Typical pitched roof (~35°)": 35, "Shallow pitch (~20°)": 20,
                    "Steep pitch (~50°)": 50, "Flat roof (~10°)": 10}
        tilt = st.number_input("Roof tilt from horizontal (degrees)", 0, 90, 35) if roof_description == "Enter angle" else tilt_map[roof_description]
        roof_basis = st.radio("Available roof space", ["Usable area", "Approximate panel count"], horizontal=True)
        if roof_basis == "Usable area":
            roof_area = st.number_input("Usable unshaded roof area (m²)", 2.0, 300.0, 30.0, 1.0)
            max_panels = max(1, int(roof_area / 2.0))
            st.caption(f"Assuming about 2 m² per panel: space for roughly {max_panels} panels.")
        else:
            max_panels = st.number_input("Approximate maximum panel count", 1, 100, 12)
        ev_miles_week = st.number_input("EV driving (miles/week)", 0.0, 2000.0, 0.0, 10.0)
        wants_battery = st.checkbox("Include battery storage")
        knows_cost = st.checkbox("I have an estimated installed cost")
        installed_cost = st.number_input("Estimated installed cost (£)", 100.0, 100000.0, 9000.0, 100.0) if knows_cost else None

    aspect = aspect_map[orientation_label]
    yield_source = "Conservative UK fallback"
    specific_yield = fallback_specific_yield(aspect, tilt)
    if postcode.strip():
        try:
            with st.spinner("Checking local solar resource with PVGIS…"):
                lat, lon = cached_location(postcode)
                pvgis = cached_yield(lat, lon, float(tilt), float(aspect))
            specific_yield = pvgis.specific_yield_kwh_kwp
            yield_source = f"PVGIS 5.3 ({specific_yield:.0f} kWh/kWp/year)"
        except SolarDataError as exc:
            st.warning(f"{exc}. Using a conservative UK fallback; try again before making a purchase decision.")
    else:
        st.info("Enter a complete postcode for an automatic location-specific PVGIS estimate. A conservative placeholder is shown meanwhile.")

    consumer = calculate_consumer_result(household_kwh=annual_home_kwh, ev_miles_year=ev_miles_week * 52,
        ev_miles_per_kwh=3.5, ev_charge_efficiency=0.90, specific_yield=specific_yield, panel_wp=440,
        max_panels=int(max_panels), wants_battery=wants_battery, import_tariff_p=import_tariff,
        export_tariff_p=export_tariff, offpeak_tariff_p=offpeak_tariff, installed_cost_gbp=installed_cost)
    record_event(st.session_state.events, "calculator_completed")
    if ev_miles_week > 0:
        recommendation_contexts.add("ev")

    st.subheader("Your headline estimate")
    r1, r2, r3 = st.columns(3)
    r1.metric("Recommended solar array", f"{consumer.array_kwp:.1f} kWp", f"about {consumer.panels} × 440 W panels")
    r2.metric("Estimated annual generation", f"{consumer.annual_generation_kwh:,.0f} kWh/year")
    r3.metric("Estimated annual saving", f"£{consumer.annual_saving_gbp:,.0f}")
    r4, r5, r6 = st.columns(3)
    r4.metric("Suggested battery", f"{consumer.battery_low_kwh:.1f}–{consumer.battery_high_kwh:.1f} kWh" if wants_battery else "No battery selected")
    r5.metric("Simple payback", f"{consumer.payback_years:.1f} years" if consumer.payback_years else "Add installed cost")
    r6.metric("Suggested inverter range", f"{consumer.inverter_low_kw:.1f}–{consumer.inverter_high_kw:.1f} kW")
    st.caption("Annual saving is based on your entered tariffs and the assumptions described below; it is not a guaranteed bill reduction.")

    with st.expander("Energy and bill breakdown", expanded=True):
        rows = {
            "Annual demand (including EV)": f"{consumer.annual_demand_kwh:,.0f} kWh",
            "EV demand": f"{consumer.ev_demand_kwh:,.0f} kWh",
            "Solar used in the home": f"{consumer.self_consumed_kwh:,.0f} kWh ({consumer.self_consumption_pct:.0f}% of generation)",
            "Grid import after solar": f"{consumer.grid_import_kwh:,.0f} kWh",
            "Solar export": f"{consumer.export_kwh:,.0f} kWh",
            "Off-peak battery charging": f"{consumer.offpeak_charge_kwh:,.0f} kWh" if consumer.offpeak_charge_kwh else "Not modelled",
            "Import cost before solar": f"£{consumer.before_cost_gbp:,.0f}/year",
            "Value of self-consumed solar": f"£{consumer.self_consumed_value_gbp:,.0f}/year",
            "Export income": f"£{consumer.export_income_gbp:,.0f}/year",
            "Import cost after solar/tariff shifting": f"£{consumer.after_import_cost_gbp:,.0f}/year",
            "Net annual cost after export income": f"£{consumer.after_net_cost_gbp:,.0f}/year",
        }
        for label, value in rows.items():
            st.write(f"**{label}:** {value}")
        st.caption(f"Solar source: {yield_source}. Values are rounded screening estimates, not tariff or performance guarantees.")

    with st.expander("Assumptions and technical next steps"):
        st.markdown("""
- Array size aims to cover annual household and EV demand, limited by the roof-space answer.
- A 440 W, roughly 2 m² panel is assumed. Actual panel dimensions and roof exclusion zones vary.
- Self-consumption uses an annual heuristic (higher with a battery); half-hourly load and PV simulation is required for a firm forecast.
- Off-peak modelling assumes some remaining import can be shifted through a battery at 90% delivery efficiency. It does not assume battery export income.
- The inverter range is an initial DC/AC screening range. Equipment, phases, DNO route, clipping and backup loads require a competent designer.
""")
else:
    recommendation_contexts.update({"advanced", "diy"})
    st.subheader("Advanced technical controls")
    with st.sidebar:
        home_kwh = st.number_input("Home electricity use (kWh/day)", 1.0, 100.0, 10.0, 0.5)
        ev_miles = st.number_input("EV driving (miles/day)", 0.0, 300.0, 20.0, 1.0)
        ev_efficiency = st.number_input("EV efficiency (miles/kWh)", 1.0, 6.0, 3.5, 0.1)
        ev_charge_efficiency = st.slider("EV charging efficiency", 70, 100, 90) / 100
        panel_wp = st.number_input("Panel power (Wp)", 200, 800, 440, 5)
        series = st.number_input("Panels per series string", 1, 40, 10)
        parallel = st.number_input("Parallel strings on this MPPT", 1, 10, 1)
        voc = st.number_input("Panel Voc at STC (V)", 10.0, 100.0, 39.5, 0.1)
        vmp = st.number_input("Panel Vmp at STC (V)", 10.0, 100.0, 33.2, 0.1)
        isc = st.number_input("Panel Isc at STC (A)", 1.0, 30.0, 14.0, 0.1)
        imp = st.number_input("Panel Imp at STC (A)", 1.0, 30.0, 13.25, 0.1)
        voc_coeff = st.number_input("Voc temperature coefficient (%/°C)", -1.0, -0.01, -0.25, 0.01)
        min_temp = st.number_input("Design minimum temperature (°C)", -30.0, 10.0, -10.0, 1.0)
        inverter_kw = st.number_input("Rated AC output (kW)", 0.5, 50.0, 3.68, 0.1)
        phases = st.selectbox("Grid phases", [1, 3])
        max_dc_v = st.number_input("Absolute maximum DC voltage (V)", 50.0, 1500.0, 600.0, 10.0)
        mppt_min = st.number_input("MPPT minimum voltage (V)", 20.0, 1200.0, 120.0, 10.0)
        mppt_max = st.number_input("MPPT maximum voltage (V)", 50.0, 1500.0, 550.0, 10.0)
        max_imp = st.number_input("Maximum operating current/MPPT (A)", 1.0, 100.0, 25.0, 1.0)
        max_isc = st.number_input("Maximum short-circuit current/MPPT (A)", 1.0, 150.0, 32.0, 1.0)
        specific_yield = st.number_input("Manual PVGIS yield override (kWh/kWp/year)", 300.0, 1400.0, 900.0, 10.0)
        pvgis_losses = st.slider("PVGIS system-loss assumption (%)", 0, 40, 14,
            help="Recorded with the manual yield assumption; do not deduct it again from a PVGIS AC-yield result.")
        autonomy = st.slider("Battery coverage target (hours)", 1, 48, 12)
        usable = st.slider("Usable battery fraction (%)", 20, 100, 90) / 100
        discharge_efficiency = st.slider("Battery-to-AC efficiency (%)", 70, 100, 94) / 100
        battery_v = st.number_input("Battery nominal voltage (V)", 12.0, 1000.0, 51.2, 1.0)
        battery_a = st.number_input("Battery/BMS continuous current (A)", 1.0, 1000.0, 100.0, 5.0)
        battery_inverter_kw = st.number_input("Inverter battery power limit (kW)", 0.1, 100.0, 5.0, 0.1)
    result = calculate_system(LoadInputs(home_kwh, ev_miles, ev_efficiency, ev_charge_efficiency),
        SolarInputs(panel_wp, series, parallel, voc, vmp, isc, imp, voc_coeff, min_temp, max_dc_v,
            mppt_min, mppt_max, max_imp, max_isc, inverter_kw, phases, specific_yield, pvgis_losses),
        BatteryInputs(autonomy, usable, discharge_efficiency, battery_v, battery_a, battery_inverter_kw))
    cols = st.columns(4)
    cols[0].metric("Demand", f"{result.total_load_kwh_day:.1f} kWh/day")
    cols[1].metric("PV array", f"{result.array_kwp:.2f} kWp")
    cols[2].metric("Annual generation", f"{result.annual_generation_kwh:,.0f} kWh")
    cols[3].metric("Battery", f"{result.battery_nominal_kwh:.1f} kWh nominal")
    with st.expander("Engineering checks", expanded=True):
        for check in result.checks:
            {"pass": st.success, "warn": st.warning, "fail": st.error}[check.level](f"**{check.title}:** {check.detail}")
    record_event(st.session_state.events, "calculator_completed")
    if ev_miles > 0:
        recommendation_contexts.add("ev")

st.divider()
st.subheader("Interested in an installer quote?")
st.caption("No installer is connected yet. This interest form currently sends and stores nothing.")
quote_open = st.checkbox("I'm interested in a future installer quote")
if quote_open:
    record_event(st.session_state.events, "quote_opened")
    st.info("No installer partnership is claimed. This demo validates your interest but currently stores or sends nothing.")
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

recommended_offers = enabled_affiliate_offers(recommendation_contexts)
if recommended_offers:
    st.subheader("Relevant product links")
    st.write("Commercial links do not influence system sizing, compatibility checks or safety warnings.")
    for offer in recommended_offers:
        with st.expander(offer.title):
            st.warning(offer.description)
            st.markdown(f"[Open tracked Amazon UK listing](?out={offer.key})")
    st.caption("As an Amazon Associate I earn from qualifying purchases. Affiliate links may earn us a commission at no extra cost to you.")

outbound_key = st.query_params.get("out")
enabled_by_key = {offer.key: offer for offer in recommended_offers}
if outbound_key in enabled_by_key:
    record_event(st.session_state.events, "affiliate_clicked")
    outbound_offer = enabled_by_key[outbound_key]
    st.info("Outbound Amazon click recorded anonymously in this session. No postcode, calculation or personal data was attached.")
    st.link_button("Continue to Amazon UK", outbound_offer.url, type="primary")

with st.expander("Methodology, sources, privacy and disclosures"):
    st.markdown("""
- [PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/en/) supplies location, orientation and tilt-aware generation estimates; its output includes the configured system losses.
- [ENA connection guidance](https://www.energynetworks.org/industry/engineering-and-technical-programmes/connecting-to-the-networks) covers G98/G99 and type-tested equipment.
- [MCS consumer guidance](https://mcscertified.com/consumers-communities/) explains certified installation and consumer protection.
- [GOV.UK smart charge point rules](https://www.gov.uk/guidance/regulations-electric-vehicle-smart-charge-points) cover relevant domestic EV-charger requirements.
- A postcode is sent to Postcodes.io for coordinates; coordinates and roof inputs are sent to the European Commission PVGIS service. Quote details are not persisted or transmitted. Anonymous events contain only an event name and time in this browser session.
- Privacy policy, cookie notice, terms and commercial disclosure require final owner/legal review before public deployment.
""")
    st.caption(f"Release: {APP_RELEASE}")
st.warning("Final electrical design, structural suitability, product compatibility, Building Regulations work, DNO approval and installation must be verified by competent professionals.")
