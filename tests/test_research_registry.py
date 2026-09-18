from sentinel_alpha.evidence_gate import EvidenceDecision
from sentinel_alpha.research_registry import ResearchRegistry


def test_equivalent_hypothesis_text_deduplicates():
    registry=ResearchRegistry()
    registry.record(" Positive   trend ",EvidenceDecision(20,False,("too_few_test_samples",)))
    found=registry.lookup("positive trend",20)
    assert found is not None
    assert found.sufficient is False
    assert len(registry)==1


def test_same_hypothesis_different_horizon_is_distinct():
    registry=ResearchRegistry()
    registry.record("positive trend",EvidenceDecision(5,False,("unstable_direction",)))
    registry.record("positive trend",EvidenceDecision(20,True,()))
    assert len(registry)==2
    assert registry.lookup("positive trend",5).sufficient is False
    assert registry.lookup("positive trend",20).sufficient is True


def test_registry_stores_no_market_payload_or_credentials():
    registry=ResearchRegistry()
    item=registry.record("volume expansion",EvidenceDecision(20,False,("too_few_test_folds",)))
    assert set(item.__dict__) == {"fingerprint","hypothesis","horizon","sufficient","reasons"}
