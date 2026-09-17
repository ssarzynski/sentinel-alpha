# Milestone 6 SEC + Sentinel Studio API

All routes use the `/api` prefix. Except `/health` and authentication routes, operational routes require a valid Bearer token.

## Health
`GET /api/health`

Public process health endpoint used by Docker Compose CI and infrastructure probes.

## SEC filing synchronization
`POST /api/sec/sync/{ticker}`

Authenticated. Runs an on-demand supported-company SEC filing synchronization. Unknown tickers return 404; upstream SEC failures are surfaced as 502 while server-side logs retain diagnostic detail.

## SEC filings
`GET /api/sec/filings?ticker=NVDA&limit=50`

Authenticated. Returns normalized SEC filing records. `ticker` is optional and `limit` is constrained to 1–200.

Key response fields include ticker, company name, CIK, accession number, form, filing/report dates, filing URL, source and ingestion timestamp.

## Studio ingestion runs
`GET /api/studio/ingestion/runs?source=SEC_FORM4&limit=50`

Authenticated. Returns recent persistent ingestion runs ordered newest first. Operational fields include run key, source, status, start/finish timestamps, checked/discovered/new/skipped/evidence counts, failures, configuration and metadata.

Expected statuses include `completed`, `completed_with_errors`, `failed` and `skipped_overlap`.

## Studio ingestion health
`GET /api/studio/ingestion/health?source=SEC_FORM4&stale_after_minutes=60`

Authenticated. Summarizes the latest run for one source. Health semantics distinguish successful/recent operation from failed, error-containing, stale and never-run states. `stale_after_minutes` is constrained to 1–10080.

## Authentication
`POST /api/auth/register` creates a user and returns a Bearer token. `POST /api/auth/login` uses OAuth2 form fields. `GET /api/auth/me` verifies the current token and returns the current user identity.

## Safety boundary
These endpoints expose research evidence and operational telemetry. They do not place trades, authorize entries, or bypass Sentinel Alpha's independent-confirmation and human-approval rules.
