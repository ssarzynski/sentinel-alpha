import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models import User
from app.services.ingestion_monitor import ingestion_health, latest_ingestion_runs
from app.services.portfolios import create_portfolio, list_portfolios, owned_portfolio, portfolio_analytics, portfolio_positions, upsert_position
from app.services.sec_filings import latest_filings, sync_company_filings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PortfolioCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    base_currency: str = Field(default="USD", min_length=3, max_length=8)
    policy: dict = Field(default_factory=dict)


class PositionUpsertRequest(BaseModel):
    asset: str = Field(min_length=1, max_length=32)
    asset_class: str = Field(min_length=1, max_length=32)
    quantity: float
    cost_basis: float | None = None
    mark_price: float = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=8)
    price_source: str = Field(min_length=1, max_length=64)
    price_observed_at: datetime
    metadata: dict = Field(default_factory=dict)


def _portfolio_or_404(db: Session, user: User, key: str):
    row = owned_portfolio(db, user, key)
    if row is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return row


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sentinel-alpha", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    logger.info("Registered user %s", user.email)
    return TokenResponse(access_token=create_access_token(user.email))


@router.post("/auth/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return TokenResponse(access_token=create_access_token(user.email))


@router.get("/auth/me")
def me(user: User = Depends(get_current_user)) -> dict[str, str | int]:
    return {"id": user.id, "email": user.email}


@router.post("/portfolios", status_code=status.HTTP_201_CREATED)
def create_portfolio_endpoint(payload: PortfolioCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict[str, object]:
    row = create_portfolio(db, user, name=payload.name, base_currency=payload.base_currency, policy=payload.policy)
    return {"portfolio_key": row.portfolio_key, "name": row.name, "base_currency": row.base_currency, "status": row.status, "policy": row.policy_json}


@router.get("/portfolios")
def list_portfolios_endpoint(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict[str, object]]:
    return [{"portfolio_key": r.portfolio_key, "name": r.name, "base_currency": r.base_currency, "status": r.status, "policy": r.policy_json} for r in list_portfolios(db, user)]


@router.put("/portfolios/{portfolio_key}/positions")
def upsert_position_endpoint(portfolio_key: str, payload: PositionUpsertRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict[str, object]:
    portfolio = _portfolio_or_404(db, user, portfolio_key)
    row = upsert_position(db, portfolio, asset=payload.asset, asset_class=payload.asset_class, quantity=payload.quantity, cost_basis=payload.cost_basis, mark_price=payload.mark_price, currency=payload.currency, price_source=payload.price_source, price_observed_at=payload.price_observed_at, metadata=payload.metadata)
    return {"asset": row.asset, "asset_class": row.asset_class, "quantity": row.quantity, "cost_basis": row.cost_basis, "mark_price": row.mark_price, "market_value": row.market_value, "currency": row.currency, "price_source": row.price_source, "price_observed_at": row.price_observed_at.isoformat()}


@router.get("/portfolios/{portfolio_key}/positions")
def positions_endpoint(portfolio_key: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict[str, object]]:
    portfolio = _portfolio_or_404(db, user, portfolio_key)
    return [{"asset": r.asset, "asset_class": r.asset_class, "quantity": r.quantity, "cost_basis": r.cost_basis, "mark_price": r.mark_price, "market_value": r.market_value, "currency": r.currency, "price_source": r.price_source, "price_observed_at": r.price_observed_at.isoformat(), "metadata": r.metadata_json} for r in portfolio_positions(db, portfolio)]


@router.get("/portfolios/{portfolio_key}/analytics")
def analytics_endpoint(portfolio_key: str, stale_after_minutes: int = Query(default=30, ge=1, le=10080), db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict[str, object]:
    portfolio = _portfolio_or_404(db, user, portfolio_key)
    result = portfolio_analytics(db, portfolio, as_of=datetime.now(timezone.utc), stale_after_minutes=stale_after_minutes)
    return {"nav": result.nav, "gross_exposure": result.gross_exposure, "net_exposure": result.net_exposure, "largest_position_weight": result.largest_position_weight, "herfindahl_index": result.herfindahl_index, "stale_assets": list(result.stale_assets), "asset_class_exposure": result.asset_class_exposure, "positions": [{"asset": p.asset, "asset_class": p.asset_class, "market_value": p.market_value, "weight": p.weight, "stale_price": p.stale_price} for p in result.positions]}


@router.post("/sec/sync/{ticker}")
def sync_sec_filings(ticker: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict[str, int | str]:
    try:
        return sync_company_filings(db, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception:
        logger.exception("SEC sync failed for %s", ticker)
        raise HTTPException(status_code=502, detail="SEC EDGAR sync failed")


@router.get("/sec/filings")
def get_sec_filings(ticker: str | None = None, limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict[str, object]]:
    filings = latest_filings(db, ticker=ticker, limit=limit)
    return [{"id": f.id, "ticker": f.ticker, "company_name": f.company_name, "cik": f.cik, "accession_number": f.accession_number, "form": f.form, "filing_date": f.filing_date.isoformat(), "report_date": f.report_date.isoformat() if f.report_date else None, "filing_url": f.filing_url, "source": f.source, "ingested_at": f.ingested_at.isoformat() if f.ingested_at else None} for f in filings]


@router.get("/studio/ingestion/runs")
def studio_ingestion_runs(source: str | None = None, limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict[str, object]]:
    rows = latest_ingestion_runs(db, source=source, limit=limit)
    return [{"run_key": r.run_key, "source": r.source, "status": r.status, "started_at": r.started_at.isoformat(), "finished_at": r.finished_at.isoformat() if r.finished_at else None, "checked": r.checked, "discovered": r.discovered, "new_records": r.new_records, "skipped_existing": r.skipped_existing, "evidence_rows": r.evidence_rows, "failures": r.failures_json, "config": r.config_json, "metadata": r.metadata_json} for r in rows]


@router.get("/studio/ingestion/health")
def studio_ingestion_health(source: str = "SEC_FORM4", stale_after_minutes: int = Query(default=60, ge=1, le=10080), db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict[str, object]:
    result = ingestion_health(db, source=source, now=datetime.now(timezone.utc), stale_after_minutes=stale_after_minutes)
    for field in ("started_at", "finished_at"):
        if result.get(field): result[field] = result[field].isoformat()
    return result
