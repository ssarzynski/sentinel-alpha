from sentinel_alpha.evidence_gate import EvidencePolicy, evaluate_evidence
from sentinel_alpha.stability_report import HorizonStability


def stability(folds=4,samples=40,agreement=0.75,retention=0.5):
    return HorizonStability(20,folds,samples,agreement,0.10,0.05,retention)


def test_sufficient_evidence_passes_all_predeclared_gates():
    result=evaluate_evidence(stability())
    assert result.sufficient is True
    assert result.reasons == ()


def test_sparse_unstable_evidence_fails_with_explicit_reasons():
    result=evaluate_evidence(stability(folds=1,samples=8,agreement=0.4,retention=0.1))
    assert result.sufficient is False
    assert result.reasons == (
        "too_few_test_folds","too_few_test_samples","unstable_direction","insufficient_effect_retention"
    )


def test_missing_statistics_fail_closed():
    item=HorizonStability(20,0,0,None,None,None,None)
    result=evaluate_evidence(item)
    assert result.sufficient is False
    assert "unstable_direction" in result.reasons
    assert "insufficient_effect_retention" in result.reasons


def test_policy_thresholds_are_configurable_not_hidden():
    policy=EvidencePolicy(min_test_folds=2,min_test_samples=10,min_direction_agreement=0.5,min_effect_retention=0.1)
    assert evaluate_evidence(stability(folds=2,samples=10,agreement=0.5,retention=0.1),policy).sufficient
