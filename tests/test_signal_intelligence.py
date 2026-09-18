from datetime import datetime, timedelta, timezone

from app.services.signal_intelligence import EvidenceFact, aggregate_signal_intelligence

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)


def fact(family: str, *, days: int = 0, insider_sale: bool = False, eligible: bool = True):
    return EvidenceFact("NVDA", family, NOW - timedelta(days=days), eligible, insider_sale)


def test_many_sec_records_count_as_one_confirmation():
    result = aggregate_signal_intelligence("NVDA", [fact("SEC"), fact("SEC"), fact("SEC")], now=NOW)
    assert result.evidence_count == 3
    assert result.confirmation_count == 1
    assert result.source_families == ("SEC",)
    assert result.state == "developing"
    assert not result.human_review_required


def test_two_independent_families_meet_confirmation_threshold_but_require_human_review():
    result = aggregate_signal_intelligence("nvda", [fact("SEC"), fact("MARKET")], now=NOW)
    assert result.confirmation_count == 2
    assert result.state == "confirmed_review"
    assert result.human_review_required
    assert "independent_confirmation_threshold_met" in result.reasons


def test_stale_or_ineligible_evidence_cannot_supply_second_confirmation():
    result = aggregate_signal_intelligence("NVDA", [fact("SEC"), fact("MARKET", days=8), fact("NEWS", eligible=False)], now=NOW)
    assert result.confirmation_count == 1
    assert result.state == "developing"


def test_insider_sale_is_warning_not_extra_confirmation():
    result = aggregate_signal_intelligence("NVDA", [fact("SEC", insider_sale=True), fact("SEC")], now=NOW)
    assert result.confirmation_count == 1
    assert result.insider_sale_warning
    assert "insider_sale_warning" in result.reasons


def test_no_fresh_eligible_evidence_is_withheld():
    result = aggregate_signal_intelligence("NVDA", [fact("SEC", days=10)], now=NOW)
    assert result.state == "withheld"
    assert result.confirmation_count == 0
    assert not result.human_review_required
