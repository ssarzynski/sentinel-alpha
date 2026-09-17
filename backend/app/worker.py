from __future__ import annotations

import logging
import os
import signal
import time
from datetime import datetime, timezone

from app.database import SessionLocal
from app.ingestion.sec_http import SecHttpClient, SecHttpConfig
from app.ingestion.sec_watchlist_worker import SecWatchItem
from app.services.scheduled_sec_runner import run_scheduled_sec_form4

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("sentinel.worker")
_STOP = False


def _stop(_signum, _frame) -> None:
    global _STOP
    _STOP = True


def parse_watchlist(value: str) -> list[SecWatchItem]:
    items: list[SecWatchItem] = []
    seen: set[tuple[str, str]] = set()
    for raw in value.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            ticker, cik = (part.strip() for part in raw.split(":", 1))
        except ValueError as exc:
            raise ValueError("watchlist entries must use TICKER:CIK") from exc
        if not ticker or not cik.isdigit():
            raise ValueError(f"invalid watchlist entry: {raw}")
        key = (ticker.upper(), cik.zfill(10))
        if key not in seen:
            seen.add(key)
            items.append(SecWatchItem(cik=key[1], ticker=key[0]))
    if not items:
        raise ValueError("SEC watchlist cannot be empty")
    return items


def run_once(items: list[SecWatchItem], client: SecHttpClient) -> None:
    started = datetime.now(timezone.utc)
    with SessionLocal() as db:
        try:
            result = run_scheduled_sec_form4(
                db, items=items, fetch_text=client.get_text, started_at=started,
                finished_at=lambda: datetime.now(timezone.utc),
                metadata={"worker": "periodic", "pid": os.getpid()},
            )
            db.commit()
            logger.info("SEC cycle %s: status=%s", result.reason, result.run.status if result.run else "none")
        except Exception:
            db.rollback()
            logger.exception("SEC ingestion cycle failed")


def main() -> None:
    global _STOP
    interval = int(os.getenv("SEC_POLL_INTERVAL_SECONDS", "900"))
    if interval < 60:
        raise ValueError("SEC_POLL_INTERVAL_SECONDS must be at least 60")
    items = parse_watchlist(os.getenv("SEC_WATCHLIST", "NVDA:1045810"))
    user_agent = os.getenv("SEC_USER_AGENT", "SentinelAlpha/0.1 research@example.com")
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    logger.info("SEC worker starting: watchlist=%d interval=%ds", len(items), interval)
    with SecHttpClient(SecHttpConfig(user_agent=user_agent)) as client:
        while not _STOP:
            run_once(items, client)
            deadline = time.monotonic() + interval
            while not _STOP and time.monotonic() < deadline:
                time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
    logger.info("SEC worker stopped")


if __name__ == "__main__":
    main()
