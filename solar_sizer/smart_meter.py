import csv
import io
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite


TIMESTAMP_HEADERS = ("timestamp", "datetime", "date time", "interval start", "start")
CONSUMPTION_HEADERS = ("consumption_kwh", "consumption (kwh)", "consumption", "usage (kwh)", "kwh")
TIMESTAMP_FORMATS = ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S")


class SmartMeterCSVError(ValueError):
    pass


@dataclass(frozen=True)
class IntervalReading:
    timestamp: datetime
    consumption_kwh: float


@dataclass(frozen=True)
class SmartMeterDataset:
    readings: tuple[IntervalReading, ...]
    source_format: str

    @property
    def total_kwh(self) -> float:
        return sum(item.consumption_kwh for item in self.readings)

    @property
    def start(self) -> datetime:
        return self.readings[0].timestamp

    @property
    def end(self) -> datetime:
        return self.readings[-1].timestamp


def _normalise_header(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _find_header(fieldnames: list[str], aliases: tuple[str, ...]) -> str | None:
    normalised = {_normalise_header(name): name for name in fieldnames}
    for alias in aliases:
        match = normalised.get(_normalise_header(alias))
        if match:
            return match
    return None


def _parse_timestamp(value: str, row_number: int) -> datetime:
    cleaned = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        parsed = None
        for pattern in TIMESTAMP_FORMATS:
            try:
                parsed = datetime.strptime(cleaned, pattern)
                break
            except ValueError:
                continue
    if parsed is None:
        raise SmartMeterCSVError(f"Row {row_number}: invalid timestamp '{value}'.")
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed


def parse_smart_meter_csv(data: bytes | str) -> SmartMeterDataset:
    """Parse a canonical/Octopus-like half-hourly consumption CSV locally."""
    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise SmartMeterCSVError("CSV must use UTF-8 text encoding.") from exc
    else:
        text = data.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise SmartMeterCSVError("CSV is empty or has no header row.")
    timestamp_header = _find_header(reader.fieldnames, TIMESTAMP_HEADERS)
    consumption_header = _find_header(reader.fieldnames, CONSUMPTION_HEADERS)
    if not timestamp_header or not consumption_header:
        raise SmartMeterCSVError("CSV needs timestamp and consumption_kWh columns (Octopus Start and Consumption (kWh) are also supported).")
    readings: list[IntervalReading] = []
    previous: datetime | None = None
    for row_number, row in enumerate(reader, start=2):
        if not any(str(value or "").strip() for value in row.values()):
            continue
        timestamp = _parse_timestamp(row.get(timestamp_header, ""), row_number)
        try:
            consumption = float(row.get(consumption_header, "").strip())
        except (AttributeError, ValueError) as exc:
            raise SmartMeterCSVError(f"Row {row_number}: consumption must be a kWh number.") from exc
        if not isfinite(consumption) or consumption < 0 or consumption > 100:
            raise SmartMeterCSVError(f"Row {row_number}: consumption kWh is outside a plausible household interval range.")
        if previous is not None:
            try:
                delta_minutes = (timestamp - previous).total_seconds() / 60
            except TypeError as exc:
                raise SmartMeterCSVError(f"Row {row_number}: timestamps must use a consistent timezone format.") from exc
            if delta_minutes <= 0:
                raise SmartMeterCSVError(f"Row {row_number}: timestamps must be strictly increasing with no duplicates.")
            if delta_minutes != 30:
                missing = max(0, round(delta_minutes / 30) - 1)
                detail = f"; approximately {missing} interval(s) are missing" if missing else ""
                raise SmartMeterCSVError(f"Row {row_number}: expected a 30-minute interval, found {delta_minutes:g} minutes{detail}.")
        readings.append(IntervalReading(timestamp, consumption))
        previous = timestamp
    if len(readings) < 2:
        raise SmartMeterCSVError("CSV needs at least two consecutive half-hourly readings.")
    source_format = "Octopus-compatible" if _normalise_header(timestamp_header) == "start" else "Canonical half-hourly"
    return SmartMeterDataset(tuple(readings), source_format)
