from streamlit.testing.v1 import AppTest
from pathlib import Path


def test_simple_and_advanced_modes_are_first_class_and_mode_persists_on_rerun():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=20).run()
    assert not app.exception
    assert app.radio[0].label == "Calculator mode"
    assert app.radio[0].value == "Simple"
    assert any(metric.label == "Recommended solar array" for metric in app.metric)

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
    assert "16 mm² three-core SWA cable listing" not in simple_expanders
    assert "Anonymous session activity" not in str(app)
    assert "recorded anonymously" not in str(app)

    app.radio[0].set_value("Advanced").run()
    advanced_expanders = [item.label for item in app.expander]
    assert "VORSPRUNG Alpha Max 7.4 kW EV charger" in advanced_expanders
    assert "bokman Type 2 EV cable" in advanced_expanders
    assert "16 mm² three-core SWA cable listing" not in advanced_expanders
    assert "SOMELINE solar crimping kit" not in advanced_expanders

    sourcing = next(
        item for item in app.checkbox
        if item.label == "I am sourcing specialist solar/electrical installation materials"
    )
    sourcing.set_value(True).run()
    sourced_expanders = [item.label for item in app.expander]
    assert "16 mm² three-core SWA cable listing" in sourced_expanders
    assert "SOMELINE solar crimping kit" in sourced_expanders
