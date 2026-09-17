from datetime import datetime, timezone

from sentinel_alpha.evidence_roles import ClassifiedEvidence, EvidenceRole
from sentinel_alpha.macro_regime import MacroRegime, MacroRegimeResult
from sentinel_alpha.pipeline import evaluate_records
from sentinel_alpha.provenance import SourceIdentity, normalize_record
from sentinel_alpha.risk_gate import TradeProposal

NOW = datetime(2026, 9, 17, tzinfo=timezone.utc)


def record(provider: str, channel: str, source_id: str):
    return normalize_record(asset="NVDA", metric="signal", value=True, source=SourceIdentity(source_id, provider, channel), observed_at=NOW, statement=f"confirmation from {provider}")


def support(records):
    return [ClassifiedEvidence(item, EvidenceRole.SUPPORT, "test semantic support") for item in records]


def macro(regime: MacroRegime) -> MacroRegimeResult:
    return MacroRegimeResult(regime, 0, (), (), (), NOW)


def evaluate(records, *, asset="NVDA", macro_context=None, proposal=None, conflicts=None):
    return evaluate_records(asset=asset, status="confirmed", records=records, classified_evidence=support(records), proposal=proposal or TradeProposal(asset=asset, stop_loss_defined=True), new_entries_this_week=0, macro=macro_context, conflicts=conflicts)


def test_two_independent_sources_flow_to_human_review():
    result = evaluate([record("SEC", "filings", "sec"), record("Finviz", "screening", "finviz")], macro_context=macro(MacroRegime.NEUTRAL))
    assert result.decision.confirmation_count == 2
    assert result.decision.strong_alert is True
    assert result.risk.eligible_for_review is True
    assert result.risk.requires_human_approval is True


def test_macro_context_cannot_fake_second_confirmation():
    result = evaluate([record("SEC", "filings", "sec")], macro_context=macro(MacroRegime.RISK_ON))
    assert result.decision.confirmation_count == 1
    assert result.decision.strong_alert is False


def test_risk_off_macro_context_blocks_escalation_without_changing_confirmations():
    result = evaluate([record("SEC", "filings", "sec"), record("Finviz", "screening", "finviz")], macro_context=macro(MacroRegime.RISK_OFF))
    assert result.decision.confirmation_count == 2
    assert result.decision.blocked is True
    assert "macro_regime_risk_off" in result.signal.conflicts


def test_unknown_macro_context_fails_closed():
    records = [record("Messari", "research", "messari"), record("Invo", "market", "invo")]
    result = evaluate(records, asset="BTC", macro_context=macro(MacroRegime.UNKNOWN))
    assert result.decision.blocked is True
    assert "macro_context_unavailable" in result.signal.conflicts


def test_duplicate_provider_channel_cannot_fake_second_confirmation():
    records = [record("Messari", "research", "messari-a"), record("Messari", "research", "messari-b")]
    result = evaluate(records, asset="BTC")
    assert result.decision.confirmation_count == 1
    assert result.decision.strong_alert is False


def test_confirmed_signal_still_cannot_bypass_risk_gate():
    records = [record("SEC", "filings", "sec"), record("Finviz", "screening", "finviz")]
    result = evaluate(records, proposal=TradeProposal(asset="NVDA", instrument_type="options", stop_loss_defined=True), macro_context=macro(MacroRegime.RISK_ON))
    assert result.decision.strong_alert is True
    assert result.risk.blocked is True
    assert "options_prohibited" in result.risk.reasons


def test_conflicting_evidence_blocks_entire_pipeline():
    records = [record("Messari", "research", "messari"), record("Invo", "market", "invo")]
    result = evaluate(records, asset="ETH", conflicts=["material_source_conflict"])
    assert result.decision.blocked is True
    assert result.risk.blocked is True
