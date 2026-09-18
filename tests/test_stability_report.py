import pytest

from sentinel_alpha.market_research import OutcomeSummary
from sentinel_alpha.stability_report import summarize_stability
from sentinel_alpha.walk_forward_evaluation import FoldEvaluation


def summary(mean, n=5):
    return OutcomeSummary(5,n,mean,mean,0.6,None,None)


def test_stability_reports_direction_and_effect_retention():
    evaluations=(
        FoldEvaluation(1,5,5,(summary(0.10),),(summary(0.05),)),
        FoldEvaluation(2,5,5,(summary(0.20),),(summary(-0.02),)),
    )
    result=summarize_stability(evaluations)[0]
    assert result.folds_with_test_evidence==2
    assert result.test_sample_size==10
    assert result.direction_agreement_rate==pytest.approx(0.5)
    assert result.mean_train_return==pytest.approx(0.15)
    assert result.mean_test_return==pytest.approx(0.015)
    assert result.effect_retention==pytest.approx(0.1)


def test_missing_test_evidence_is_not_converted_to_zero():
    evaluations=(FoldEvaluation(1,5,0,(summary(0.10),),()),)
    result=summarize_stability(evaluations)[0]
    assert result.folds_with_test_evidence==0
    assert result.test_sample_size==0
    assert result.mean_test_return is None
    assert result.effect_retention is None
