from __future__ import annotations

import logging
import os
import signal
import time
from datetime import datetime, timezone

from app.database import SessionLocal
from app.ingestion.sec_http import SecHttpClient, SecHttpConfig
from app.ingestion.sec_watchlist_worker import SecWatchItem
from app.services.ingestion_scheduler import run_scheduled_sec_form4_cycle

logger = logging.getLogger(__name__)
_stop = False


def _stop_handler(_signum, _frame) -> None:
    global _stop
    _stop = True


def _watchlist() -> list[SecWatchItem]:
    raw = os.getenv("SENTINEL_SEC_WATCHLIST", "1045810:NVDA")
    items: list[SecWatchItem] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            cik, ticker = token.split(":", 1)
        except ValueError as exc:
            raise ValueError("SENTINEL_SEC_WATCHLIST entries must use CIK:TICKER") from exc
        if not cik.strip() or not ticker.strip():
            raise ValueError("SENTINEL_SEC_WATCHLIST entries require CIK and ticker")
        items.append(SecWatchItem(cik.strip(), ticker.strip().upper()))
    if not items:
        raise ValueError("SEC watchlist cannot be empty")
    return items


def run_once() -> str:
    contact = os.environ["SENTINEL_SEC_CONTACT_EMAIL"]
    interval = int(os.getenv("SENTINEL_SEC_INTERVAL_MINUTES", "15"))
    max_running = int(os.getenv("SENTINEL_SEC_MAX_RUNNING_MINUTES", "30"))
    items = _watchlist()
    now = datetime.now(timezone.utc)
    config = SecHttpConfig(user_agent=f"SentinelAlpha/0.1 {contact}")
    with SessionLocal() as db, SecHttpClient(config) as client:
        decision, row = run_scheduled_sec_form4_cycle(
            db, items=items, fetch_text=client.get_text, now=now,
            finished_at=lambda: datetime.now(timezone.utc), interval_minutes=interval,
            max_running_minutes=max_running, metadata={"entrypoint": "sec_form4_worker"},
        )
        db.commit()
        if row is None:
            logger.info("SEC Form 4 cycle skipped: %s; next=%s", decision.reason, decision.next_due_at)
            return decision.reason
        logger.info("SEC Form 4 cycle %s: status=%s evidence=%s failures=%s",
                    row.run_key, row.status, row.evidence_rows, len(row.failures_json or []))
        return row.status


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    signal.signal(signal.SIGTERM, _stop_handler)
    signal.signal(signal.SIGINT, _stop_handler)
    poll_seconds = max(5, int(os.getenv("SENTINEL_SEC_POLL_SECONDS", "60")))
    logger.info("Starting Sentinel SEC Form 4 worker")
    while not _stop:
        try:
            run_once()
        except Exception:
            logger.exception("SEC Form 4 worker cycle failed")
        if not _stop:
            time.sleep(poll_seconds)
    logger.info("Sentinel SEC Form 4 worker stopped")


if __name__ == "__main__":
    main()
