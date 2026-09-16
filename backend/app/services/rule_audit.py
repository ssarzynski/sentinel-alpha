from __future__ import annotations

from dataclasses import asdict
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Evidence, RuleEvaluation
from app.scoring.rules import RuleResult


def independent_evidence(evidence: list[Evidence]) -> list[Evidence]:
    """Return one representative per independent source-family/category pair.

    Multiple stories or records from the same source family in the same evidence
    category do not inflate confirmation. Different evidence categories remain
    independent even when they originate from the same trusted family.
    """
    representatives: dict[tuple[str, str], Evidence] = {}
    for item in evidence:
        key = (item.source_family.strip().lower(), item.category.strip().lower())
        representatives.setdefault(key, item)
    return list(representatives.values())


def independent_confirmation_count(evidence: list[Evidence]) -> int:
    return len(independent_evidence(evidence))


def persist_rule_evaluation(
    db: Session,
    *,
    result: RuleResult,
    facts: dict,
    evidence: list[Evidence],
    asset: str | None = None,
    human_review_required: bool = True,
) -> RuleEvaluation:
    """Append one immutable audit snapshot. Never updates an existing evaluation."""
    independent = independent_evidence(evidence)
    row = RuleEvaluation(
        evaluation_key=str(uuid4()),
        rule_id=result.rule_id,
        rule_version=result.version,
        asset=asset,
        passed=result.passed,
        human_review_required=human_review_required,
        independent_confirmation_count=len(independent),
        facts_json=dict(facts),
        conditions_json=[asdict(condition) for condition in result.conditions],
        output_json=dict(result.output),
        evidence_ids_json=[item.id for item in evidence],
        evidence_categories_json=sorted({item.category for item in independent}),
        source_families_json=sorted({item.source_family for item in independent}),
    )
    db.add(row)
    db.flush()
    return row
