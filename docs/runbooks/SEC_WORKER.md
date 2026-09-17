# SEC Worker Operations Runbook

## Purpose
The `sec-worker` service periodically ingests SEC Form 4 evidence independently of the FastAPI web process.

## Configuration
- `SEC_WATCHLIST`: comma-separated `TICKER:CIK` entries, e.g. `NVDA:1045810,MSFT:789019`.
- `SEC_POLL_INTERVAL_SECONDS`: polling interval; minimum 60 seconds. Compose default is 900 seconds.
- `SEC_USER_AGENT`: SEC-compliant identifying User-Agent. Production deployments must replace the development placeholder with a monitored contact identity.
- `DATABASE_URL`: PostgreSQL SQLAlchemy URL.

## Start
`docker compose up -d sec-worker`

For the complete local stack use `docker compose up`.

## Observe
Use Sentinel Studio or authenticated endpoints:
- `/api/studio/ingestion/health?source=SEC_FORM4`
- `/api/studio/ingestion/runs?source=SEC_FORM4&limit=50`

Container diagnostics: `docker compose ps` and `docker compose logs sec-worker`.

## Status interpretation
- `completed`: cycle completed without recorded company-level failures.
- `completed_with_errors`: cycle finished but one or more watched companies failed.
- `failed`: fatal job-level exception occurred.
- `skipped_overlap`: another worker owned the PostgreSQL advisory lock; duplicate execution was intentionally skipped.
- `stale`: Studio health considers the latest run older than the configured threshold.
- `never_run`: no persistent run exists for the source.

## Failure handling
The worker rolls back a failed database transaction and logs the exception. Do not interpret a failed/stale run as evidence that no insider activity occurred. Restore ingestion health first, then reassess the affected evidence window.

## Deployment safety
Multiple worker containers may exist, but PostgreSQL advisory locking prevents concurrent `SEC_FORM4` cycles. This is defense in depth; record-level deduplication remains required.

## Acceptance check
CI must validate Compose configuration, build application images, start the core stack, reach `/api/health` through Nginx, verify Alembic state, start `sec-worker`, confirm the process remains running, and tear down the environment cleanly.
