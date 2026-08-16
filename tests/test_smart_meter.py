import pytest

from solar_sizer.smart_meter import SmartMeterCSVError, parse_smart_meter_csv


def test_valid_half_hourly_csv_is_parsed():
    data = """timestamp,consumption_kWh
01/01/2026 00:00,0.20
01/01/2026 00:30,0.15
01/01/2026 01:00,0.25
01/01/2026 01:30,0.30
"""
    result = parse_smart_meter_csv(data)
    assert len(result.readings) == 4
    assert result.total_kwh == pytest.approx(0.9)
    assert result.source_format == "Canonical half-hourly"


def test_octopus_style_headers_are_extensible_adapter_baseline():
    data = """Consumption (kWh),Start
0.2,2026-01-01T00:00:00+00:00
0.3,2026-01-01T00:30:00+00:00
"""
    result = parse_smart_meter_csv(data.encode())
    assert result.total_kwh == pytest.approx(0.5)
    assert result.source_format == "Octopus-compatible"


@pytest.mark.parametrize("data, message", [
    ("timestamp,consumption_kWh\nnot-a-date,0.2\n01/01/2026 00:30,0.3\n", "invalid timestamp"),
    ("timestamp,consumption_kWh\n01/01/2026 00:00,nope\n01/01/2026 00:30,0.3\n", "must be a kWh number"),
    ("timestamp,consumption_kWh\n01/01/2026 00:00,nan\n01/01/2026 00:30,0.3\n", "plausible household"),
    ("time,value\n01/01/2026 00:00,0.2\n01/01/2026 00:30,0.3\n", "needs timestamp"),
])
def test_malformed_csv_is_rejected(data, message):
    with pytest.raises(SmartMeterCSVError, match=message):
        parse_smart_meter_csv(data)


def test_missing_half_hourly_intervals_are_rejected():
    data = """timestamp,consumption_kWh
01/01/2026 00:00,0.20
01/01/2026 01:00,0.25
"""
    with pytest.raises(SmartMeterCSVError, match="1 interval.*missing"):
        parse_smart_meter_csv(data)
