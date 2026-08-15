# UK Solar System Sizer

A consumer-first Streamlit feasibility calculator for UK domestic solar PV, batteries, inverters and EV demand. Simple mode uses cached postcode and PVGIS data; Advanced mode retains datasheet, MPPT, grid and manual-yield controls.

**Live app:** [UK Solar & Battery System Sizer](https://share.streamlit.io/art333art/solar-system-sizer/main/app.py)

The live Streamlit Community Cloud deployment resolves to this repository's `main` branch and `app.py`. The in-app release marker can be used to confirm an automatic deployment after a push.

## Run and test

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
python -m pytest
python -m compileall app.py solar_sizer
```

This is an early-stage planning tool, not an electrical design, MCS calculation, DNO application or permission to connect. Use PVGIS monthly/hourly results and measured consumption for purchasing decisions.

## Affiliate configuration

Commercial offers are configured in `solar_sizer/affiliates.py`; only enabled offers whose context requirements match the calculation are rendered. Approved Amazon UK Associates links carry the disclosure. The two Bimble applications remain disabled pending approval, and the supplied bokman URL remains disabled because it currently resolves to a different brand/product. Verify every destination before enabling it.

The quote-interest sink in `solar_sizer/leads.py` deliberately validates but stores and transmits nothing. Replace that function with an owner-approved service only after privacy, consent, retention and processor terms are ready. Anonymous analytics currently remain in Streamlit session memory and contain event name/time only.

## Commercial launch checklist

1. Replace the placeholder contact email with an owned inbox and add privacy/legal pages.
2. Recruit real UK partners; add labelled tracked links only after written programme approval.
3. Add an opt-in quote/referral form with consent and analytics, then measure completed enquiries rather than clicks.
4. Build a maintained product dataset with compatibility, certifications, warranty, support and pricing evidence.
