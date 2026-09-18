import pytest

from sentinel_alpha.research_trials import FIRST_REAL_DATA_TRIAL, ResearchTrialPlan, TrialHypothesis


def test_first_real_data_trial_is_small_and_predeclared():
    FIRST_REAL_DATA_TRIAL.validate()
    assert FIRST_REAL_DATA_TRIAL.symbols == ("NVDA", "SPY")
    assert FIRST_REAL_DATA_TRIAL.horizons == (5, 20, 60)
    assert len(FIRST_REAL_DATA_TRIAL.hypotheses) == 3


def test_trial_rejects_symbol_sprawl():
    plan=ResearchTrialPlan(
        symbols=("A","B","C","D","E"),horizons=(5,),
        hypotheses=(TrialHypothesis("x",lambda item: True),),
    )
    with pytest.raises(ValueError,match="symbol count"):
        plan.validate()


def test_trial_rejects_hypothesis_sprawl():
    hypotheses=tuple(TrialHypothesis(str(i),lambda item: True) for i in range(4))
    plan=ResearchTrialPlan(symbols=("NVDA",),horizons=(5,),hypotheses=hypotheses)
    with pytest.raises(ValueError,match="hypothesis count"):
        plan.validate()
