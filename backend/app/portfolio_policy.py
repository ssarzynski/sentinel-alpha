from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.portfolio import PortfolioAnalytics
from app.portfolio_risk import RiskAnalytics


@dataclass(frozen=True)
class PolicyFinding:
    code: str
    severity: str
    actual: float | int | str
    limit: float | int | str
    message: str


@dataclass(frozen=True)
class PolicyEvaluation:
    compliant: bool
    findings: tuple[PolicyFinding, ...]


def evaluate_portfolio_policy(
    analytics: PortfolioAnalytics,
    policy: Mapping[str, object],
    *,
    risk: RiskAnalytics | None = None,
) -> PolicyEvaluation:
    """Evaluate portfolio diagnostics against explicit user-configured limits.

    This engine only reports deterministic findings. It never creates orders,
    modifies positions, or authorizes a financial action.
    """
    findings: list[PolicyFinding] = []

    def violation(code: str, actual, limit, message: str) -> None:
        findings.append(PolicyFinding(code, "violation", actual, limit, message))

    max_position = policy.get("max_position_weight")
    if max_position is not None and analytics.largest_position_weight > float(max_position):
        violation("max_position_weight", analytics.largest_position_weight, float(max_position), "Largest position exceeds configured concentration limit")

    max_hhi = policy.get("max_herfindahl_index")
    if max_hhi is not None and analytics.herfindahl_index > float(max_hhi):
        violation("max_herfindahl_index", analytics.herfindahl_index, float(max_hhi), "Portfolio concentration index exceeds configured limit")

    max_gross = policy.get("max_gross_exposure")
    if max_gross is not None and analytics.gross_exposure > float(max_gross):
        violation("max_gross_exposure", analytics.gross_exposure, float(max_gross), "Gross exposure exceeds configured limit")

    max_abs_net = policy.get("max_absolute_net_exposure")
    if max_abs_net is not None and abs(analytics.net_exposure) > float(max_abs_net):
        violation("max_absolute_net_exposure", abs(analytics.net_exposure), float(max_abs_net), "Absolute net exposure exceeds configured limit")

    class_limits = policy.get("max_asset_class_exposure", {})
    if class_limits is not None:
        if not isinstance(class_limits, Mapping):
            raise ValueError("max_asset_class_exposure must be a mapping")
        for asset_class, limit in class_limits.items():
            actual = abs(float(analytics.asset_class_exposure.get(str(asset_class), 0.0)))
            if actual > float(limit):
                violation(f"max_asset_class_exposure:{asset_class}", actual, float(limit), f"{asset_class} exposure exceeds configured limit")

    stale_allowed = bool(policy.get("allow_stale_prices", False))
    if analytics.stale_assets and not stale_allowed:
        findings.append(PolicyFinding("stale_prices", "violation", ",".join(analytics.stale_assets), "none", "Portfolio contains stale price observations"))

    max_vol = policy.get("max_annualized_volatility")
    if max_vol is not None:
        if risk is None:
            findings.append(PolicyFinding("risk_unavailable", "warning", "unavailable", float(max_vol), "Volatility policy cannot be evaluated without accepted historical risk data"))
        elif risk.annualized_portfolio_volatility > float(max_vol):
            violation("max_annualized_volatility", risk.annualized_portfolio_volatility, float(max_vol), "Annualized portfolio volatility exceeds configured limit")

    findings.sort(key=lambda item: (item.severity, item.code))
    return PolicyEvaluation(
        compliant=not any(item.severity == "violation" for item in findings),
        findings=tuple(findings),
    )
