from sentinel_alpha.eightk_parser import parse_8k_events
from sentinel_alpha.sec_semantics import EightKEventKind


def test_extracts_item_numbers_in_order_as_unknown():
    parsed = parse_8k_events("Item 2.04 text. Item 8.01 other text.")
    assert [(event.item, event.kind) for event in parsed] == [
        ("2.04", EightKEventKind.UNKNOWN),
        ("8.01", EightKEventKind.UNKNOWN),
    ]


def test_duplicate_items_are_deduplicated():
    parsed = parse_8k_events("Item 4.02 first. ITEM 4.02 repeated.")
    assert len(parsed) == 1
    assert parsed[0].item == "4.02"
    assert parsed[0].kind is EightKEventKind.UNKNOWN


def test_item_number_alone_never_infers_negative():
    parsed = parse_8k_events("Item 2.04 Item 2.06 Item 3.01 Item 4.02")
    assert {event.item for event in parsed} == {"2.04", "2.06", "3.01", "4.02"}
    assert {event.kind for event in parsed} == {EightKEventKind.UNKNOWN}


def test_unrecognized_item_is_unknown_not_positive():
    parsed = parse_8k_events("Item 9.01 Financial Statements and Exhibits")
    assert len(parsed) == 1
    assert parsed[0].kind is EightKEventKind.UNKNOWN


def test_html_and_entities_are_normalized():
    parsed = parse_8k_events("<b>Item&nbsp;3.01</b><p>Notice</p>")
    assert len(parsed) == 1
    assert parsed[0].item == "3.01"
    assert parsed[0].kind is EightKEventKind.UNKNOWN


def test_document_without_items_returns_empty():
    assert parse_8k_events("No item heading here") == ()
