from streamlit.testing.v1 import AppTest
from pathlib import Path


def test_simple_and_advanced_modes_are_first_class_and_mode_persists_on_rerun():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=20).run()
    assert not app.exception
    assert app.radio[0].label == "Calculator mode"
    assert app.radio[0].value == "Simple"
    assert any(metric.label == "Selected solar array" for metric in app.metric)
    configuration = next(item for item in app.selectbox if item.label == "System configuration")
    assert configuration.value == "Solar only"
    assert configuration.options == [
        "Grid only / baseline", "Solar only", "Battery only", "Solar + battery",
        "Solar + battery + tariff optimisation",
    ]
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
        "3. PV inverter and MPPT",
        "4. Battery and inverter/charger",
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
    assert next(metric for metric in app.metric if metric.label == "Selected array").value == "5.00 kWp"
    advanced_configuration = next(item for item in app.selectbox if item.label == "System configuration")
    assert advanced_configuration.value == "Solar only"
    advanced_configuration.set_value("Grid only / baseline").run()
    assert next(metric for metric in app.metric if metric.label == "Selected array").value == "0.00 kWp"
    assert any("PV string and PV inverter/MPPT checks are not applicable" in item.value for item in app.info)


def test_product_links_are_contextual_and_activity_log_is_not_customer_facing():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=20).run()
    simple_expanders = [item.label for item in app.expander]
    assert "Useful solar & EV products" in simple_expanders
    assert simple_expanders.count("Useful solar & EV products") == 1
    simple_markdown = [item.value for item in app.markdown]
    simple_page = "\n".join(simple_markdown)
    assert simple_markdown.count("**OWON 80A 2-clamp bi-directional energy monitor**") == 1
    assert simple_markdown.count("**VORSPRUNG Alpha Max 7.4 kW EV charger**") == 1
    assert "bokman Type 2 EV cable" not in simple_page
    assert "SOMELINE solar crimping kit" not in simple_page
    assert "16 mm² 3-core SWA cable" not in simple_page
    assert "Anonymous session activity" not in simple_page
    assert "recorded anonymously" not in simple_page
    assert "tracked Amazon UK listing" not in simple_page
    assert sum("[Check on Amazon UK →]" in value for value in simple_markdown) == 2
    for key in ("amazon_ev_charger", "amazon_energy_monitor"):
        assert f"?out={key}" in simple_page
    disclosure = "As an Amazon Associate I earn from qualifying purchases. Affiliate links may earn us a commission at no extra cost to you."
    assert [item.value for item in app.caption].count(disclosure) == 1

    ev_miles = next(item for item in app.number_input if item.label == "EV driving (miles/week)")
    ev_miles.set_value(100).run()
    simple_ev_titles = [item.value for item in app.markdown if item.value.startswith("**")]
    assert simple_ev_titles.index("**VORSPRUNG Alpha Max 7.4 kW EV charger**") < simple_ev_titles.index("**OWON 80A 2-clamp bi-directional energy monitor**")

    app.radio[0].set_value("Advanced").run()
    advanced_page = "\n".join(item.value for item in app.markdown)
    assert "VORSPRUNG Alpha Max 7.4 kW EV charger" in advanced_page
    assert "OWON 80A 2-clamp bi-directional energy monitor" in advanced_page
    assert "bokman Type 2 EV cable" not in advanced_page
    assert "16 mm² 3-core SWA cable" not in advanced_page
    assert "SOMELINE solar crimping kit" not in advanced_page

    sourcing = next(
        item for item in app.checkbox
        if item.label == "I am sourcing specialist solar/electrical installation materials"
    )
    sourcing.set_value(True).run()
    sourced_markdown = [item.value for item in app.markdown]
    for title in (
        "VORSPRUNG Alpha Max 7.4 kW EV charger",
        "SOMELINE solar crimping kit",
        "16 mm² 3-core SWA cable",
        "OWON 80A 2-clamp bi-directional energy monitor",
    ):
        assert sourced_markdown.count(f"**{title}**") == 1
    assert all("bokman Type 2 EV cable" not in value for value in sourced_markdown)
    assert sum("[Check on Amazon UK →]" in value for value in sourced_markdown) == 4
    assert [item.value for item in app.caption].count(disclosure) == 1


