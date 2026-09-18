from datetime import datetime, timedelta, timezone

from sentinel_alpha.market_features import MarketFeatures
from sentinel_alpha.research_dataset import ResearchDataset
from sentinel_alpha.research_examples import ResearchExample
from sentinel_alpha.walk_forward import walk_forward_splits

BASE = datetime(2020, 1, 1, tzinfo=timezone.utc)


def example(day):
    moment = BASE + timedelta(days=day)
    features = MarketFeatures("NVDA", moment, day, 100.0, None, None, None, None, None)
    return ResearchExample("NVDA", moment, moment, moment, features, ())


def dataset(count):
    items = tuple(example(day) for day in range(1, count + 1))
    return ResearchDataset("NVDA", BASE + timedelta(days=count + 1), items, 0)


def test_expanding_walk_forward_never_trains_on_future_test_examples():
    folds = walk_forward_splits(dataset(12), min_train=6, test_size=2, step=2)
    assert len(folds) == 3
    assert [len(fold.train) for fold in folds] == [6, 8, 10]
    assert all(fold.train_end < fold.test_start for fold in folds)
    assert folds[0].test[0].anchor_at == BASE + timedelta(days=7)
    assert folds[-1].test[-1].anchor_at == BASE + timedelta(days=12)


def test_input_order_cannot_break_chronology():
    original = dataset(8)
    reversed_dataset = ResearchDataset(original.symbol, original.dataset_known_by, tuple(reversed(original.examples)), 0)
    folds = walk_forward_splits(reversed_dataset, min_train=4, test_size=2)
    assert folds[0].train_end < folds[0].test_start
    assert folds[0].train[0].anchor_at == BASE + timedelta(days=1)


def test_insufficient_history_returns_no_folds():
    assert walk_forward_splits(dataset(5), min_train=5, test_size=1) == ()
