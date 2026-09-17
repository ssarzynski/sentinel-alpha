from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.ingestion.form4 import InsiderTransaction, classify_transaction, role_weight
from app.services.insider_intelligence import classify_event, detect_cluster


def tx(owner="Alice", code="P", ad="A", derivative=False, roles=("director",), ticker="NVDA"):
    return InsiderTransaction(
        issuer="NVIDIA", ticker=ticker, owner_name=owner, owner_roles=roles,
        transaction_code=code, acquired_disposed=ad,
        shares=Decimal("100"), price_per_share=Decimal("200"),
        direct_or_indirect="D", is_derivative=derivative,
    )


def test_open_market_purchase_is_distinguished_from_other_transactions():
    result = classify_transaction(tx(code="P"))
    assert result.economic_type == "open_market_purchase"
    assert result.direction == "buy"
    assert result.discretionary_open_market is True
    assert result.signal_eligible is True


def test_tax_and_option_transactions_are_not_discretionary_sales():
    tax = classify_transaction(tx(code="F", ad="D"))
    option = classify_transaction(tx(code="M", ad="A"))
    assert tax.economic_type == "tax_withholding_or_payment"
    assert tax.signal_eligible is False
    assert option.economic_type == "option_exercise"
    assert option.signal_eligible is False


def test_derivative_open_market_code_is_not_signal_eligible():
    result = classify_transaction(tx(code="P", derivative=True))
    assert result.discretionary_open_market is True
    assert result.signal_eligible is False


def test_role_weights_prioritize_executive_information_without_making_a_trade_decision():
    assert role_weight(("CEO",)) > role_weight(("director",))
    assert role_weight(("CFO",)) > role_weight(("10% owner",))


def test_cluster_requires_distinct_insiders_and_sums_value():
    now = datetime(2026, 9, 17, tzinfo=timezone.utc)
    events = [
        classify_event(tx(owner="Alice", roles=("CEO",)), now - timedelta(days=3)),
        classify_event(tx(owner="Bob", roles=("director",)), now),
    ]
    cluster = detect_cluster(events)
    assert cluster is not None
    assert cluster.distinct_insiders == 2
    assert cluster.transaction_count == 2
    assert cluster.aggregate_value == Decimal("40000")
    assert cluster.direction == "buy"
    assert cluster.signal_eligible is True


def test_repeated_filings_by_one_insider_do_not_form_cluster():
    now = datetime(2026, 9, 17, tzinfo=timezone.utc)
    events = [classify_event(tx(owner="Alice"), now - timedelta(days=1)), classify_event(tx(owner="Alice"), now)]
    assert detect_cluster(events) is None
