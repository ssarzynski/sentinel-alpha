import pytest

from app.data_quality_gate import DataQualityGate
from app.signal_evaluation import EvidenceConfirmation, evaluate_signal, independent_confirmation_count, requested_alert_level


def quality(status="PASS", allowed=True):
    return DataQualityGate(status=status, risk_signals_allowed=allowed, findings=())


def test_confirmation_count_deduplicates_source_families():
    evidence=[EvidenceConfirmation("SEC"), EvidenceConfirmation("sec"), EvidenceConfirmation("exchange"), EvidenceConfirmation("news", accepted=False)]
    assert independent_confirmation_count(evidence)==2


def test_score_thresholds_are_deterministic():
    assert requested_alert_level(49.9)=="NONE"
    assert requested_alert_level(50)=="WATCH"
    assert requested_alert_level(80)=="STRONG"
    with pytest.raises(ValueError): requested_alert_level(80,strong_threshold=50,watch_threshold=50)


def test_strong_signal_passes_with_two_independent_confirmations_and_good_market_data():
    result=evaluate_signal("nvda",90,[EvidenceConfirmation("SEC"),EvidenceConfirmation("exchange")],quality())
    assert result.asset=="NVDA"
    assert result.requested_level=="STRONG"
    assert result.effective_level=="STRONG"
    assert result.allowed is True
    assert result.human_approval_required is True


def test_strong_signal_is_withheld_when_confirmation_rule_fails():
    result=evaluate_signal("NVDA",90,[EvidenceConfirmation("SEC"),EvidenceConfirmation("SEC")],quality())
    assert result.effective_level=="WITHHELD"
    assert result.allowed is False
    assert result.human_approval_required is False
    assert "fewer_than_two_independent_evidence_confirmations" in result.gate_reasons


def test_strong_signal_is_withheld_when_market_data_gate_blocks():
    result=evaluate_signal("BTC",90,[EvidenceConfirmation("exchange"),EvidenceConfirmation("institutional")],quality("WITHHOLD",False))
    assert result.effective_level=="WITHHELD"
    assert "market_data_withhold" in result.gate_reasons


def test_insider_selling_is_warning_not_automatic_rejection():
    result=evaluate_signal("NVDA",90,[EvidenceConfirmation("SEC"),EvidenceConfirmation("exchange")],quality(),insider_selling_warning=True)
    assert result.effective_level=="STRONG"
    assert "insider_selling" in result.warnings


def test_degraded_market_data_remains_visible_on_allowed_signal():
    result=evaluate_signal("ETH",90,[EvidenceConfirmation("exchange"),EvidenceConfirmation("institutional")],quality("DEGRADED",True))
    assert result.allowed is True
    assert "market_data_degraded" in result.warnings


def test_watch_signal_requires_human_approval_but_is_not_promoted():
    result=evaluate_signal("MSFT",60,[],quality("WITHHOLD",False))
    assert result.effective_level=="WATCH"
    assert result.human_approval_required is True
