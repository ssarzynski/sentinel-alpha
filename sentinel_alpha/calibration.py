"""Anti-look-ahead contracts for Sentinel Alpha historical calibration."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class CalibrationStatus(str, Enum):
    EXPERIMENTAL = "experimental"
    VALIDATED = "validated"


@dataclass(frozen=True)
class HistoricalFeature:
    """A feature known no later than the evaluation cutoff."""

    name: str
    value: float
    observed_at: datetime

    def validate_for(self, cutoff: datetime) -> None:
        if self.observed_at > cutoff:
            raise ValueError(f"look-ahead feature rejected: {self.name}")


@dataclass(frozen=True)
class HistoricalOutcome:
    """Forward outcome used only after a simulated decision has been frozen."""

    horizon: str
    return_pct: float
    observed_at: datetime

    def validate_for(self, cutoff: datetime) -> None:
        if self.observed_at <= cutoff:
            raise ValueError("outcome must occur after evaluation cutoff")


@dataclass(frozen=True)
class CalibrationRun:
    asset: str
    rule_version: str
    cutoff: datetime
    features: tuple[HistoricalFeature, ...]
    outcome: HistoricalOutcome
    status: CalibrationStatus = CalibrationStatus.EXPERIMENTAL

    def validate(self) -> None:
        if not self.asset.strip():
            raise ValueError("asset is required")
        if not self.rule_version.strip():
            raise ValueError("rule_version is required")
        if not self.features:
            raise ValueError("calibration run requires historical features")
        for feature in self.features:
            feature.validate_for(self.cutoff)
        self.outcome.validate_for(self.cutoff)

    @property
    def production_eligible(self) -> bool:
        """Calibration cannot silently change production rules."""
        return self.status is CalibrationStatus.VALIDATED


def build_calibration_run(
    *,
    asset: str,
    rule_version: str,
    cutoff: datetime,
    features: tuple[HistoricalFeature, ...],
    outcome: HistoricalOutcome,
) -> CalibrationRun:
    """Create an experimental run after enforcing temporal boundaries."""
    run = CalibrationRun(
        asset=asset.strip().upper(),
        rule_version=rule_version,
        cutoff=cutoff,
        features=features,
        outcome=outcome,
    )
    run.validate()
    return run
