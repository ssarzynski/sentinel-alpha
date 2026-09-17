from datetime import datetime, timedelta, timezone
import pytest
from sentinel_alpha.macro_provenance import normalize_macro_inputs
from sentinel_alpha.macro_regime import MacroInput
from sentinel_alpha.provenance import independent_confirmation_keys

def _input(metric: str, source: str) -> MacroInput:
    return MacroInput(metric=metric, value=4.25, observed_at=datetime(2026, 9, 17, tzinfo=timezone.utc), source=source, max_age=timedelta(days=5))

def test_fred_transport_preserves_underlying_source_independence():
    records = normalize_macro_inputs({"treasury_2y": _input("treasury_2y", "fred:DGS2"), "treasury_10y": _input("treasury_10y", "fred:DGS10")})
    assert records[0].source.provider == "Federal Reserve Bank of St. Louis"
    assert independent_confirmation_keys(records) == {"federal_reserve_board"}

def test_bls_series_share_bls_independence_group():
    records = normalize_macro_inputs({"inflation": _input("inflation", "fred:CPIAUCSL"), "unemployment": _input("unemployment", "fred:UNRATE")})
    assert independent_confirmation_keys(records) == {"bls"}

def test_distinct_underlying_publishers_are_distinct():
    records = normalize_macro_inputs({"treasury_2y": _input("treasury_2y", "fred:DGS2"), "vix": _input("vix", "fred:VIXCLS")})
    assert independent_confirmation_keys(records) == {"federal_reserve_board", "cboe"}

def test_treasury_direct_is_not_conflated_with_fred_h15():
    records = normalize_macro_inputs({"treasury_2y": _input("treasury_2y", "treasury:daily_treasury_yield_curve")})
    assert independent_confirmation_keys(records) == {"us_treasury"}

def test_mapping_key_must_match_macro_metric():
    with pytest.raises(ValueError, match="does not match"):
        normalize_macro_inputs({"treasury_10y": _input("treasury_2y", "fred:DGS2")})

def test_unknown_fred_series_fails_closed():
    with pytest.raises(ValueError, match="unsupported FRED macro series"):
        normalize_macro_inputs({"x": _input("x", "fred:UNKNOWN")})

def test_unknown_macro_source_fails_closed():
    with pytest.raises(ValueError, match="unsupported macro source"):
        normalize_macro_inputs({"x": _input("x", "unverified:yield")})
