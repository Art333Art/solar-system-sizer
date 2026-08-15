from dataclasses import dataclass


@dataclass(frozen=True)
class AffiliateOffer:
    key: str
    title: str
    description: str
    url: str
    enabled: bool
    network: str


# Approval state is deliberately explicit. Pending offers stay configured so
# they are easy to activate after acceptance, but the UI only reads enabled
# entries. Do not enable an offer without confirming its approved tracking URL.
AFFILIATE_OFFERS = (
    AffiliateOffer(
        key="amazon_electricals",
        title="Electrical monitoring and accessories",
        description="Browse relevant electrical products on Amazon UK.",
        url="https://link.amazon/B05z6RNmr",
        enabled=True,
        network="Amazon UK Associates",
    ),
    AffiliateOffer(
        key="bimble_inverters",
        title="Hybrid inverters",
        description="High-voltage string and hybrid inverter products.",
        url="https://www.bimblesolar.com/",
        enabled=False,
        network="Pending approval",
    ),
    AffiliateOffer(
        key="bimble_batteries",
        title="Battery storage kits",
        description="New and second-life battery storage products.",
        url="https://www.bimblesolar.com/",
        enabled=False,
        network="Pending approval",
    ),
)


def enabled_affiliate_offers() -> tuple[AffiliateOffer, ...]:
    return tuple(offer for offer in AFFILIATE_OFFERS if offer.enabled)
