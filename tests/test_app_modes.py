from streamlit.testing.v1 import AppTest
from pathlib import Path


def test_simple_and_advanced_modes_are_first_class_and_mode_persists_on_rerun():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=20).run()
    assert not app.exception
    assert app.radio[0].label == "Calculator mode"
    assert app.radio[0].value == "Simple"
    assert any(metric.label == "Recommended solar array" for metric in app.metric)
    assert any(item.value == "Compare system options" for item in app.subheader)
    assert any(item.value == "Your solar plan" for item in app.subheader)
    assert app.file_uploader[0].label == "Half-hourly consumption CSV"
    assert len(app.dataframe) == 1
    assert "Estimated annual financial benefit" in app.code[0].value

    app.radio[0].set_value("Advanced").run()
    assert not app.exception
    assert app.radio[0].value == "Advanced"
    assert [item.label for item in app.sidebar.expander[:6]] == [
        "1. Demand and EV",
        "2. PV module and strings",
        "3. Inverter and MPPT",
        "4. Battery",
        "5. Grid, yield and economics",
        "6. Project context",
    ]
    assert any(metric.label == "Cold string Voc" for metric in app.metric)
    assert any(item.value == "Compare system options" for item in app.subheader)
    assert len(app.dataframe) == 1
    assert "Your solar plan" in app.code[0].value

    panel_power = next(item for item in app.number_input if item.label == "Panel power (Wp)")
    panel_power.set_value(500).run()
    assert not app.exception
    assert app.radio[0].value == "Advanced"
    assert next(metric for metric in app.metric if metric.label == "Array").value == "5.00 kWp"


def test_product_links_are_contextual_and_activity_log_is_not_customer_facing():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=20).run()
    simple_expanders = [item.label for item in app.expander]
    assert "OWON 80A 2-clamp bi-directional energy monitor" in simple_expanders
    assert "VORSPRUNG Alpha Max 7.4 kW EV charger" not in simple_expanders
    assert "Type 2 EV charging cable listing" not in simple_expanders
    assert "16 mm² three-core SWA cable listing" not in simple_expanders
    assert "Useful solar & EV products" in simple_expanders
    simple_page = "\n".join(item.value for item in app.markdown)
    assert "VORSPRUNG Alpha Max 7.4 kW EV charger" in simple_page
    assert "Type 2 EV charging cable listing" in simple_page
    assert "OWON 80A 2-clamp bi-directional energy monitor" in simple_page
    assert "SOMELINE solar crimping kit" not in simple_page
    assert "16 mm² three-core SWA cable listing" not in simple_page
    assert "Anonymous session activity" not in simple_page
    assert "recorded anonymously" not in simple_page
    for key in ("amazon_ev_charger", "amazon_ev_cable", "amazon_energy_monitor"):
        assert f"?out={key}" in simple_page

    ev_miles = next(item for item in app.number_input if item.label == "EV driving (miles/week)")
    ev_miles.set_value(100).run()
    simple_ev_expanders = [item.label for item in app.expander]
    assert "VORSPRUNG Alpha Max 7.4 kW EV charger" in simple_ev_expanders
    assert "Type 2 EV charging cable listing" in simple_ev_expanders

    app.radio[0].set_value("Advanced").run()
    advanced_expanders = [item.label for item in app.expander]
    assert "VORSPRUNG Alpha Max 7.4 kW EV charger" in advanced_expanders
    assert "Type 2 EV charging cable listing" in advanced_expanders
    assert "16 mm² three-core SWA cable listing" not in advanced_expanders
    assert "SOMELINE solar crimping kit" not in advanced_expanders
    assert "Products & technical resources" in advanced_expanders
    advanced_page = "\n".join(
        [item.value for item in app.markdown]
        + [item.value for item in app.warning]
    )
    for title in (
        "16 mm² three-core SWA cable listing",
        "VORSPRUNG Alpha Max 7.4 kW EV charger",
        "Type 2 EV charging cable listing",
        "SOMELINE solar crimping kit",
        "OWON 80A 2-clamp bi-directional energy monitor",
    ):
        assert title in advanced_page
    assert "Qualified example only" in advanced_page
    for key in (
        "amazon_electricals", "amazon_ev_charger", "amazon_ev_cable",
        "amazon_solar_tools", "amazon_energy_monitor",
    ):
        assert f"?out={key}" in advanced_page

    sourcing = next(
        item for item in app.checkbox
        if item.label == "I am sourcing specialist solar/electrical installation materials"
    )
    sourcing.set_value(True).run()
    sourced_expanders = [item.label for item in app.expander]
    assert "SOMELINE solar crimping kit" in sourced_expanders
    assert "16 mm² three-core SWA cable listing" not in sourced_expanders


def test_smart_meter_upload_is_validated_in_the_streamlit_ui():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=20).run()
    csv_data = b"timestamp,consumption_kWh\n01/01/2026 00:00,0.2\n01/01/2026 00:30,0.3\n"
    app.file_uploader[0].upload("meter.csv", csv_data, "text/csv").run()
    assert not app.exception
    assert any("Validated 2 consecutive half-hourly readings" in item.value for item in app.success)
    assert any("Interval battery dispatch is intentionally not enabled" in item.value for item in app.info)
