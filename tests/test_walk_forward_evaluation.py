from datetime import datetime, timedelta, timezone

import pytest

from sentinel_alpha.market_features import MarketFeatures
from sentinel_alpha.market_outcomes import ForwardOutcome
from sentinel_alpha.research_examples import ResearchExample
from sentinel_alpha.walk_forward import WalkForwardFold
from sentinel_alpha.walk_forward_evaluation import evaluate_condition_walk_forward

BASE=datetime(2020,1,1,tzinfo=timezone.utc)


def example(day, trend, outcome):
    moment=BASE+timedelta(days=day)
    features=MarketFeatures("NVDA",moment,day,100.0,None,None,None,None,trend)
    label=ForwardOutcome("NVDA",moment,100.0,5,moment+timedelta(days=5),100*(1+outcome),outcome)
    return ResearchExample("NVDA",moment,moment,moment+timedelta(days=5),features,(label,))


def test_same_condition_is_measured_separately_in_train_and_unseen_test():
    fold=WalkForwardFold(
        1,
        (example(1,0.2,0.10),example(2,-0.2,-0.05),example(3,0.3,0.20)),
        (example(4,0.1,-0.10),example(5,-0.1,0.15)),
    )
    result=evaluate_condition_walk_forward((fold,),condition=lambda x: x.features.trend_5 is not None and x.features.trend_5>0)[0]
    assert result.train_matches==2
    assert result.test_matches==1
    assert result.train[0].mean_return==pytest.approx(0.15)
    assert result.test[0].mean_return==pytest.approx(-0.10)


def test_no_test_matches_produces_empty_test_summary_not_fake_zero():
    fold=WalkForwardFold(1,(example(1,0.2,0.10),),(example(2,-0.2,-0.10),))
    result=evaluate_condition_walk_forward((fold,),condition=lambda x: x.features.trend_5>0)[0]
    assert result.test_matches==0
    assert result.test==()
