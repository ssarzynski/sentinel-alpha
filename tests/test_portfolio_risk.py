import pytest

from app.portfolio_risk import analyze_return_risk


def test_perfect_positive_correlation_and_equal_weight_volatility():
    a = [0.01, -0.01, 0.02, -0.02] * 5
    result = analyze_return_risk({"A": a, "B": a}, {"A": 0.5, "B": 0.5}, min_observations=20)
    assert result.observations == 20
    assert result.correlation_matrix["A"]["B"] == pytest.approx(1.0)
    assert result.annualized_portfolio_volatility == pytest.approx(result.annualized_asset_volatility["A"])
    assert result.diversification_ratio == pytest.approx(1.0)


def test_negative_correlation_reduces_portfolio_volatility():
    a = [0.01, -0.01, 0.02, -0.02] * 5
    b = [-x for x in a]
    result = analyze_return_risk({"A": a, "B": b}, {"A": 0.5, "B": 0.5}, min_observations=20)
    assert result.correlation_matrix["A"]["B"] == pytest.approx(-1.0)
    assert result.annualized_portfolio_volatility == pytest.approx(0.0, abs=1e-12)
    assert result.diversification_ratio == 0.0


def test_constant_series_has_defined_correlation_behavior():
    flat = [0.0] * 20
    moving = [0.01, -0.01] * 10
    result = analyze_return_risk({"FLAT": flat, "MOVE": moving}, {"FLAT": 0.2, "MOVE": 0.8})
    assert result.correlation_matrix["FLAT"]["FLAT"] == 1.0
    assert result.correlation_matrix["FLAT"]["MOVE"] == 0.0
    assert result.annualized_asset_volatility["FLAT"] == 0.0


def test_insufficient_history_is_rejected_explicitly():
    with pytest.raises(ValueError, match="insufficient return history"):
        analyze_return_risk({"A": [0.01] * 19}, {"A": 1.0})


def test_misaligned_series_are_rejected():
    with pytest.raises(ValueError, match="aligned and equal length"):
        analyze_return_risk({"A": [0.01] * 20, "B": [0.01] * 21}, {"A": 0.5, "B": 0.5})


def test_weight_asset_mismatch_is_rejected():
    with pytest.raises(ValueError, match="weights must contain exactly"):
        analyze_return_risk({"A": [0.01] * 20}, {"B": 1.0})


def test_invalid_configuration_is_rejected():
    with pytest.raises(ValueError, match="periods_per_year"):
        analyze_return_risk({"A": [0.01, -0.01]}, {"A": 1.0}, periods_per_year=0, min_observations=2)
    with pytest.raises(ValueError, match="min_observations"):
        analyze_return_risk({"A": [0.01, -0.01]}, {"A": 1.0}, min_observations=1)
