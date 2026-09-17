"""BTC MVP vertical slice built on shared Sentinel Alpha safety controls."""

from dataclasses import dataclass

from .evidence_roles import ClassifiedEvidence, classify_uninterpreted
from .macro_regime import MacroRegimeResult
from .messari_ingestion import MessariClient
from .pipeline import EvaluationResult, evaluate_records
from .provenance import NormalizedRecord
from .risk_gate import TradeProposal

BTC = "BTC"


@dataclass(frozen=True)
class BtcEvidenceBundle:
    """Normalized BTC observations plus explicitly classified semantics."""

    records: tuple[NormalizedRecord, ...]
    macro: MacroRegimeResult | None = None
    conflicts: tuple[str, ...] = ()
    classified_evidence: tuple[ClassifiedEvidence, ...] = ()

    def validate(self) -> None:
        if not self.records:
            raise ValueError("BTC evaluation requires evidence")
        wrong_assets = sorted(
            {record.observation.asset for record in self.records if record.observation.asset != BTC}
        )
        if wrong_assets:
            raise ValueError(f"BTC bundle contains non-BTC evidence: {', '.join(wrong_assets)}")


def load_btc_market_evidence(
    client: MessariClient,
    asset_identifier: str = "bitcoin",
    *,
    granularity: str = "1h",
) -> tuple[NormalizedRecord, ...]:
    """Load BTC market observations without assigning directional support."""
    return tuple(client.price_records(BTC, asset_identifier, granularity=granularity))


def build_btc_evidence(
    client: MessariClient,
    *,
    asset_identifier: str = "bitcoin",
    granularity: str = "1h",
    macro: MacroRegimeResult | None = None,
) -> BtcEvidenceBundle:
    """Build the BTC market observation bundle.

    Messari market and research records share one provider independence group.
    Raw price observations remain CONTEXT until a versioned crypto semantic rule
    classifies them; this slice cannot manufacture a strong alert from one feed.
    """
    return BtcEvidenceBundle(
        records=load_btc_market_evidence(
            client, asset_identifier=asset_identifier, granularity=granularity
        ),
        macro=macro,
    )


def classify_btc_evidence(
    records: tuple[NormalizedRecord, ...],
) -> list[ClassifiedEvidence]:
    """Fail closed: raw BTC observations are context, never automatic support."""
    return [classify_uninterpreted(record) for record in records]


def evaluate_btc_candidate(
    bundle: BtcEvidenceBundle,
    *,
    stop_loss_defined: bool,
    new_entries_this_week: int,
) -> EvaluationResult:
    """Run BTC evidence through shared confirmation and risk controls only."""
    bundle.validate()
    proposal = TradeProposal(asset=BTC, stop_loss_defined=stop_loss_defined)
    classified = (
        list(bundle.classified_evidence)
        if bundle.classified_evidence
        else classify_btc_evidence(bundle.records)
    )
    return evaluate_records(
        asset=BTC,
        status="confirmed",
        records=list(bundle.records),
        classified_evidence=classified,
        proposal=proposal,
        new_entries_this_week=new_entries_this_week,
        conflicts=list(bundle.conflicts),
        macro=bundle.macro,
    )
