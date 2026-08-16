from dataclasses import dataclass


@dataclass(frozen=True)
class AffiliateOffer:
    product_id: str
    title: str
    description: str
    url: str
    enabled: bool
    network: str
    required_contexts: frozenset[str]

    @property
    def key(self) -> str:
        """Backward-compatible alias for existing outbound event keys."""
        return self.product_id


# Approval state is deliberately explicit. The UI only reads enabled entries
# whose calculation context matches their intended audience.
AFFILIATE_OFFERS = (
    AffiliateOffer(
        product_id="amazon_electricals",
        title="16 mm² 3-core SWA cable",
        description="An SWA cable example; cable sizing must be determined for the actual installation.",
        url="https://link.amazon/B05z6RNmr",
        enabled=True,
        network="Amazon UK Associates",
        required_contexts=frozenset({"advanced", "diy"}),
    ),
    AffiliateOffer(
        product_id="amazon_ev_charger",
        title="VORSPRUNG Alpha Max 7.4 kW EV charger",
        description="A tethered 7.4 kW home charger for compatible Type 2 electric vehicles.",
        url="https://link.amazon/B03Lpp2EH",
        enabled=True,
        network="Amazon UK Associates",
        required_contexts=frozenset({"ev"}),
    ),
    AffiliateOffer(
        product_id="amazon_ev_cable",
        title="bokman Type 2 EV cable",
        description="A portable Type 2 charging cable for compatible vehicles and charge points.",
        url="https://link.amazon/B04LIcvRh",
        enabled=False,
        network="Disabled: supplied URL resolves to a different product",
        required_contexts=frozenset({"ev"}),
    ),
    AffiliateOffer(
        product_id="amazon_solar_tools",
        title="SOMELINE solar crimping kit",
        description="A compact crimping and assembly kit for compatible solar connectors.",
        url="https://link.amazon/B0f4YmGAU",
        enabled=True,
        network="Amazon UK Associates",
        required_contexts=frozenset({"advanced", "diy"}),
    ),
    AffiliateOffer(
        product_id="amazon_energy_monitor",
        title="OWON 80A 2-clamp bi-directional energy monitor",
        description="A two-clamp monitor for viewing household electricity import, export and consumption.",
        url="https://link.amazon/B0fdrsDTb",
        enabled=True,
        network="Amazon UK Associates",
        required_contexts=frozenset({"monitoring"}),
    ),
    AffiliateOffer(
        product_id="bimble_inverters",
        title="Hybrid inverters",
        description="High-voltage string and hybrid inverter products.",
        url="https://www.bimblesolar.com/",
        enabled=False,
        network="Pending approval",
        required_contexts=frozenset(),
    ),
    AffiliateOffer(
        product_id="bimble_batteries",
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


def affiliate_products_for_page(mode: str, contexts: set[str]) -> tuple[AffiliateOffer, ...]:
    """Return one deduplicated, context-ordered product list for the page."""
    enabled_amazon = {
        offer.product_id: offer for offer in enabled_affiliate_offers()
        if offer.network == "Amazon UK Associates"
    }
    visible_ids = {"amazon_ev_charger", "amazon_ev_cable", "amazon_energy_monitor"}
    if mode == "Advanced" and {"advanced", "diy"} <= contexts:
        visible_ids.update({"amazon_solar_tools", "amazon_electricals"})

    priority: list[str] = []
    if "ev" in contexts:
        priority.extend(("amazon_ev_charger", "amazon_ev_cable"))
    if mode == "Advanced" and "diy" in contexts:
        priority.extend(("amazon_solar_tools", "amazon_electricals"))
    if "monitoring" in contexts:
        priority.append("amazon_energy_monitor")
    priority.extend(("amazon_energy_monitor", "amazon_ev_charger", "amazon_ev_cable",
                     "amazon_solar_tools", "amazon_electricals"))

    seen: set[str] = set()
    products: list[AffiliateOffer] = []
    for product_id in priority:
        if product_id in visible_ids and product_id in enabled_amazon and product_id not in seen:
            products.append(enabled_amazon[product_id])
            seen.add(product_id)
    return tuple(products)
