"""Compact in-memory registry of evaluated research hypotheses.

The registry stores fingerprints and verdict metadata, never raw market history,
credentials, provider payloads, or derived datasets. Persistence can be added
later only if measured repeat-work savings justify its storage cost.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from sentinel_alpha.evidence_gate import EvidenceDecision


@dataclass(frozen=True)
class ResearchCandidate:
    fingerprint: str
    hypothesis: str
    horizon: int
    sufficient: bool
    reasons: tuple[str, ...]


class ResearchRegistry:
    def __init__(self) -> None:
        self._items: dict[str, ResearchCandidate] = {}

    @staticmethod
    def fingerprint(hypothesis: str, horizon: int) -> str:
        normalized = " ".join(hypothesis.strip().lower().split())
        if not normalized:
            raise ValueError("hypothesis is required")
        if horizon < 1:
            raise ValueError("horizon must be positive")
        return sha256(f"v1|{normalized}|{horizon}".encode("utf-8")).hexdigest()[:24]

    def record(self, hypothesis: str, decision: EvidenceDecision) -> ResearchCandidate:
        key = self.fingerprint(hypothesis, decision.horizon)
        candidate = ResearchCandidate(key, " ".join(hypothesis.strip().split()), decision.horizon, decision.sufficient, decision.reasons)
        self._items[key] = candidate
        return candidate

    def lookup(self, hypothesis: str, horizon: int) -> ResearchCandidate | None:
        return self._items.get(self.fingerprint(hypothesis, horizon))

    def __len__(self) -> int:
        return len(self._items)
