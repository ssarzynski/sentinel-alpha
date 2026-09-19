from datetime import datetime, timezone
import sqlite3

import pytest

from sentinel_alpha.evidence_roles import ClassifiedEvidence, EvidenceRole
from sentinel_alpha.journal import EvaluationJournal
from sentinel_alpha.paper_operations import PaperOperationLedger
from sentinel_alpha.pipeline import evaluate_records
from sentinel_alpha.provenance import SourceIdentity, normalize_record
from sentinel_alpha.risk_gate import TradeProposal


def evaluation(confirmations=2, stop_loss=True):
    now = datetime.now(timezone.utc)
    records = [
        normalize_record(
            asset="BTC",
            metric="signal",
            value=True,
            source=SourceIdentity(f"source-{i}", f"Provider {i}", "fixture"),
            observed_at=now,
            statement=f"support {i}",
        )
        for i in range(confirmations)
    ]
    classified = [
        ClassifiedEvidence(record, EvidenceRole.SUPPORT, "paper fixture support")
        for record in records
    ]
    return evaluate_records(
        asset="BTC",
        status="confirmed",
        records=records,
        classified_evidence=classified,
        proposal=TradeProposal(asset="BTC", stop_loss_defined=stop_loss),
        new_entries_this_week=0,
    )


def test_paper_entry_requires_human_approval(tmp_path):
    ledger = PaperOperationLedger(tmp_path / "paper.db")
    with pytest.raises(ValueError, match="explicit human approval"):
        ledger.record(
            evaluation_id="eval-1",
            result=evaluation(),
            approved_by_human=False,
            hypothetical_action="paper_entry",
        )


def test_blocked_evaluation_cannot_be_paper_entry(tmp_path):
    ledger = PaperOperationLedger(tmp_path / "paper.db")
    with pytest.raises(ValueError, match="blocked evaluation"):
        ledger.record(
            evaluation_id="eval-1",
            result=evaluation(confirmations=1),
            approved_by_human=True,
            hypothetical_action="paper_entry",
        )


def test_approved_unblocked_paper_entry_is_recorded(tmp_path):
    database = tmp_path / "paper.db"
    result = evaluation()
    evaluation_id = EvaluationJournal(database).append(result)
    ledger = PaperOperationLedger(database)
    paper_id = ledger.record(
        evaluation_id=evaluation_id,
        result=result,
        approved_by_human=True,
        hypothetical_action="paper_entry",
        notes="hypothetical only",
        price=100.0,
        quantity=1.0,
    )
    rows = ledger.recent()
    assert rows[0].paper_id == paper_id
    assert rows[0].approved_by_human is True
    assert rows[0].hypothetical_action == "paper_entry"


def test_observe_can_record_blocked_evaluation_without_approval(tmp_path):
    ledger = PaperOperationLedger(tmp_path / "paper.db")
    ledger.record(
        evaluation_id="eval-1",
        result=evaluation(confirmations=1),
        approved_by_human=False,
        hypothetical_action="observe",
    )
    assert ledger.recent()[0].hypothetical_action == "observe"


def test_unsupported_action_fails_closed(tmp_path):
    ledger = PaperOperationLedger(tmp_path / "paper.db")
    with pytest.raises(ValueError, match="unsupported"):
        ledger.record(
            evaluation_id="eval-1",
            result=evaluation(),
            approved_by_human=True,
            hypothetical_action="buy",
        )


def test_lifecycle_entry_uses_authoritative_integrity_ledger(tmp_path):
    database = tmp_path / "paper.db"
    result = evaluation()
    evaluation_id = EvaluationJournal(database).append(result)
    ledger = PaperOperationLedger(database)
    paper_id = ledger.record(
        evaluation_id=evaluation_id,
        result=result,
        approved_by_human=True,
        hypothetical_action="paper_entry",
        price=100.0,
        quantity=2.0,
    )
    decision = ledger.recent()[0]
    assert decision.paper_id == paper_id
    assert decision.lifecycle_event_id is not None
    assert ledger.verify_integrity() is True


def test_lifecycle_exit_cannot_exceed_open_paper_position(tmp_path):
    database = tmp_path / "paper.db"
    result = evaluation()
    journal = EvaluationJournal(database)
    evaluation_id = journal.append(result)
    ledger = PaperOperationLedger(database)
    ledger.record(
        evaluation_id=evaluation_id,
        result=result,
        approved_by_human=True,
        hypothetical_action="paper_entry",
        price=100.0,
        quantity=1.0,
    )
    exit_evaluation_id = journal.append(result)
    with pytest.raises(ValueError, match="exceeds open paper position"):
        ledger.record(
            evaluation_id=exit_evaluation_id,
            result=result,
            approved_by_human=True,
            hypothetical_action="paper_exit",
            price=110.0,
            quantity=2.0,
        )


def test_lifecycle_event_requires_real_matching_evaluation(tmp_path):
    database = tmp_path / "paper.db"
    EvaluationJournal(database)
    ledger = PaperOperationLedger(database)
    with pytest.raises(ValueError, match="existing evaluation"):
        ledger.record(
            evaluation_id="missing",
            result=evaluation(),
            approved_by_human=True,
            hypothetical_action="paper_entry",
            price=100.0,
            quantity=1.0,
        )


def test_lifecycle_event_rolls_back_if_decision_insert_fails(tmp_path):
    database = tmp_path / "paper.db"
    result = evaluation()
    evaluation_id = EvaluationJournal(database).append(result)
    ledger = PaperOperationLedger(database)

    with sqlite3.connect(database) as connection:
        connection.execute(
            """CREATE TRIGGER reject_paper_decision
               BEFORE INSERT ON paper_decisions
               BEGIN SELECT RAISE(ABORT, 'forced decision failure'); END"""
        )

    with pytest.raises(sqlite3.IntegrityError, match="forced decision failure"):
        ledger.record(
            evaluation_id=evaluation_id,
            result=result,
            approved_by_human=True,
            hypothetical_action="paper_entry",
            price=100.0,
            quantity=1.0,
        )

    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM paper_events").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM paper_decisions").fetchone()[0] == 0
    assert ledger.verify_integrity() is True
