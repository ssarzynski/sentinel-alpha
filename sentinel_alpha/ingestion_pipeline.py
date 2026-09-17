"""Bridge normalized ingestion records into Sentinel Alpha evaluation."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from .evidence_roles import ClassifiedEvidence, classify_uninterpreted
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
    """Persist, correlate, and evaluate classified evidence without execution."""

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
        return self.process_classified([classify_uninterpreted(record) for record in records])

    def process_classified(self, items: list[ClassifiedEvidence]) -> list[EvaluationResult]:
        grouped: dict[str, list[ClassifiedEvidence]] = {}
        for item in items:
            asset = item.record.observation.asset.strip().upper()
            grouped.setdefault(asset, []).append(item)
            if self.evidence_store is not None:
                self.evidence_store.append_classified(item)

        results: list[EvaluationResult] = []
        for asset, asset_items in grouped.items():
            evaluation_items = asset_items
            if self.evidence_store is not None:
                evaluation_items = self.evidence_store.window_classified(
                    asset,
                    now=self.clock(),
                    hours=self.policy.evidence_window_hours,
                )

            evaluation_records = [item.record for item in evaluation_items]
            proposal = TradeProposal(
                asset=asset,
                stop_loss_defined=self.policy.stop_loss_defined,
            )
            result = evaluate_records(
                asset=asset,
                status=self.policy.status,
                records=evaluation_records,
                classified_evidence=evaluation_items,
                proposal=proposal,
                new_entries_this_week=self.policy.new_entries_this_week,
            )
            results.append(result)
            if self.on_result is not None:
                self.on_result(result)
        return results
