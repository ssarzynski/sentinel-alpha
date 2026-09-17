"""NVDA MVP vertical slice built on existing Sentinel Alpha safety controls."""

from dataclasses import dataclass

from .alpha_vantage_ingestion import AlphaVantageClient, daily_bar_to_records
from .evidence_roles import ClassifiedEvidence, classify_sec_record, classify_uninterpreted
from .macro_regime import MacroRegimeResult
from .pipeline import EvaluationResult, evaluate_records
from .provenance import NormalizedRecord
from .risk_gate import TradeProposal
from .sec_ingestion import SecEdgarClient, filing_to_record
from .sec_parsed_evidence import classify_sec_document

NVDA = "NVDA"
NVDA_CIK = "0001045810"


@dataclass(frozen=True)
class NvdaEvidenceBundle:
    """Evidence already normalized by authorized provider adapters."""

    records: tuple[NormalizedRecord, ...]
    macro: MacroRegimeResult | None = None
    conflicts: tuple[str, ...] = ()
    classified_evidence: tuple[ClassifiedEvidence, ...] = ()

    def validate(self) -> None:
        if not self.records:
            raise ValueError("NVDA evaluation requires evidence")
        wrong_assets = sorted(
            {record.observation.asset for record in self.records if record.observation.asset != NVDA}
        )
        if wrong_assets:
            raise ValueError(f"NVDA bundle contains non-NVDA evidence: {', '.join(wrong_assets)}")


def load_nvda_sec_evidence(client: SecEdgarClient) -> tuple[NormalizedRecord, ...]:
    """Load current watched NVIDIA filing metadata from the SEC adapter."""
    filings = client.recent_watched_filings(NVDA_CIK)
    return tuple(filing_to_record(filing, NVDA) for filing in filings)


def load_nvda_sec_classified_evidence(
    client: SecEdgarClient,
) -> tuple[tuple[NormalizedRecord, ...], tuple[ClassifiedEvidence, ...]]:
    """Fetch NVIDIA filing documents and classify parsed SEC facts fail closed."""
    records: list[NormalizedRecord] = []
    classified: list[ClassifiedEvidence] = []
    for filing in client.recent_watched_filings(NVDA_CIK):
        record = filing_to_record(filing, NVDA)
        records.append(record)
        try:
            document = client.fetch_filing_document(filing)
            classified.extend(classify_sec_document(record, form=filing.form, document=document))
        except (OSError, ValueError, UnicodeError):
            classified.append(classify_sec_record(record))
    return tuple(records), tuple(classified)


def load_nvda_market_evidence(client: AlphaVantageClient) -> tuple[NormalizedRecord, ...]:
    """Load NVDA daily market observations without assigning direction."""
    return daily_bar_to_records(client.latest_daily(NVDA))


def build_nvda_evidence(
    sec_client: SecEdgarClient,
    market_client: AlphaVantageClient,
    *,
    macro: MacroRegimeResult | None = None,
) -> NvdaEvidenceBundle:
    """Build the SEC + market NVDA observation bundle."""
    sec_records, sec_classified = load_nvda_sec_classified_evidence(sec_client)
    market_records = load_nvda_market_evidence(market_client)
    records = sec_records + market_records
    return NvdaEvidenceBundle(
        records=records,
        macro=macro,
        classified_evidence=sec_classified,
    )


def classify_nvda_evidence(records: tuple[NormalizedRecord, ...]) -> list[ClassifiedEvidence]:
    """Classify raw NVDA observations fail closed.

    Raw filing existence and raw daily close/volume are observations, not
    directional candidate support. Parsed SEC facts may override the raw SEC
    context classification when supplied by the evidence bundle.
    """
    classified: list[ClassifiedEvidence] = []
    for record in records:
        if record.source.independence_key == "sec":
            classified.append(classify_sec_record(record))
        else:
            classified.append(classify_uninterpreted(record))
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
    classified = (
        list(bundle.classified_evidence)
        if bundle.classified_evidence
        else classify_nvda_evidence(bundle.records)
    )
    return evaluate_records(
        asset=NVDA,
        status="confirmed",
        records=list(bundle.records),
        classified_evidence=classified,
        proposal=proposal,
        new_entries_this_week=new_entries_this_week,
        conflicts=list(bundle.conflicts),
        macro=bundle.macro,
    )
