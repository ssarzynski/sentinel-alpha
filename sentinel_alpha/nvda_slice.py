"""NVDA MVP vertical slice built on existing Sentinel Alpha safety controls."""

from dataclasses import dataclass

from .macro_regime import MacroRegimeResult
from .pipeline import EvaluationResult, evaluate_records
from .provenance import NormalizedRecord
from .risk_gate import TradeProposal
from .sec_ingestion import SecEdgarClient, filing_to_record

NVDA = "NVDA"
NVDA_CIK = "0001045810"


@dataclass(frozen=True)
class NvdaEvidenceBundle:
    """Evidence already normalized by authorized provider adapters."""

    records: tuple[NormalizedRecord, ...]
    macro: MacroRegimeResult | None = None
    conflicts: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.records:
            raise ValueError("NVDA evaluation requires evidence")
        wrong_assets = sorted(
            {record.observation.asset for record in self.records if record.observation.asset != NVDA}
        )
        if wrong_assets:
            raise ValueError(f"NVDA bundle contains non-NVDA evidence: {', '.join(wrong_assets)}")


def load_nvda_sec_evidence(client: SecEdgarClient) -> tuple[NormalizedRecord, ...]:
    """Load current watched NVIDIA filings from the existing SEC adapter.

    SEC filings are one provenance group regardless of how many filings are
    returned, so multiple filings can never manufacture independent confirmation.
    """
    filings = client.recent_watched_filings(NVDA_CIK)
    return tuple(filing_to_record(filing, NVDA) for filing in filings)


def evaluate_nvda_candidate(
    bundle: NvdaEvidenceBundle,
    *,
    stop_loss_defined: bool,
    new_entries_this_week: int,
) -> EvaluationResult:
    """Run NVDA evidence through the same confirmation and risk pipeline.

    This function cannot place a trade. It only returns a review decision and
    always relies on the shared risk gate for human-approval enforcement.
    """
    bundle.validate()
    proposal = TradeProposal(asset=NVDA, stop_loss_defined=stop_loss_defined)
    return evaluate_records(
        asset=NVDA,
        status="confirmed",
        records=list(bundle.records),
        proposal=proposal,
        new_entries_this_week=new_entries_this_week,
        conflicts=list(bundle.conflicts),
        macro=bundle.macro,
    )
