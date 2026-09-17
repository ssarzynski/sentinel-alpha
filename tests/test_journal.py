from datetime import datetime, timezone

import pytest

from sentinel_alpha.journal import EvaluationJournal
from sentinel_alpha.pipeline import evaluate_records
from sentinel_alpha.provenance import SourceIdentity, normalize_record
from sentinel_alpha.risk_gate import TradeProposal


def evaluation():
    now = datetime.now(timezone.utc)
    records = [
        normalize_record(
            asset="NVDA",
            metric="signal",
            value=True,
            source=SourceIdentity("sec", "SEC", "filings"),
            observed_at=now,
            statement="SEC confirmation",
        ),
        normalize_record(
            asset="NVDA",
            metric="signal",
            value=True,
            source=SourceIdentity("finviz", "Finviz", "screening"),
            observed_at=now,
            statement="Finviz confirmation",
        ),
    ]
    return evaluate_records(
        asset="NVDA",
        status="confirmed",
        records=records,
        proposal=TradeProposal(asset="NVDA", stop_loss_defined=True),
        new_entries_this_week=0,
    )


def test_append_and_get_round_trip(tmp_path):
    journal = EvaluationJournal(tmp_path / "journal.db")
    evaluation_id = journal.append(evaluation())
    stored = journal.get(evaluation_id)
    assert stored is not None
    assert stored["evaluation_id"] == evaluation_id
    assert stored["asset"] == "NVDA"
    assert stored["result"]["decision"]["confirmation_count"] == 2
    assert stored["result"]["risk"]["requires_human_approval"] is True


def test_recent_returns_newest_first(tmp_path):
    journal = EvaluationJournal(tmp_path / "journal.db")
    first = journal.append(evaluation())
    second = journal.append(evaluation())
    rows = journal.recent()
    assert len(rows) == 2
    assert {rows[0]["evaluation_id"], rows[1]["evaluation_id"]} == {first, second}


def test_unknown_evaluation_returns_none(tmp_path):
    journal = EvaluationJournal(tmp_path / "journal.db")
    assert journal.get("missing") is None


def test_recent_limit_is_bounded(tmp_path):
    journal = EvaluationJournal(tmp_path / "journal.db")
    with pytest.raises(ValueError, match="between 1 and 200"):
        journal.recent(201)
