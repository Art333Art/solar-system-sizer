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
    assert [item.label for item in app.sidebar.expander[:5]] == [
        "1. Demand and EV",
        "2. PV module and strings",
        "3. Inverter and MPPT",
        "4. Battery",
        "5. Grid, yield and economics",
    ]
    assert any(metric.label == "Cold string Voc" for metric in app.metric)

    panel_power = next(item for item in app.number_input if item.label == "Panel power (Wp)")
    panel_power.set_value(500).run()
    assert not app.exception
    assert app.radio[0].value == "Advanced"
    assert next(metric for metric in app.metric if metric.label == "Array").value == "5.00 kWp"
