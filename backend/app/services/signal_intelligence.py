from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Evidence


@dataclass(frozen=True)
class EvidenceFact:
    asset: str
    source_family: str
    observed_at: datetime
    signal_eligible: bool = True
    insider_sale: bool = False


@dataclass(frozen=True)
class SignalIntelligence:
    asset: str
    evidence_count: int
    confirmation_count: int
    source_families: tuple[str, ...]
    state: str
    human_review_required: bool
    insider_sale_warning: bool
    reasons: tuple[str, ...]


def aggregate_signal_intelligence(asset: str, evidence: Iterable[EvidenceFact], *, now: datetime, max_age: timedelta = timedelta(days=7), min_confirmations: int = 2) -> SignalIntelligence:
    """Aggregate evidence without treating duplicate source families as confirmation."""
    if now.tzinfo is None: raise ValueError("now must be timezone-aware")
    if max_age <= timedelta(0) or min_confirmations < 2: raise ValueError("signal aggregation parameters are invalid")
    target=asset.upper().strip(); rows=[r for r in evidence if r.asset.upper().strip()==target]
    fresh=[r for r in rows if r.signal_eligible and r.observed_at.tzinfo is not None and timedelta(0)<=now-r.observed_at<=max_age]
    families=tuple(sorted({r.source_family.strip().upper() for r in fresh if r.source_family.strip()})); confirmations=len(families); reasons=[]
    if not rows: state="no_evidence"; reasons.append("no_evidence")
    elif not fresh: state="withheld"; reasons.append("no_fresh_signal_eligible_evidence")
    elif confirmations<min_confirmations: state="developing"; reasons.append("fewer_than_two_independent_evidence_confirmations")
    else: state="confirmed_review"; reasons.append("independent_confirmation_threshold_met")
    insider_warning=any(r.insider_sale for r in fresh)
    if insider_warning: reasons.append("insider_sale_warning")
    return SignalIntelligence(target,len(rows),confirmations,families,state,state=="confirmed_review",insider_warning,tuple(reasons))


def _bool(payload: dict, key: str, default: bool) -> bool:
    value=payload.get(key,default)
    return value if isinstance(value,bool) else default


def _utc(value: datetime) -> datetime:
    """Normalize ORM timestamps; SQLite commonly drops timezone metadata."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def evidence_fact(row: Evidence) -> EvidenceFact:
    """Translate persisted evidence conservatively; unknown facts never gain eligibility."""
    payload=row.payload_json or {}
    classification=payload.get("classification") if isinstance(payload.get("classification"),dict) else payload
    economic_type=str(classification.get("economic_type","")).lower()
    direction=str(classification.get("direction","")).lower()
    insider_sale=_bool(classification,"signal_eligible",False) and economic_type=="open_market" and direction in {"sale","sell","disposed"}
    return EvidenceFact(asset=row.asset or "",source_family=row.source_family,observed_at=_utc(row.observed_at),signal_eligible=_bool(classification,"signal_eligible",True),insider_sale=insider_sale)


def signal_intelligence_for_asset(db: Session, asset: str, *, now: datetime, max_age: timedelta = timedelta(days=7)) -> SignalIntelligence:
    target=asset.upper().strip()
    rows=list(db.scalars(select(Evidence).where(Evidence.asset==target).order_by(Evidence.observed_at.desc())).all())
    return aggregate_signal_intelligence(target,(evidence_fact(r) for r in rows),now=now.astimezone(timezone.utc),max_age=max_age)


def signal_intelligence_watchlist(db: Session, assets: Iterable[str], *, now: datetime, max_age: timedelta = timedelta(days=7)) -> list[dict]:
    """Read-only watchlist projection suitable for API serialization."""
    results=[]
    for asset in dict.fromkeys(a.upper().strip() for a in assets if a.strip()):
        item=asdict(signal_intelligence_for_asset(db,asset,now=now,max_age=max_age))
        item["source_families"]=list(item["source_families"]); item["reasons"]=list(item["reasons"]); results.append(item)
    return results
