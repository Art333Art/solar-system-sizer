import pytest

from solar_sizer.analytics import record_event


def test_anonymous_events_store_no_payload_and_are_deduplicated():
    events = []
    record_event(events, "calculator_started")
    record_event(events, "calculator_started")
    assert len(events) == 1
    assert set(events[0].__dict__) == {"name", "timestamp"}


def test_unknown_event_is_rejected():
    with pytest.raises(ValueError):
        record_event([], "postcode_entered")
