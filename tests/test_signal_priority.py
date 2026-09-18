from app.services.signal_intelligence import SignalIntelligence
from app.services.signal_priority import prioritize_signal


def signal(*,confirmations=1,state="developing",insider=False):
    return SignalIntelligence(asset="NVDA",evidence_count=confirmations,confirmation_count=confirmations,source_families=tuple(f"S{i}" for i in range(confirmations)),state=state,human_review_required=state=="confirmed_review",insider_sale_warning=insider,reasons=())


def test_one_confirmation_cannot_become_alert_eligible():
    result=prioritize_signal(signal(confirmations=1))
    assert result.attention_score==25
    assert result.priority=="monitor"
    assert result.eligible_for_alert is False
    assert result.human_review_required is False


def test_two_confirmations_enable_review_not_execution():
    result=prioritize_signal(signal(confirmations=2,state="confirmed_review"))
    assert result.attention_score==60
    assert result.priority=="review"
    assert result.eligible_for_alert is True
    assert result.human_review_required is True


def test_extra_independent_families_raise_attention_with_cap():
    result=prioritize_signal(signal(confirmations=5,state="confirmed_review"))
    assert result.attention_score==80
    assert result.priority=="high_review"
    assert result.human_review_required is True


def test_insider_sale_is_review_warning_not_confirmation():
    result=prioritize_signal(signal(confirmations=1,insider=True))
    assert result.attention_score==35
    assert result.eligible_for_alert is False
    assert "insider_sale_review_warning" in result.reasons


def test_withheld_signal_stays_withheld_even_with_warning():
    result=prioritize_signal(signal(confirmations=0,state="withheld",insider=True))
    assert result.priority=="withheld"
    assert result.eligible_for_alert is False
    assert result.attention_score==10
