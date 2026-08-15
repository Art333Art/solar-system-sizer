from dataclasses import dataclass


@dataclass(frozen=True)
class AffiliateOffer:
    key: str
    title: str
    description: str
    url: str
    enabled: bool
    network: str
    required_contexts: frozenset[str]


# Approval state is deliberately explicit. Pending offers stay configured so
# they are easy to activate after acceptance, but the UI only reads enabled
# entries. Do not enable an offer without confirming its approved tracking URL.
AFFILIATE_OFFERS = (
    AffiliateOffer(
        key="amazon_electricals",
        title="16 mm² three-core SWA cable listing",
        description="Only relevant when this exact cable type and size has already been specified by a competent designer. This calculator does not size AC cables.",
        url="https://link.amazon/B05z6RNmr",
        enabled=True,
        network="Amazon UK Associates",
        required_contexts=frozenset({"advanced"}),
    ),
    AffiliateOffer(
        key="amazon_ev_charger",
        title="VORSPRUNG Alpha Max 7.4 kW EV charger",
        description="Relevant to home EV charging. Vehicle, supply, earthing, load management, smart-charge compliance and installation compatibility must be checked by a competent installer.",
        url="https://link.amazon/B03Lpp2EH",
        enabled=True,
        network="Amazon UK Associates",
        required_contexts=frozenset({"ev"}),
    ),
    AffiliateOffer(
        key="amazon_ev_cable",
        title="bokman Type 2 EV charging cable",
        description="Relevant to Type 2 EV users. A cable marketed for up to 22 kW will charge only at the lowest limit of the vehicle, charge point, cable and electrical supply.",
        url="https://link.amazon/B04LIcvRh",
        enabled=False,
        network="Amazon URL target mismatch — awaiting corrected tracking URL",
        required_contexts=frozenset({"ev"}),
    ),
    AffiliateOffer(
        key="amazon_solar_tools",
        title="SOMELINE solar crimping tool kit",
        description="An Advanced/DIY tool kit only. Included connectors are not proof of compatibility: use the exact connector family and manufacturer-approved tooling specified for the installation.",
        url="https://link.amazon/B0f4YmGAU",
        enabled=True,
        network="Amazon UK Associates",
        required_contexts=frozenset({"advanced", "diy"}),
    ),
    AffiliateOffer(
        key="amazon_energy_monitor",
        title="OWON 80A two-clamp bi-directional Wi-Fi energy monitor",
        description="Relevant for observing household import, export and self-consumption. Installation around mains conductors must follow the manufacturer instructions and be completed without unqualified access to live electrical equipment.",
        url="https://link.amazon/B0fdrsDTb",
        enabled=True,
        network="Amazon UK Associates",
        required_contexts=frozenset({"monitoring"}),
    ),
    AffiliateOffer(
        key="bimble_inverters",
        title="Hybrid inverters",
        description="High-voltage string and hybrid inverter products.",
        url="https://www.bimblesolar.com/",
        enabled=False,
        network="Pending approval",
        required_contexts=frozenset(),
    ),
    AffiliateOffer(
        key="bimble_batteries",
        title="Battery storage kits",
        description="New and second-life battery storage products.",
        url="https://www.bimblesolar.com/",
        enabled=False,
        network="Pending approval",
        required_contexts=frozenset(),
    ),
)


def enabled_affiliate_offers(contexts: set[str] | None = None) -> tuple[AffiliateOffer, ...]:
    enabled = tuple(offer for offer in AFFILIATE_OFFERS if offer.enabled)
    if contexts is None:
        return enabled
    return tuple(offer for offer in enabled if offer.required_contexts <= contexts)