def test_smart_meter_upload_is_validated_in_the_streamlit_ui():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=20).run()
    csv_data = b"timestamp,consumption_kWh\n01/01/2026 00:00,0.2\n01/01/2026 00:30,0.3\n"
    app.file_uploader[0].upload("meter.csv", csv_data, "text/csv").run()
    assert not app.exception
    assert any("Validated 2 consecutive half-hourly readings" in item.value for item in app.success)
    assert any("Interval battery dispatch is intentionally not enabled" in item.value for item in app.info)


def test_explicit_system_configurations_control_simple_results_and_tariff_availability():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=20).run()
    configuration = next(item for item in app.selectbox if item.label == "System configuration")
    assert configuration.options == [
        "Grid only / baseline", "Solar only", "Battery only", "Solar + battery",
        "Solar + battery + tariff optimisation",
    ]
    assert len(app.dataframe[0].value) == 4
    assert any("Add an off-peak tariff" in item.value for item in app.info)

    configuration.set_value("Grid only / baseline").run()
    assert next(metric for metric in app.metric if metric.label == "Selected solar array").value == "0.0 kWp"
    assert next(metric for metric in app.metric if metric.label == "Selected battery").value == "Battery disabled"

    configuration = next(item for item in app.selectbox if item.label == "System configuration")
    configuration.set_value("Battery only").run()
    assert next(metric for metric in app.metric if metric.label == "Selected solar array").value == "0.0 kWp"
    assert "usable" in next(metric for metric in app.metric if metric.label == "Selected battery").value

    configuration = next(item for item in app.selectbox if item.label == "System configuration")
    configuration.set_value("Solar + battery + tariff optimisation").run()
    assert len(app.dataframe[0].value) == 5
    assert "Selected configuration: Solar + battery + tariff optimisation" in app.code[0].value

    rows = app.dataframe[0].value.set_index("Scenario")
    battery_row = next(index for index in rows.index if "Solar + battery" in index and "tariff" not in index)
    tariff_row = next(index for index in rows.index if "tariff optimisation" in index)
    assert rows.loc[battery_row, "Off-peak charge"] == "0 kWh"
    assert rows.loc[tariff_row, "Off-peak charge"] != "0 kWh"
    assert rows.loc[battery_row, "Annual electricity cost"] != rows.loc[tariff_row, "Annual electricity cost"]


def test_inactive_component_outputs_clear_and_input_state_survives_switching():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=20).run()
    roof_area = next(item for item in app.number_input if item.label == "Usable unshaded roof area (m²)")
    roof_area.set_value(42).run()
    configuration = next(item for item in app.selectbox if item.label == "System configuration")
    configuration.set_value("Battery only").run()
    roof_area = next(item for item in app.number_input if item.label == "Usable unshaded roof area (m²)")
    assert roof_area.disabled and roof_area.value == 42
    assert next(metric for metric in app.metric if metric.label == "Selected solar array").value == "0.0 kWp"
    assert next(metric for metric in app.metric if metric.label == "Estimated annual generation").value == "0 kWh/year"
    assert "Solar: disabled" in app.code[0].value
    rows = app.dataframe[0].value.set_index("Scenario")
    selected_row = next(index for index in rows.index if "Selected" in index)
    assert "Battery only" in selected_row
    assert rows.loc[selected_row, "Solar"] == "0.0 kWp"
    assert rows.loc[selected_row, "Generation"] == "0 kWh"

    configuration = next(item for item in app.selectbox if item.label == "System configuration")
    configuration.set_value("Solar only").run()
    roof_area = next(item for item in app.number_input if item.label == "Usable unshaded roof area (m²)")
    assert not roof_area.disabled and roof_area.value == 42
    assert next(metric for metric in app.metric if metric.label == "Selected battery").value == "Battery disabled"
    assert "Battery: disabled" in app.code[0].value
    rows = app.dataframe[0].value.set_index("Scenario")
    selected_row = next(index for index in rows.index if "Selected" in index)
    assert "Solar only" in selected_row
    assert rows.loc[selected_row, "Battery"] == "None"

    app.radio[0].set_value("Advanced").run()
    assert len([item for item in app.selectbox if item.label == "System configuration"]) == 1
    advanced_configuration = next(item for item in app.selectbox if item.label == "System configuration")
    assert advanced_configuration.options == configuration.options
    panel_power = next(item for item in app.number_input if item.label == "Panel power (Wp)")
    panel_power.set_value(500).run()
    advanced_configuration = next(item for item in app.selectbox if item.label == "System configuration")
    advanced_configuration.set_value("Battery only").run()
    panel_power = next(item for item in app.number_input if item.label == "Panel power (Wp)")
    assert panel_power.disabled and panel_power.value == 500
    assert next(metric for metric in app.metric if metric.label == "Selected array").value == "0.00 kWp"
    assert next(metric for metric in app.metric if metric.label == "Annual generation").value == "0 kWh"

    advanced_configuration = next(item for item in app.selectbox if item.label == "System configuration")
    advanced_configuration.set_value("Solar + battery").run()
    panel_power = next(item for item in app.number_input if item.label == "Panel power (Wp)")
    assert not panel_power.disabled and panel_power.value == 500
    assert next(metric for metric in app.metric if metric.label == "Selected array").value == "5.00 kWp"


