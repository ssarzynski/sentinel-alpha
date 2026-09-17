from app.data_quality_gate import DataQualityGate, DataQualityFinding
from app.signal_quality_gate import gate_signal_level


def quality(status="PASS", allowed=True):
    findings = () if allowed else (DataQualityFinding("NVDA", "stale_market_data", "block", "stale"),)
    return DataQualityGate(status=status, risk_signals_allowed=allowed, findings=findings)


def test_strong_alert_requires_two_independent_evidence_confirmations():
    result = gate_signal_level("STRONG", independent_evidence_confirmations=1, market_quality=quality())
    assert result.allowed is False
    assert result.effective_level == "WITHHELD"
    assert "fewer_than_two_independent_evidence_confirmations" in result.reasons


def test_strong_alert_is_withheld_when_market_quality_blocks_risk_signals():
    result = gate_signal_level("STRONG", independent_evidence_confirmations=2, market_quality=quality("WITHHOLD", False))
    assert result.allowed is False
    assert result.effective_level == "WITHHELD"
    assert "market_data_withhold" in result.reasons


def test_strong_alert_passes_only_when_both_prerequisites_pass():
    result = gate_signal_level("STRONG", independent_evidence_confirmations=2, market_quality=quality())
    assert result.allowed is True
    assert result.effective_level == "STRONG"
    assert result.reasons == ()


def test_degraded_market_data_may_pass_when_gate_still_allows_risk_signals():
    result = gate_signal_level("STRONG", independent_evidence_confirmations=2, market_quality=quality("DEGRADED", True))
    assert result.allowed is True
    assert result.effective_level == "STRONG"


def test_non_strong_alert_is_not_promoted_or_rewritten_by_strong_gate():
    result = gate_signal_level("WATCH", independent_evidence_confirmations=0, market_quality=quality("WITHHOLD", False))
    assert result.allowed is True
    assert result.effective_level == "WATCH"
