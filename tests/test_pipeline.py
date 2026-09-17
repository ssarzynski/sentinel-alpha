from datetime import datetime, timezone

from sentinel_alpha.macro_regime import MacroRegime, MacroRegimeResult
from sentinel_alpha.pipeline import evaluate_records
from sentinel_alpha.provenance import SourceIdentity, normalize_record
from sentinel_alpha.risk_gate import TradeProposal

NOW = datetime(2026, 9, 17, tzinfo=timezone.utc)


def record(provider: str, channel: str, source_id: str):
    return normalize_record(
        asset="NVDA",
        metric="signal",
        value=True,
        source=SourceIdentity(source_id, provider, channel),
        observed_at=NOW,
        statement=f"confirmation from {provider}",
    )


def macro(regime: MacroRegime) -> MacroRegimeResult:
    return MacroRegimeResult(regime, 0, (), (), (), NOW)


def test_two_independent_sources_flow_to_human_review():
    result = evaluate_records(
        asset="NVDA",
        status="confirmed",
        records=[record("SEC", "filings", "sec"), record("Finviz", "screening", "finviz")],
        proposal=TradeProposal(asset="NVDA", stop_loss_defined=True),
        new_entries_this_week=0,
        macro=macro(MacroRegime.NEUTRAL),
    )
    assert result.decision.confirmation_count == 2
    assert result.decision.strong_alert is True
    assert result.risk.eligible_for_review is True
    assert result.risk.requires_human_approval is True
    assert result.macro.regime is MacroRegime.NEUTRAL


def test_macro_context_cannot_fake_second_confirmation():
    result = evaluate_records(
        asset="NVDA",
        status="confirmed",
        records=[record("SEC", "filings", "sec")],
        proposal=TradeProposal(asset="NVDA", stop_loss_defined=True),
        new_entries_this_week=0,
        macro=macro(MacroRegime.RISK_ON),
    )
    assert result.decision.confirmation_count == 1
    assert result.decision.strong_alert is False
    assert result.risk.blocked is True


def test_risk_off_macro_context_blocks_escalation_without_changing_confirmations():
    result = evaluate_records(
        asset="NVDA",
        status="confirmed",
        records=[record("SEC", "filings", "sec"), record("Finviz", "screening", "finviz")],
        proposal=TradeProposal(asset="NVDA", stop_loss_defined=True),
        new_entries_this_week=0,
        macro=macro(MacroRegime.RISK_OFF),
    )
    assert result.decision.confirmation_count == 2
    assert result.decision.blocked is True
    assert "macro_regime_risk_off" in result.signal.conflicts


def test_unknown_macro_context_fails_closed():
    result = evaluate_records(
        asset="BTC",
        status="confirmed",
        records=[record("Messari", "research", "messari"), record("Invo", "market", "invo")],
        proposal=TradeProposal(asset="BTC", stop_loss_defined=True),
        new_entries_this_week=0,
        macro=macro(MacroRegime.UNKNOWN),
    )
    assert result.decision.blocked is True
    assert "macro_context_unavailable" in result.signal.conflicts


def test_duplicate_provider_channel_cannot_fake_second_confirmation():
    result = evaluate_records(
        asset="BTC",
        status="confirmed",
        records=[
            record("Messari", "research", "messari-a"),
            record("Messari", "research", "messari-b"),
        ],
        proposal=TradeProposal(asset="BTC", stop_loss_defined=True),
        new_entries_this_week=0,
    )
    assert result.decision.confirmation_count == 1
    assert result.decision.strong_alert is False
    assert result.risk.blocked is True


def test_confirmed_signal_still_cannot_bypass_risk_gate():
    result = evaluate_records(
        asset="NVDA",
        status="confirmed",
        records=[record("SEC", "filings", "sec"), record("Finviz", "screening", "finviz")],
        proposal=TradeProposal(asset="NVDA", instrument_type="options", stop_loss_defined=True),
        new_entries_this_week=0,
        macro=macro(MacroRegime.RISK_ON),
    )
    assert result.decision.strong_alert is True
    assert result.risk.blocked is True
    assert "options_prohibited" in result.risk.reasons


def test_conflicting_evidence_blocks_entire_pipeline():
    result = evaluate_records(
        asset="ETH",
        status="confirmed",
        records=[record("Messari", "research", "messari"), record("Invo", "market", "invo")],
        proposal=TradeProposal(asset="ETH", stop_loss_defined=True),
        new_entries_this_week=0,
        conflicts=["material_source_conflict"],
    )
    assert result.decision.blocked is True
    assert result.risk.blocked is True
    assert "signal_not_eligible" in result.risk.reasons
