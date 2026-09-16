import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models import User
from app.services.sec_filings import latest_filings, sync_company_filings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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


@router.post("/sec/sync/{ticker}")
def sync_sec_filings(
    ticker: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, int | str]:
    try:
        return sync_company_filings(db, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception:
        logger.exception("SEC sync failed for %s", ticker)
        raise HTTPException(status_code=502, detail="SEC EDGAR sync failed")


@router.get("/sec/filings")
def get_sec_filings(
    ticker: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict[str, object]]:
    filings = latest_filings(db, ticker=ticker, limit=limit)
    return [
        {
            "id": filing.id,
            "ticker": filing.ticker,
            "company_name": filing.company_name,
            "cik": filing.cik,
            "accession_number": filing.accession_number,
            "form": filing.form,
            "filing_date": filing.filing_date.isoformat(),
            "report_date": filing.report_date.isoformat() if filing.report_date else None,
            "filing_url": filing.filing_url,
            "source": filing.source,
            "ingested_at": filing.ingested_at.isoformat() if filing.ingested_at else None,
        }
        for filing in filings
    ]
