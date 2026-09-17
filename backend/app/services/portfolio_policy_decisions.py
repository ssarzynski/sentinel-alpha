from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Portfolio, PortfolioPolicyDecision
from app.portfolio_policy import PolicyEvaluation, evaluate_portfolio_policy
from app.services.portfolio_risk import portfolio_historical_risk
from app.services.portfolios import portfolio_analytics


def _analytics_payload(value) -> dict:
    return {
        "nav": value.nav,
        "gross_exposure": value.gross_exposure,
        "net_exposure": value.net_exposure,
        "largest_position_weight": value.largest_position_weight,
        "herfindahl_index": value.herfindahl_index,
        "stale_assets": list(value.stale_assets),
        "asset_class_exposure": value.asset_class_exposure,
    }


def _risk_payload(value) -> dict:
    return {
        "assets": list(value.assets),
        "observations": value.observations,
        "correlation_matrix": value.correlation_matrix,
        "annualized_asset_volatility": value.annualized_asset_volatility,
        "annualized_portfolio_volatility": value.annualized_portfolio_volatility,
        "diversification_ratio": value.diversification_ratio,
    }


def evaluate_and_record_portfolio_policy(
    db: Session,
    portfolio: Portfolio,
    *,
    stale_after_minutes: int = 30,
    risk_start: datetime | None = None,
    risk_end: datetime | None = None,
    min_observations: int = 20,
) -> PortfolioPolicyDecision:
    analytics = portfolio_analytics(
        db,
        portfolio,
        as_of=datetime.now(timezone.utc),
        stale_after_minutes=stale_after_minutes,
    )

    risk = None
    risk_status = "available"
    try:
        risk = portfolio_historical_risk(
            db,
            portfolio,
            start=risk_start,
            end=risk_end,
            min_observations=min_observations,
        )
    except ValueError as exc:
        risk_status = f"unavailable:{exc}"

    evaluation: PolicyEvaluation = evaluate_portfolio_policy(
        analytics,
        portfolio.policy_json or {},
        risk=risk,
    )
    findings = [
        {
            "code": finding.code,
            "severity": finding.severity,
            "actual": finding.actual,
            "limit": finding.limit,
            "message": finding.message,
        }
        for finding in evaluation.findings
    ]
    decision = PortfolioPolicyDecision(
        decision_key=str(uuid4()),
        portfolio_id=portfolio.id,
        compliant=evaluation.compliant,
        policy_json=dict(portfolio.policy_json or {}),
        analytics_json=_analytics_payload(analytics),
        risk_json=_risk_payload(risk) if risk is not None else None,
        findings_json=findings,
        risk_data_status=risk_status,
        human_review_status="pending",
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


def policy_decision_history(db: Session, portfolio: Portfolio, *, limit: int = 50) -> list[PortfolioPolicyDecision]:
    return (
        db.query(PortfolioPolicyDecision)
        .filter(PortfolioPolicyDecision.portfolio_id == portfolio.id)
        .order_by(PortfolioPolicyDecision.evaluated_at.desc(), PortfolioPolicyDecision.id.desc())
        .limit(limit)
        .all()
    )
