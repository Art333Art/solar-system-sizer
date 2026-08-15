from solar_sizer.content import BUYING_GUIDES


def test_buying_guides_are_focused_and_evidence_led():
    assert len(BUYING_GUIDES) == 5
    combined = " ".join(BUYING_GUIDES.values()).lower()
    assert "half-hourly" in combined
    assert "16 a per phase" in combined
    assert "3.5 miles/kwh" in combined
