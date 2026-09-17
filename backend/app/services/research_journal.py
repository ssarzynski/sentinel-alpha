from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ResearchJournalEntry

STATUSES = {"proposed", "testing", "completed"}
DECISIONS = {"accepted", "rejected", "modified"}


def create_research_entry(
    db: Session,
    *,
    title: str,
    hypothesis: str,
    rationale: str,
    methodology: dict,
    evidence_ids: list[int] | None = None,
    prediction_ids: list[int] | None = None,
) -> ResearchJournalEntry:
    if not title.strip() or not hypothesis.strip() or not rationale.strip():
        raise ValueError("title, hypothesis, and rationale are required")
    if not methodology:
        raise ValueError("methodology is required")
    row = ResearchJournalEntry(
        research_key=str(uuid4()), version=1, title=title.strip(),
        hypothesis=hypothesis.strip(), rationale=rationale.strip(),
        methodology_json=dict(methodology),
        linked_evidence_ids_json=sorted(set(evidence_ids or [])),
        linked_prediction_ids_json=sorted(set(prediction_ids or [])),
        metrics_json={}, results_json={}, limitations_json=[],
        status="proposed", decision=None, production_rule_change_authorized=False,
    )
    db.add(row); db.flush(); return row


def create_research_version(
    db: Session,
    *,
    prior: ResearchJournalEntry,
    status: str,
    metrics: dict,
    results: dict,
    limitations: list[str],
    decision: str | None = None,
) -> ResearchJournalEntry:
    if status not in STATUSES:
        raise ValueError(f"unsupported research status: {status}")
    if decision is not None and decision not in DECISIONS:
        raise ValueError(f"unsupported research decision: {decision}")
    if decision is not None and status != "completed":
        raise ValueError("a research decision requires completed status")
    latest = db.scalar(
        select(func.max(ResearchJournalEntry.version)).where(
            ResearchJournalEntry.research_key == prior.research_key
        )
    ) or prior.version
    row = ResearchJournalEntry(
        research_key=prior.research_key, version=latest + 1,
        title=prior.title, hypothesis=prior.hypothesis, rationale=prior.rationale,
        methodology_json=dict(prior.methodology_json),
        linked_evidence_ids_json=list(prior.linked_evidence_ids_json),
        linked_prediction_ids_json=list(prior.linked_prediction_ids_json),
        metrics_json=dict(metrics), results_json=dict(results), limitations_json=list(limitations),
        status=status, decision=decision,
        production_rule_change_authorized=False,
    )
    db.add(row); db.flush(); return row
