from solar_sizer.leads import QuoteInterest, submit_quote_interest, validate_quote_interest


def test_quote_requires_valid_email_and_consent():
    errors = validate_quote_interest(QuoteInterest("Ada", "bad", "SW1A", False))
    assert set(errors) == {"email", "consent"}


def test_valid_quote_is_accepted_by_noop_sink():
    lead = QuoteInterest("Ada", "ada@example.com", "SW1A", True)
    assert validate_quote_interest(lead) == {}
    assert submit_quote_interest(lead) is True
