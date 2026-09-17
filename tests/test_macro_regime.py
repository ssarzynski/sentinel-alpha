from datetime import datetime, timedelta, timezone

from sentinel_alpha.macro_regime import MacroInput, MacroRegime, evaluate_macro_regime

NOW = datetime(2026, 9, 17, 20, tzinfo=timezone.utc)


def item(metric, value, age_hours=1, max_age_hours=48):
    return MacroInput(metric, value, NOW - timedelta(hours=age_hours), "authoritative-fixture", timedelta(hours=max_age_hours))


def complete(**overrides):
    values = {
        "fed_funds_rate": 3.5,
        "treasury_2y": 3.2,
        "treasury_10y": 3.8,
        "inflation_yoy": 2.2,
        "unemployment_rate": 4.0,
        "volatility_index": 17.0,
    }
    values.update(overrides)
    return {name: item(name, value) for name, value in values.items()}


def test_risk_on_fixture_is_explainable():
    result = evaluate_macro_regime(complete(), now=NOW)
    assert result.regime is MacroRegime.RISK_ON
    assert result.usable is True
    assert result.score >= 2
    assert result.reasons


def test_risk_off_fixture_is_explainable():
    result = evaluate_macro_regime(complete(
        fed_funds_rate=5.5,
        treasury_2y=5.0,
        treasury_10y=4.0,
        inflation_yoy=4.5,
        unemployment_rate=6.5,
        volatility_index=35.0,
    ), now=NOW)
    assert result.regime is MacroRegime.RISK_OFF
    assert result.score <= -2


def test_missing_critical_metric_fails_closed():
    inputs = complete()
    del inputs["inflation_yoy"]
    result = evaluate_macro_regime(inputs, now=NOW)
    assert result.regime is MacroRegime.UNKNOWN
    assert result.missing_metrics == ("inflation_yoy",)


def test_stale_critical_metric_fails_closed():
    inputs = complete()
    inputs["treasury_10y"] = item("treasury_10y", 3.8, age_hours=72, max_age_hours=48)
    result = evaluate_macro_regime(inputs, now=NOW)
    assert result.regime is MacroRegime.UNKNOWN
    assert result.stale_metrics == ("treasury_10y",)


def test_naive_timestamps_are_treated_as_utc():
    inputs = complete()
    inputs["fed_funds_rate"] = MacroInput("fed_funds_rate", 3.5, NOW.replace(tzinfo=None), "fixture", timedelta(hours=48))
    assert evaluate_macro_regime(inputs, now=NOW).usable is True
