from dataclasses import dataclass
from time import time


ALLOWED_EVENTS = {"calculator_started", "calculator_completed", "advanced_opened",
                  "affiliate_clicked", "quote_opened", "quote_submitted"}


@dataclass(frozen=True)
class AnonymousEvent:
    name: str
    timestamp: int


def record_event(session_events: list[AnonymousEvent], name: str) -> None:
    """Record event name and time only in the current Streamlit session."""
    if name not in ALLOWED_EVENTS:
        raise ValueError("Unsupported analytics event")
    if not any(event.name == name for event in session_events):
        session_events.append(AnonymousEvent(name, int(time())))
