"""Bridge normalized ingestion records into Sentinel Alpha evaluation."""

from dataclasses import dataclass
from typing import Callable

from .pipeline import EvaluationResult, evaluate_records
from .provenance import NormalizedRecord
from .risk_gate import TradeProposal


@dataclass(frozen=True)
class EvaluationPolicy:
    status: str = "confirmed"
    new_entries_this_week: int = 0
    stop_loss_defined: bool = False


class IngestionEvaluationBridge:
    """Groups newly ingested evidence by asset and evaluates it without execution."""

    def __init__(
        self,
        policy: EvaluationPolicy | None = None,
        on_result: Callable[[EvaluationResult], None] | None = None,
    ) -> None:
        self.policy = policy or EvaluationPolicy()
        self.on_result = on_result

    def process(self, records: list[NormalizedRecord]) -> list[EvaluationResult]:
        grouped: dict[str, list[NormalizedRecord]] = {}
        for record in records:
            grouped.setdefault(record.observation.asset, []).append(record)

        results: list[EvaluationResult] = []
        for asset, asset_records in grouped.items():
            proposal = TradeProposal(
                asset=asset,
                stop_loss_defined=self.policy.stop_loss_defined,
            )
            result = evaluate_records(
                asset=asset,
                status=self.policy.status,
                records=asset_records,
                proposal=proposal,
                new_entries_this_week=self.policy.new_entries_this_week,
            )
            results.append(result)
            if self.on_result is not None:
                self.on_result(result)
        return results
