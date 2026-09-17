from sentinel_alpha.form4_parser import parse_form4_transactions
from sentinel_alpha.sec_semantics import Form4TransactionKind


def xml_with_codes(*codes: str) -> str:
    transactions = "".join(
        f"<nonDerivativeTransaction><transactionCoding><transactionCode>{code}</transactionCode>"
        f"</transactionCoding></nonDerivativeTransaction>"
        for code in codes
    )
    return f"<ownershipDocument><nonDerivativeTable>{transactions}</nonDerivativeTable></ownershipDocument>"


def test_parses_purchase_sale_and_award_codes():
    parsed = parse_form4_transactions(xml_with_codes("P", "S", "A"))
    assert [item.kind for item in parsed] == [
        Form4TransactionKind.PURCHASE,
        Form4TransactionKind.SALE,
        Form4TransactionKind.AWARD,
    ]


def test_unknown_code_is_other_not_support():
    parsed = parse_form4_transactions(xml_with_codes("M"))
    assert len(parsed) == 1
    assert parsed[0].kind is Form4TransactionKind.OTHER
    assert parsed[0].transaction_code == "M"


def test_missing_transaction_code_is_ignored():
    document = "<ownershipDocument><nonDerivativeTransaction /></ownershipDocument>"
    assert parse_form4_transactions(document) == ()


def test_malformed_xml_fails_closed():
    assert parse_form4_transactions("<ownershipDocument>") == ()


def test_namespace_does_not_break_parser():
    document = (
        '<ownershipDocument xmlns="urn:sec">'
        "<nonDerivativeTransaction><transactionCoding><transactionCode>S</transactionCode>"
        "</transactionCoding></nonDerivativeTransaction></ownershipDocument>"
    )
    parsed = parse_form4_transactions(document)
    assert len(parsed) == 1
    assert parsed[0].kind is Form4TransactionKind.SALE
