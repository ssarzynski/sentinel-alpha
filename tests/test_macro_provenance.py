from datetime import datetime, timedelta, timezone

import pytest

from sentinel_alpha.macro_provenance import normalize_macro_inputs
from sentinel_alpha.macro_regime import MacroInput
from sentinel_alpha.provenance import independent_confirmation_keys


def _input(metric: str, source: str) -> MacroInput:
    return MacroInput(
        metric=metric,
        value=4.25,
        observed_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
        source=source,
        max_age=timedelta(days=5),
    )


def test_fred_macro_inputs_normalize_to_canonical_records():
    records = normalize_macro_inputs({
        "treasury_2y": _input("treasury_2y", "fred:DGS2"),
        "treasury_10y": _input("treasury_10y", "fred:DGS10"),
    })
    assert [record.observation.asset for record in records] == ["MACRO", "MACRO"]
    assert records[0].observation.metric == "treasury_2y"
    assert records[0].observation.quality == "authoritative"
    assert records[0].evidence.reference == "fred:DGS2"


def test_fred_series_share_one_independence_group():
    records = normalize_macro_inputs({
        "treasury_2y": _input("treasury_2y", "fred:DGS2"),
        "treasury_10y": _input("treasury_10y", "fred:DGS10"),
    })
    assert independent_confirmation_keys(records) == {"fred"}


def test_treasury_direct_is_distinct_from_fred_redistribution():
    fred_records = normalize_macro_inputs({
        "treasury_2y": _input("treasury_2y", "fred:DGS2"),
    })
    treasury_records = normalize_macro_inputs({
        "treasury_2y": _input(
            "treasury_2y", "treasury:daily_treasury_yield_curve"
        ),
    })
    assert independent_confirmation_keys(fred_records + treasury_records) == {
        "fred",
        "us_treasury",
    }


def test_mapping_key_must_match_macro_metric():
    with pytest.raises(ValueError, match="does not match"):
        normalize_macro_inputs({
            "treasury_10y": _input("treasury_2y", "fred:DGS2"),
        })


def test_unknown_macro_source_fails_closed():
    with pytest.raises(ValueError, match="unsupported macro source"):
        normalize_macro_inputs({
            "treasury_2y": _input("treasury_2y", "unverified:yield"),
        })
