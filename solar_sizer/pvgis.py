from dataclasses import dataclass
from typing import Any, Callable

import requests

PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc"
POSTCODE_URL = "https://api.postcodes.io/postcodes/{postcode}"


class SolarDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class PVGISResult:
    specific_yield_kwh_kwp: float
    monthly_kwh_per_kwp: tuple[float, ...]
    latitude: float
    longitude: float
    source: str = "PVGIS 5.3"


def parse_pvgis_response(payload: dict[str, Any], latitude: float, longitude: float) -> PVGISResult:
    try:
        monthly = tuple(float(row["E_m"]) for row in payload["outputs"]["monthly"]["fixed"])
        annual = float(payload["outputs"]["totals"]["fixed"]["E_y"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SolarDataError("PVGIS returned an unexpected response") from exc
    if len(monthly) != 12 or not 200 <= annual <= 2000:
        raise SolarDataError("PVGIS returned implausible yield data")
    return PVGISResult(annual, monthly, latitude, longitude)


def geocode_uk_postcode(postcode: str, get: Callable[..., Any] = requests.get) -> tuple[float, float]:
    cleaned = "".join(postcode.upper().split())
    if len(cleaned) < 5:
        raise SolarDataError("Enter a complete UK postcode")
    try:
        response = get(POSTCODE_URL.format(postcode=cleaned), timeout=6)
        response.raise_for_status()
        result = response.json()["result"]
        return float(result["latitude"]), float(result["longitude"])
    except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
        raise SolarDataError("Postcode lookup is unavailable") from exc


def fetch_pvgis_yield(latitude: float, longitude: float, tilt: float, aspect: float,
                      losses_pct: float = 14, get: Callable[..., Any] = requests.get) -> PVGISResult:
    params = {"lat": latitude, "lon": longitude, "peakpower": 1, "loss": losses_pct,
              "angle": tilt, "aspect": aspect, "outputformat": "json", "mountingplace": "building"}
    try:
        response = get(PVGIS_URL, params=params, timeout=12)
        response.raise_for_status()
        return parse_pvgis_response(response.json(), latitude, longitude)
    except SolarDataError:
        raise
    except (requests.RequestException, ValueError) as exc:
        raise SolarDataError("PVGIS is temporarily unavailable") from exc


def fallback_specific_yield(aspect: float, tilt: float) -> float:
    """Conservative UK placeholder, used only when live PVGIS cannot be reached."""
    orientation_factor = max(0.65, 1 - abs(aspect) / 360)
    tilt_factor = max(0.85, 1 - abs(35 - tilt) / 200)
    return 850 * orientation_factor * tilt_factor
