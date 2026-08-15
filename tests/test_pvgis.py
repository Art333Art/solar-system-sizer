import pytest
import requests

from solar_sizer.pvgis import SolarDataError, fetch_pvgis_yield, parse_pvgis_response


def payload():
    return {"outputs": {"monthly": {"fixed": [{"E_m": 75 + month} for month in range(12)]},
                        "totals": {"fixed": {"E_y": 966.5}}}}


class Response:
    def raise_for_status(self):
        return None

    def json(self):
        return payload()


def test_pvgis_response_parsing():
    result = parse_pvgis_response(payload(), 51.5, -0.1)
    assert result.specific_yield_kwh_kwp == 966.5
    assert len(result.monthly_kwh_per_kwp) == 12


def test_pvgis_request_failure_has_controlled_error():
    def failing_get(*args, **kwargs):
        raise requests.Timeout()

    with pytest.raises(SolarDataError, match="temporarily unavailable"):
        fetch_pvgis_yield(51.5, -0.1, 35, 0, get=failing_get)


def test_pvgis_fetch_passes_roof_inputs():
    captured = {}

    def fake_get(url, **kwargs):
        captured.update(kwargs["params"])
        return Response()

    result = fetch_pvgis_yield(51.5, -0.1, 30, -45, get=fake_get)
    assert result.specific_yield_kwh_kwp == 966.5
    assert captured["angle"] == 30
    assert captured["aspect"] == -45
