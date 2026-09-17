from datetime import datetime, timezone

from app.portfolio import PositionInput, analyze_portfolio
from app.portfolio_policy import evaluate_portfolio_policy
from app.portfolio_risk import analyze_return_risk

NOW = datetime(2026, 9, 17, 18, 0, tzinfo=timezone.utc)


def analytics():
    return analyze_portfolio(
        [
            PositionInput("NVDA", "equity", 600, NOW),
            PositionInput("MSFT", "equity", 300, NOW),
            PositionInput("BTC", "crypto", 100, NOW),
        ],
        as_of=NOW,
    )


def test_compliant_policy_has_no_findings():
    result = evaluate_portfolio_policy(
        analytics(),
        {
            "max_position_weight": 0.7,
            "max_herfindahl_index": 0.5,
            "max_gross_exposure": 1200,
            "max_absolute_net_exposure": 1200,
            "max_asset_class_exposure": {"equity": 950, "crypto": 150},
        },
    )
    assert result.compliant is True
    assert result.findings == ()


def test_concentration_and_asset_class_violations_are_reported():
    result = evaluate_portfolio_policy(
        analytics(),
        {"max_position_weight": 0.5, "max_herfindahl_index": 0.4, "max_asset_class_exposure": {"equity": 800}},
    )
    codes = {finding.code for finding in result.findings}
    assert result.compliant is False
    assert codes == {"max_position_weight", "max_herfindahl_index", "max_asset_class_exposure:equity"}


def test_stale_prices_are_violation_by_default():
    stale = analyze_portfolio([PositionInput("NVDA", "equity", 100, NOW.replace(hour=16))], as_of=NOW)
    result = evaluate_portfolio_policy(stale, {})
    assert result.compliant is False
    assert result.findings[0].code == "stale_prices"


def test_policy_can_explicitly_allow_stale_prices():
    stale = analyze_portfolio([PositionInput("NVDA", "equity", 100, NOW.replace(hour=16))], as_of=NOW)
    result = evaluate_portfolio_policy(stale, {"allow_stale_prices": True})
    assert result.compliant is True


def test_volatility_limit_uses_risk_analytics():
    returns = [0.01, -0.01, 0.02, -0.02] * 5
    risk = analyze_return_risk({"NVDA": returns}, {"NVDA": 1.0})
    result = evaluate_portfolio_policy(analytics(), {"max_annualized_volatility": 0.01}, risk=risk)
    assert result.compliant is False
    assert any(f.code == "max_annualized_volatility" for f in result.findings)


def test_missing_risk_data_is_warning_not_fake_pass_or_violation():
    result = evaluate_portfolio_policy(analytics(), {"max_annualized_volatility": 0.2})
    assert result.compliant is True
    assert result.findings[0].code == "risk_unavailable"
    assert result.findings[0].severity == "warning"


def test_invalid_asset_class_policy_shape_is_rejected():
    try:
        evaluate_portfolio_policy(analytics(), {"max_asset_class_exposure": 100})
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "must be a mapping" in str(exc)
