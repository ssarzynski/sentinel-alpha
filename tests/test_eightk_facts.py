from sentinel_alpha.eightk_facts import parse_explicit_adverse_8k_facts
from sentinel_alpha.sec_semantics import EightKEventKind


def test_item_402_non_reliance_language_is_explicit_negative_fact():
    parsed = parse_explicit_adverse_8k_facts(
        "The Audit Committee concluded that the previously issued financial statements should no longer be relied upon."
    )
    assert [(event.item, event.kind) for event in parsed] == [
        ("4.02", EightKEventKind.NEGATIVE)
    ]


def test_item_301_delisting_notice_is_explicit_negative_fact():
    parsed = parse_explicit_adverse_8k_facts(
        "The company received a notice of delisting from the exchange."
    )
    assert [(event.item, event.kind) for event in parsed] == [
        ("3.01", EightKEventKind.NEGATIVE)
    ]


def test_item_number_alone_never_creates_adverse_fact():
    assert parse_explicit_adverse_8k_facts("Item 4.02") == ()
    assert parse_explicit_adverse_8k_facts("Item 3.01") == ()


def test_ambiguous_reliance_language_fails_closed():
    assert parse_explicit_adverse_8k_facts("Management discussed reliance on financial statements.") == ()


def test_html_and_entities_are_normalized():
    parsed = parse_explicit_adverse_8k_facts(
        "<p>Previously issued financial statements should&nbsp;not be relied upon.</p>"
    )
    assert parsed[0].kind is EightKEventKind.NEGATIVE
