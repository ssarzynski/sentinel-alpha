"""NVDA MVP vertical slice built on existing Sentinel Alpha safety controls."""

from dataclasses import dataclass

from .alpha_vantage_ingestion import AlphaVantageClient, daily_bar_to_records
from .evidence_roles import ClassifiedEvidence, EvidenceRole, classify_sec_record
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
    """Load current watched NVIDIA filings from the existing SEC adapter."""
    filings = client.recent_watched_filings(NVDA_CIK)
    return tuple(filing_to_record(filing, NVDA) for filing in filings)


def load_nvda_market_evidence(client: AlphaVantageClient) -> tuple[NormalizedRecord, ...]:
    """Load one independently-provenanced NVDA daily market observation group."""
    return daily_bar_to_records(client.latest_daily(NVDA))


def build_nvda_evidence(
    sec_client: SecEdgarClient,
    market_client: AlphaVantageClient,
    *,
    macro: MacroRegimeResult | None = None,
) -> NvdaEvidenceBundle:
    """Build the first end-to-end SEC + market NVDA evidence bundle."""
    records = load_nvda_sec_evidence(sec_client) + load_nvda_market_evidence(market_client)
    return NvdaEvidenceBundle(records=records, macro=macro)


def classify_nvda_evidence(records: tuple[NormalizedRecord, ...]) -> list[ClassifiedEvidence]:
    """Apply the current conservative NVDA semantic policy.

    Raw SEC filings are context until their event/transaction direction is
    parsed. Alpha Vantage market observations are explicit market SUPPORT.
    Other sources fail closed as CONTEXT in the shared pipeline.
    """
    classified: list[ClassifiedEvidence] = []
    for record in records:
        if record.source.independence_key == "sec":
            classified.append(classify_sec_record(record))
        elif record.source.independence_key == "alpha_vantage":
            classified.append(
                ClassifiedEvidence(
                    record,
                    EvidenceRole.SUPPORT,
                    "authorized independent NVDA market observation",
                )
            )
    return classified


def evaluate_nvda_candidate(
    bundle: NvdaEvidenceBundle,
    *,
    stop_loss_defined: bool,
    new_entries_this_week: int,
) -> EvaluationResult:
    """Run NVDA evidence through shared confirmation and risk controls only."""
    bundle.validate()
    proposal = TradeProposal(asset=NVDA, stop_loss_defined=stop_loss_defined)
    return evaluate_records(
        asset=NVDA,
        status="confirmed",
        records=list(bundle.records),
        classified_evidence=classify_nvda_evidence(bundle.records),
        proposal=proposal,
        new_entries_this_week=new_entries_this_week,
        conflicts=list(bundle.conflicts),
        macro=bundle.macro,
    )
