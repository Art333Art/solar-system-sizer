from dataclasses import dataclass
import re


@dataclass(frozen=True)
class QuoteInterest:
    name: str
    email: str
    postcode_district: str
    consent: bool


def validate_quote_interest(lead: QuoteInterest) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not lead.name.strip():
        errors["name"] = "Enter your name"
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", lead.email.strip()):
        errors["email"] = "Enter a valid email address"
    if lead.postcode_district and not re.fullmatch(r"[A-Z]{1,2}\d[A-Z\d]?", lead.postcode_district.strip().upper()):
        errors["postcode_district"] = "Use only the postcode district, for example SW1A"
    if not lead.consent:
        errors["consent"] = "Explicit consent is required"
    return errors


def submit_quote_interest(lead: QuoteInterest) -> bool:
    """No-op sink: validates but intentionally stores/sends nothing until configured."""
    return not validate_quote_interest(lead)
