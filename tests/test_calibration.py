from datetime import datetime, timedelta, timezone

import pytest

from sentinel_alpha.calibration import (
    CalibrationStatus,
    HistoricalFeature,
    HistoricalOutcome,
    build_calibration_run,
)

CUTOFF = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_valid_historical_run_is_experimental_by_default():
    run = build_calibration_run(
        asset="btc",
        rule_version="crypto-v1-experiment",
        cutoff=CUTOFF,
        features=(HistoricalFeature("momentum", 0.03, CUTOFF - timedelta(hours=1)),),
        outcome=HistoricalOutcome("24h", 0.02, CUTOFF + timedelta(hours=24)),
    )
    assert run.asset == "BTC"
    assert run.status is CalibrationStatus.EXPERIMENTAL
    assert run.production_eligible is False


def test_feature_after_cutoff_is_rejected_as_look_ahead():
    with pytest.raises(ValueError, match="look-ahead feature rejected"):
        build_calibration_run(
            asset="BTC",
            rule_version="crypto-v1-experiment",
            cutoff=CUTOFF,
            features=(HistoricalFeature("future_volume", 2.0, CUTOFF + timedelta(seconds=1)),),
            outcome=HistoricalOutcome("24h", 0.02, CUTOFF + timedelta(hours=24)),
        )


def test_outcome_must_be_strictly_after_cutoff():
    with pytest.raises(ValueError, match="outcome must occur after"):
        build_calibration_run(
            asset="NVDA",
            rule_version="market-v1-experiment",
            cutoff=CUTOFF,
            features=(HistoricalFeature("momentum", 0.03, CUTOFF),),
            outcome=HistoricalOutcome("24h", 0.02, CUTOFF),
        )


def test_empty_features_fail_closed():
    with pytest.raises(ValueError, match="requires historical features"):
        build_calibration_run(
            asset="NVDA",
            rule_version="market-v1-experiment",
            cutoff=CUTOFF,
            features=(),
            outcome=HistoricalOutcome("24h", 0.02, CUTOFF + timedelta(hours=24)),
        )
