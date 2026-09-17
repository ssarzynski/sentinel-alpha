"""FastAPI service boundary for Sentinel Alpha."""

import os
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .journal import EvaluationJournal
from .pipeline import evaluate_records
from .providers import get_provider
from .risk_gate import TradeProposal

app = FastAPI(title="Sentinel Alpha", version="0.1.0")


def get_journal() -> EvaluationJournal:
    return EvaluationJournal(os.getenv("SENTINEL_DB_PATH", "sentinel_alpha.db"))


class EvidenceInput(BaseModel):
    provider: str
    observed_at: datetime
    payload: dict[str, Any]


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


@app.post("/v1/evaluate")
def evaluate(request: EvaluationInput) -> dict[str, Any]:
    records = [
        get_provider(item.provider).normalize(item.payload, item.observed_at)
        for item in request.evidence
    ]
    proposal = TradeProposal(
        asset=request.asset.strip().upper(),
        instrument_type=request.proposal.instrument_type,
        leverage=request.proposal.leverage,
        stop_loss_defined=request.proposal.stop_loss_defined,
        insider_selling_warning=request.proposal.insider_selling_warning,
    )
    result = evaluate_records(
        asset=request.asset,
        status=request.status,
        records=records,
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
