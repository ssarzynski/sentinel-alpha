"""FastAPI service boundary for Sentinel Alpha."""

import os
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .admin_api import router as admin_router
from .browser_auth import router as browser_auth_router
from .evidence_roles import ClassifiedEvidence, EvidenceRole
from .journal import EvaluationJournal
from .paper_operations import PaperOperationLedger
from .pipeline import evaluate_records
from .providers import get_provider
from .risk_gate import TradeProposal
from .security_headers import SecurityHeadersMiddleware

app = FastAPI(title="Sentinel Alpha", version="0.1.0")
app.add_middleware(SecurityHeadersMiddleware)
app.include_router(admin_router)
app.include_router(browser_auth_router)


def get_journal() -> EvaluationJournal:
    return EvaluationJournal(os.getenv("SENTINEL_DB_PATH", "sentinel_alpha.db"))


def get_paper_ledger() -> PaperOperationLedger:
    return PaperOperationLedger(os.getenv("SENTINEL_DB_PATH", "sentinel_alpha.db"))


class EvidenceInput(BaseModel):
    provider: str
    observed_at: datetime
    payload: dict[str, Any]
    role: EvidenceRole = EvidenceRole.CONTEXT
    rationale: str = "unclassified API evidence defaults to context"


class ProposalInput(BaseModel):
    instrument_type: str = "spot"
    leverage: float = Field(default=1.0, ge=1.0)
    stop_loss_defined: bool = False
    insider_selling_warning: bool = False


class EvaluationInput(BaseModel):
    asset: str = Field(min_length=1)
    status: str = Field(min_length=1)
    evidence: list[EvidenceInput] = Field(min_length=1)
    proposal: ProposalInput
    new_entries_this_week: int = Field(default=0, ge=0)
    conflicts: list[str] = Field(default_factory=list)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sentinel-alpha"}


@app.get("/v1/rules")
def rules() -> dict[str, Any]:
    return {
        "minimum_independent_confirmations": 2,
        "maximum_new_entries_per_week": 2,
        "options_allowed": False,
        "leverage_allowed": False,
        "risk_control_required_before_entry": True,
        "insider_selling": "warning_only",
        "human_approval_required": True,
        "automatic_trading": False,
        "unclassified_evidence": "context_only",
    }


@app.get("/v1/audit/verify")
def verify_audit_chain() -> dict[str, Any]:
    journal = get_journal()
    valid = journal.verify_integrity()
    return {"valid": valid, "status": "verified" if valid else "integrity_failure"}


@app.post("/v1/evaluate")
def evaluate(request: EvaluationInput) -> dict[str, Any]:
    try:
        records = [
            get_provider(item.provider).normalize(item.payload, item.observed_at)
            for item in request.evidence
        ]
        classified = [
            ClassifiedEvidence(record, item.role, item.rationale)
            for record, item in zip(records, request.evidence, strict=True)
        ]
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    expected_asset = request.asset.strip().upper()
    if any(record.observation.asset.strip().upper() != expected_asset for record in records):
        raise HTTPException(status_code=422, detail="evidence asset must match request asset")

    proposal = TradeProposal(
        asset=expected_asset,
        instrument_type=request.proposal.instrument_type,
        leverage=request.proposal.leverage,
        stop_loss_defined=request.proposal.stop_loss_defined,
        insider_selling_warning=request.proposal.insider_selling_warning,
    )
    result = evaluate_records(
        asset=expected_asset,
        status=request.status,
        records=records,
        classified_evidence=classified,
        proposal=proposal,
        new_entries_this_week=request.new_entries_this_week,
        conflicts=request.conflicts,
    )
    evaluation_id = get_journal().append(result)
    return {
        "evaluation_id": evaluation_id,
        "asset": result.signal.asset,
        "confirmations": result.decision.confirmation_count,
        "strong_alert": result.decision.strong_alert,
        "blocked": result.risk.blocked,
        "eligible_for_review": result.risk.eligible_for_review,
        "requires_human_approval": result.risk.requires_human_approval,
        "warnings": list(result.risk.warnings),
        "reasons": list(result.risk.reasons),
    }


@app.get("/v1/evaluations/{evaluation_id}")
def get_evaluation(evaluation_id: str) -> dict[str, Any]:
    stored = get_journal().get(evaluation_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="evaluation not found")
    return stored


@app.get("/v1/evaluations")
def recent_evaluations(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    return get_journal().recent(limit)


@app.get("/v1/paper-decisions")
def recent_paper_decisions(limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
    """Read-only paper-operation history for Sentinel Studio."""
    return [
        {
            "paper_id": item.paper_id,
            "evaluation_id": item.evaluation_id,
            "asset": item.asset,
            "created_at": item.created_at,
            "approved_by_human": item.approved_by_human,
            "hypothetical_action": item.hypothetical_action,
            "notes": item.notes,
        }
        for item in get_paper_ledger().recent(limit)
    ]


@app.get("/v1/dashboard/summary")
def dashboard_summary() -> dict[str, Any]:
    """Small read model for the production dashboard; performs no actions."""
    journal = get_journal()
    recent = journal.recent(50)
    paper = get_paper_ledger().recent(50)
    strong_alerts = sum(
        1 for item in recent if item["result"]["decision"].get("strong_alert") is True
    )
    blocked = sum(1 for item in recent if item["result"]["risk"].get("blocked") is True)
    return {
        "evaluation_count": len(recent),
        "strong_alert_count": strong_alerts,
        "blocked_count": blocked,
        "paper_decision_count": len(paper),
        "audit_chain_valid": journal.verify_integrity(),
        "automatic_trading": False,
        "human_approval_required": True,
    }
