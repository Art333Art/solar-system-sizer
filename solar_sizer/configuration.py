from dataclasses import dataclass


CONFIGURATION_OPTIONS = (
    "Grid only / baseline",
    "Solar only",
    "Battery only",
    "Solar + battery",
    "Solar + battery + tariff optimisation",
)


@dataclass(frozen=True)
class ActiveConfiguration:
    """Canonical component activation state derived from one user selection.

    Widget values remain in Streamlit session state when inactive, but only
    values guarded by these flags may enter selected results or active checks.
    """

    title: str
    key: str
    solar: bool
    battery: bool
    pv_inverter_mppt: bool
    battery_inverter_charger: bool
    grid_tariffs: bool
    tariff_optimisation: bool

    @property
    def inverter_charger(self) -> bool:
        return self.pv_inverter_mppt or self.battery_inverter_charger


_CONFIGURATIONS = {
    "Grid only / baseline": ActiveConfiguration(
        "Grid only / baseline", "grid", False, False, False, False, True, False
    ),
    "Solar only": ActiveConfiguration(
        "Solar only", "solar", True, False, True, False, True, False
    ),
    "Battery only": ActiveConfiguration(
        "Battery only", "battery_only", False, True, False, True, True, False
    ),
    "Solar + battery": ActiveConfiguration(
        "Solar + battery", "battery", True, True, True, True, True, False
    ),
    "Solar + battery + tariff optimisation": ActiveConfiguration(
        "Solar + battery + tariff optimisation", "tariff", True, True, True, True, True, True
    ),
}


def active_configuration(title: str) -> ActiveConfiguration:
    try:
        return _CONFIGURATIONS[title]
    except KeyError as exc:
        raise ValueError(f"Unknown system configuration: {title}") from exc
