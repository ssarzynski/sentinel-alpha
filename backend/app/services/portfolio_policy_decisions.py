from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.data_quality_gate import evaluate_data_quality_gate
from app.models import Portfolio, PortfolioPolicyDecision
from app.portfolio_policy import PolicyEvaluation, evaluate_portfolio_policy
from app.services.market_provenance import market_provenance_summary
from app.services.portfolio_risk import portfolio_historical_risk
from app.services.portfolios import portfolio_analytics, portfolio_positions


def _analytics_payload(value) -> dict:
    return {"nav": value.nav, "gross_exposure": value.gross_exposure, "net_exposure": value.net_exposure, "largest_position_weight": value.largest_position_weight, "herfindahl_index": value.herfindahl_index, "stale_assets": list(value.stale_assets), "asset_class_exposure": value.asset_class_exposure}


def _risk_payload(value) -> dict:
    return {"assets": list(value.assets), "observations": value.observations, "correlation_matrix": value.correlation_matrix, "annualized_asset_volatility": value.annualized_asset_volatility, "annualized_portfolio_volatility": value.annualized_portfolio_volatility, "diversification_ratio": value.diversification_ratio}


def evaluate_and_record_portfolio_policy(db: Session, portfolio: Portfolio, *, stale_after_minutes: int = 30, risk_start: datetime | None = None, risk_end: datetime | None = None, min_observations: int = 20) -> PortfolioPolicyDecision:
    now = datetime.now(timezone.utc)
    analytics = portfolio_analytics(db, portfolio, as_of=now, stale_after_minutes=stale_after_minutes)
    assets = [row.asset for row in portfolio_positions(db, portfolio)]
    provenance = market_provenance_summary(db, assets, now=now, stale_after_minutes=stale_after_minutes)
    gate = evaluate_data_quality_gate(provenance)

    risk = None
    if gate.risk_signals_allowed:
        risk_status = "available"
        try:
            risk = portfolio_historical_risk(db, portfolio, start=risk_start, end=risk_end, min_observations=min_observations)
        except ValueError as exc:
            risk_status = f"unavailable:{exc}"
    else:
        risk_status = f"withheld:data_quality:{gate.status.lower()}"

    evaluation: PolicyEvaluation = evaluate_portfolio_policy(analytics, portfolio.policy_json or {}, risk=risk)
    findings = [{"code": f.code, "severity": f.severity, "actual": f.actual, "limit": f.limit, "message": f.message} for f in evaluation.findings]
    findings.extend({"code": f"data_quality:{f.code}", "severity": "violation" if f.severity == "block" else "warning", "actual": f.asset, "limit": "PASS", "message": f.message} for f in gate.findings)
    compliant = evaluation.compliant and gate.status != "WITHHOLD"

    decision = PortfolioPolicyDecision(decision_key=str(uuid4()), portfolio_id=portfolio.id, compliant=compliant, policy_json=dict(portfolio.policy_json or {}), analytics_json=_analytics_payload(analytics), risk_json=_risk_payload(risk) if risk is not None else None, findings_json=findings, risk_data_status=risk_status, human_review_status="pending")
    db.add(decision); db.commit(); db.refresh(decision)
    return decision


def policy_decision_history(db: Session, portfolio: Portfolio, *, limit: int = 50) -> list[PortfolioPolicyDecision]:
    return db.query(PortfolioPolicyDecision).filter(PortfolioPolicyDecision.portfolio_id == portfolio.id).order_by(PortfolioPolicyDecision.evaluated_at.desc(), PortfolioPolicyDecision.id.desc()).limit(limit).all()
