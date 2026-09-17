"""Bridge normalized ingestion records into Sentinel Alpha evaluation."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from .evidence_store import EvidenceStore
from .pipeline import EvaluationResult, evaluate_records
from .provenance import NormalizedRecord
from .risk_gate import TradeProposal


@dataclass(frozen=True)
class EvaluationPolicy:
    status: str = "confirmed"
    new_entries_this_week: int = 0
    stop_loss_defined: bool = False
    evidence_window_hours: int = 24


class IngestionEvaluationBridge:
    """Persist, correlate, and evaluate normalized evidence without execution."""

    def __init__(
        self,
        policy: EvaluationPolicy | None = None,
        on_result: Callable[[EvaluationResult], None] | None = None,
        evidence_store: EvidenceStore | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.policy = policy or EvaluationPolicy()
        if self.policy.evidence_window_hours < 1:
            raise ValueError("evidence_window_hours must be positive")
        self.on_result = on_result
        self.evidence_store = evidence_store
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def process(self, records: list[NormalizedRecord]) -> list[EvaluationResult]:
        grouped: dict[str, list[NormalizedRecord]] = {}
        for record in records:
            asset = record.observation.asset.strip().upper()
            grouped.setdefault(asset, []).append(record)
            if self.evidence_store is not None:
                self.evidence_store.append(record)

        results: list[EvaluationResult] = []
        for asset, asset_records in grouped.items():
            evaluation_records = asset_records
            if self.evidence_store is not None:
                evaluation_records = self.evidence_store.window(
                    asset,
                    now=self.clock(),
                    hours=self.policy.evidence_window_hours,
                )

            proposal = TradeProposal(
                asset=asset,
                stop_loss_defined=self.policy.stop_loss_defined,
            )
            result = evaluate_records(
                asset=asset,
                status=self.policy.status,
                records=evaluation_records,
                proposal=proposal,
                new_entries_this_week=self.policy.new_entries_this_week,
            )
            results.append(result)
            if self.on_result is not None:
                self.on_result(result)
        return results