def test_explicit_battery_capacity_controls_are_available_in_both_modes():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=20).run()
    simple_size = next(item for item in app.number_input if item.label == "Battery size (kWh usable)")
    assert simple_size.disabled
    configuration = next(item for item in app.selectbox if item.label == "System configuration")
    configuration.set_value("Battery only").run()
    simple_size = next(item for item in app.number_input if item.label == "Battery size (kWh usable)")
    assert not simple_size.disabled
    simple_size.set_value(12.5).run()
    assert next(metric for metric in app.metric if metric.label == "Selected battery").value == "12.5 kWh usable"
    export_control = next(item for item in app.checkbox if item.label == "Allow battery export to grid")
    assert not export_control.disabled and export_control.value is False

    app.radio[0].set_value("Advanced").run()
    nominal = next(item for item in app.number_input if item.label == "Installed battery capacity (kWh nominal)")
    assert not nominal.disabled
    nominal.set_value(14.0).run()
    assert next(metric for metric in app.metric if metric.label == "Selected battery").value == "12.6 kWh usable"
    labels = {item.label for item in app.number_input}
    assert {"AC battery charge power limit (kW)", "AC battery discharge power limit (kW)"} <= labels
    app.radio[0].set_value("Simple").run()
    assert next(item for item in app.number_input if item.label == "Battery size (kWh usable)").value == 12.5
    assert next(metric for metric in app.metric if metric.label == "Selected battery").value == "12.5 kWh usable"


def test_simple_configuration_activation_matrix_and_ev_storage_separation():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=20).run()
    assert [item.value for item in app.markdown].count("### Home battery storage") == 1
    ev = next(item for item in app.number_input if item.label == "EV driving (miles/week)")
    ev.set_value(250).run()
    assert [item.value for item in app.markdown].count("### Home battery storage") == 1

    expected = {
        "Grid only / baseline": (False, False, "Not applicable"),
        "Solar only": (True, False, "PV inverter"),
        "Battery only": (False, True, "Battery inverter/charger"),
        "Solar + battery": (True, True, "PV inverter"),
        "Solar + battery + tariff optimisation": (True, True, "PV inverter"),
    }
    for title, (solar_active, battery_active, inverter_text) in expected.items():
        next(item for item in app.selectbox if item.label == "System configuration").set_value(title).run()
        roof = next(item for item in app.number_input if item.label == "Usable unshaded roof area (m²)")
        battery = next(item for item in app.number_input if item.label == "Battery size (kWh usable)")
        charger = next(item for item in app.number_input if item.label == "Battery inverter/charger power limit (kW)")
        assert roof.disabled is (not solar_active)
        assert battery.disabled is (not battery_active)
        assert charger.disabled is (not battery_active)
        inverter = next(item for item in app.metric if item.label == "Inverter / charger")
        assert inverter_text in inverter.value


