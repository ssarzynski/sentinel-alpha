"""Canonical domain models for Sentinel Alpha.

The initial models intentionally stay small. They define the contracts that
providers, research code, and the future API will share.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Asset:
    symbol: str
    asset_class: str
    active: bool = True


@dataclass(frozen=True)
class Observation:
    asset: str
    metric: str
    value: Any
    source: str
    observed_at: datetime
    quality: str = "unknown"


@dataclass(frozen=True)
class Evidence:
    source: str
    statement: str
    observed_at: datetime
    reference: str | None = None


@dataclass
class Signal:
    asset: str
    status: str
    confirmations: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    rule_version: str = "0.1"

    def has_minimum_confirmations(self, minimum: int = 2) -> bool:
        return len(set(self.confirmations)) >= minimum
