from decimal import Decimal

from app.ingestion.form4 import InsiderTransaction
from app.services.sec_signal_evidence import normalized_form4_payload


def tx(code: str, ad: str, *, derivative: bool = False) -> InsiderTransaction:
    return InsiderTransaction("Example", "EX", "Jane Doe", ("officer",), code, ad, Decimal("10"), Decimal("5"), "D", derivative)


def test_open_market_purchase_is_signal_eligible():
    payload = normalized_form4_payload(tx("P", "A"))
    assert payload["economic_type"] == "open_market_purchase"
    assert payload["transaction_direction"] == "buy"
    assert payload["signal_eligible"] is True


def test_open_market_sale_is_signal_eligible_and_normalized_as_sell():
    payload = normalized_form4_payload(tx("S", "D"))
    assert payload["economic_type"] == "open_market_sale"
    assert payload["transaction_direction"] == "sell"
    assert payload["signal_eligible"] is True


def test_tax_disposition_is_not_signal_eligible_sale():
    payload = normalized_form4_payload(tx("F", "D"))
    assert payload["economic_type"] == "tax_withholding_or_payment"
    assert payload["transaction_direction"] == "dispose"
    assert payload["signal_eligible"] is False


def test_derivative_open_market_code_is_not_signal_eligible():
    payload = normalized_form4_payload(tx("S", "D", derivative=True))
    assert payload["signal_eligible"] is False
    assert "derivative transaction" in payload["classification_reasons"]
