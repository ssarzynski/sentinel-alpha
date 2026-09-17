from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.market_data import PriceObservationInput
from app.models import User
from app.services.market_prices import persist_price_observation
from app.services.portfolio_policy_decisions import evaluate_and_record_portfolio_policy, policy_decision_history
from app.services.portfolios import create_portfolio, upsert_position

T0 = datetime.now(timezone.utc).replace(microsecond=0)


def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def setup(db, policy):
    user = User(email="ledger@example.com", password_hash="test")
    db.add(user); db.commit(); db.refresh(user)
    portfolio = create_portfolio(db, user, name="Ledger", policy=policy)
    upsert_position(db, portfolio, asset="NVDA", asset_class="equity", quantity=10, cost_basis=None, mark_price=100, currency="USD", price_source="TEST", price_observed_at=T0)
    return portfolio


def save_history(db, second_family=True):
    for index in range(22):
        observed = T0 - timedelta(days=21-index)
        persist_price_observation(db, PriceObservationInput("NVDA", observed, 100 + index + index % 2, "USD", "A", "exchange", f"a-{index}"))
        if second_family:
            persist_price_observation(db, PriceObservationInput("NVDA", observed, 100 + index + index % 2, "USD", "B", "institutional", f"b-{index}"))


def test_evaluation_uses_persisted_policy_and_records_snapshot():
    db = db_session(); portfolio = setup(db, {"max_position_weight": 0.5, "max_annualized_volatility": 10.0}); save_history(db)
    decision = evaluate_and_record_portfolio_policy(db, portfolio, stale_after_minutes=60*24*30, min_observations=20)
    assert decision.compliant is False
    assert decision.policy_json["max_position_weight"] == 0.5
    assert decision.risk_data_status == "available"
    assert decision.risk_json["observations"] >= 20
    assert any(item["code"] == "max_position_weight" for item in decision.findings_json)
    assert decision.human_review_status == "pending"


def test_confirmation_gap_withholds_risk_and_is_recorded():
    db = db_session(); portfolio = setup(db, {"max_annualized_volatility": 0.2}); save_history(db, second_family=False)
    decision = evaluate_and_record_portfolio_policy(db, portfolio, stale_after_minutes=60*24*30)
    assert decision.compliant is False
    assert decision.risk_json is None
    assert decision.risk_data_status == "withheld:data_quality:withhold"
    assert any(item["code"] == "data_quality:insufficient_independent_confirmation" for item in decision.findings_json)


def test_stale_provenance_withholds_risk_even_with_two_families():
    db = db_session(); portfolio = setup(db, {}); save_history(db)
    decision = evaluate_and_record_portfolio_policy(db, portfolio, stale_after_minutes=1)
    assert decision.risk_json is None
    assert any(item["code"] == "data_quality:stale_market_data" for item in decision.findings_json)


def test_history_is_append_only_across_repeated_evaluations():
    db = db_session(); portfolio = setup(db, {})
    first = evaluate_and_record_portfolio_policy(db, portfolio); second = evaluate_and_record_portfolio_policy(db, portfolio)
    rows = policy_decision_history(db, portfolio)
    assert len(rows) == 2
    assert {row.decision_key for row in rows} == {first.decision_key, second.decision_key}
