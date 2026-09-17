# Milestone 6 — Insider Intelligence

## Status
Engineering-complete candidate pending final CI and PR audit.

## Delivered
- Deterministic SEC Form 4 transaction classification.
- Distinct-insider cluster detection and signal eligibility guardrails.
- SEC submissions discovery and Form 4/4-A XML parsing.
- Normalized immutable Evidence creation with deduplication.
- Hardened SEC HTTP transport and watchlist ingestion worker.
- Persistent ingestion-run lifecycle, metrics and failure records.
- PostgreSQL advisory locking to prevent overlapping scheduled jobs.
- Deployable periodic SEC worker with graceful shutdown and environment configuration.
- Authenticated Sentinel Studio ingestion health/run-history APIs.
- Sentinel Studio operations dashboard.
- Docker Compose runtime integration and CI smoke testing.

## Guardrails
- Derivative transactions do not become insider-buy/sell signals.
- Repeated filings by one insider do not create a multi-insider cluster.
- Insider evidence does not authorize a trade.
- Strong decisions still require independent confirmation and human approval.
- No leverage, options or automatic trading is introduced by this milestone.

## Runtime verification
CI validates backend tests, frontend production build, Compose configuration, application image builds, PostgreSQL/Redis/FastAPI/frontend/Nginx startup, public health routing, Alembic migration state and SEC worker process startup.

## Runtime dependencies discovered by smoke testing
Full-container testing identified two dependencies that unit/build tests did not expose: `email-validator` for Pydantic `EmailStr`, and `python-multipart` for FastAPI OAuth form handling. Both are now explicit production dependencies.

## Follow-on work
Milestone 7 expands from insider intelligence into portfolio intelligence, risk, correlation, allocation and the decision ledger. Broader market/macro/crypto source ingestion remains separate work and must meet the same Evidence and provenance standards.