def test_advanced_configuration_matrix_keeps_battery_inverter_active_without_pv():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=20).run()
    app.radio[0].set_value("Advanced").run()
    expected = {
        "Grid only / baseline": (False, False),
        "Solar only": (True, False),
        "Battery only": (False, True),
        "Solar + battery": (True, True),
        "Solar + battery + tariff optimisation": (True, True),
    }
    for title, (solar_active, battery_active) in expected.items():
        next(item for item in app.selectbox if item.label == "System configuration").set_value(title).run()
        panel = next(item for item in app.number_input if item.label == "Panel power (Wp)")
        pv_inverter = next(item for item in app.number_input if item.label == "PV inverter rated AC output (kW)")
        charge = next(item for item in app.number_input if item.label == "AC battery charge power limit (kW)")
        discharge = next(item for item in app.number_input if item.label == "AC battery discharge power limit (kW)")
        phases = next(item for item in app.selectbox if item.label == "Grid phases")
        assert panel.disabled is (not solar_active)
        assert pv_inverter.disabled is (not solar_active)
        assert charge.disabled is (not battery_active)
        assert discharge.disabled is (not battery_active)
        assert phases.disabled is (not (solar_active or battery_active))


def test_advanced_stored_values_restore_without_entering_inactive_results():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=20).run()
    next(item for item in app.selectbox if item.label == "System configuration").set_value("Solar + battery").run()
    app.radio[0].set_value("Advanced").run()
    panel = next(item for item in app.number_input if item.label == "Panel power (Wp)")
    nominal = next(item for item in app.number_input if item.label == "Installed battery capacity (kWh nominal)")
    panel.set_value(500).run()
    nominal = next(item for item in app.number_input if item.label == "Installed battery capacity (kWh nominal)")
    nominal.set_value(18.0).run()

    next(item for item in app.selectbox if item.label == "System configuration").set_value("Battery only").run()
    assert next(item for item in app.number_input if item.label == "Panel power (Wp)").value == 500
    assert next(item for item in app.number_input if item.label == "Panel power (Wp)").disabled
    assert next(metric for metric in app.metric if metric.label == "Selected array").value == "0.00 kWp"
    assert next(metric for metric in app.metric if metric.label == "Annual generation").value == "0 kWh"

    next(item for item in app.selectbox if item.label == "System configuration").set_value("Solar only").run()
    assert next(item for item in app.number_input if item.label == "Installed battery capacity (kWh nominal)").value == 18.0
    assert next(item for item in app.number_input if item.label == "Installed battery capacity (kWh nominal)").disabled
    assert next(metric for metric in app.metric if metric.label == "Selected battery").value == "Battery disabled"

    next(item for item in app.selectbox if item.label == "System configuration").set_value("Solar + battery").run()
    assert next(item for item in app.number_input if item.label == "Panel power (Wp)").value == 500
    assert next(item for item in app.number_input if item.label == "Installed battery capacity (kWh nominal)").value == 18.0
    assert next(metric for metric in app.metric if metric.label == "Selected battery").value == "16.2 kWh usable"


def test_advanced_overview_separates_charge_discharge_and_raw_bms_limits():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=20).run()
    next(item for item in app.selectbox if item.label == "System configuration").set_value("Battery only").run()
    app.radio[0].set_value("Advanced").run()
    next(item for item in app.number_input if item.label == "Battery nominal voltage (V)").set_value(100.0).run()
    next(item for item in app.number_input if item.label == "Battery/BMS continuous current (A)").set_value(100.0).run()
    next(item for item in app.number_input if item.label == "AC battery charge power limit (kW)").set_value(5.0).run()
    next(item for item in app.number_input if item.label == "AC battery discharge power limit (kW)").set_value(8.0).run()
    metrics = {item.label: item.value for item in app.metric}
    assert metrics["Battery charge capability"] == "≤ 5.0 kW"
    assert metrics["Battery discharge capability"] == "≤ 8.0 kW"
    assert metrics["Battery/BMS raw limit"] == "10.0 kW"
