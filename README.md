# UK Solar System Sizer

A Streamlit feasibility calculator for UK domestic solar PV, batteries, inverters and EV demand. It separates a tested calculation engine from the interface and highlights questions that require datasheets, site modelling, an installer or the DNO.

## Run and test

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
python -m pytest
python -m compileall app.py solar_sizer
```

This is an early-stage planning tool, not an electrical design, MCS calculation, DNO application or permission to connect. Use PVGIS monthly/hourly results and measured consumption for purchasing decisions.

## Commercial launch checklist

1. Replace the placeholder contact email with an owned inbox and add privacy/legal pages.
2. Recruit real UK partners; add labelled tracked links only after written programme approval.
3. Add an opt-in quote/referral form with consent and analytics, then measure completed enquiries rather than clicks.
4. Build a maintained product dataset with compatibility, certifications, warranty, support and pricing evidence.
