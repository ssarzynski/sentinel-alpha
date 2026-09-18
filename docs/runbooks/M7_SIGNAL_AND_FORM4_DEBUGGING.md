# M7 Signal + Form 4 Debugging Runbook

## Purpose
This runbook documents the Milestone 7 market-provenance, signal-gating, and SEC Form 4 pipeline so a future maintainer can diagnose failures without reverse-engineering the implementation.

## Canonical production flow
`scheduler -> IngestionRun -> sec_watchlist_worker -> SEC discovery -> sec_form4_orchestrator -> form4_xml parser -> form4 classifier -> insider evidence -> signal system`

`ingestion/form4_xml.py` is the canonical ownership-XML parser; do not create a second parser. `ingestion/form4.py` owns economic classification. `services/insider_evidence.py` owns normalized transaction evidence. Multiple SEC rows remain one SEC source family for confirmation purposes.

## Invariants
- No automatic trading or order creation.
- Human approval is required for actionable WATCH/STRONG outputs.
- STRONG requires at least two independent evidence source families.
- Duplicate observations from one source family do not increase confirmation count.
- Missing/stale/unconfirmed market data withholds risk-dependent output.
- Generic Form 4 metadata is not proof of insider selling.
- Only explicitly classified, non-derivative open-market `S` transactions trigger the insider-selling warning.
- Tax withholding, gifts, grants, exercises and derivatives must not masquerade as discretionary open-market sales.
- Failed SEC document retrieval/parsing must never fabricate transaction evidence.
- Evidence is append-only/idempotent through deterministic evidence keys.
- One company failure must not suppress processing of the remaining watchlist.

## Scheduled worker: durable audit + live diagnostics
Every scheduled execution creates an `IngestionRun` before external SEC work begins. Terminal states are `completed`, `completed_with_errors`, or `failed`. Durable counts include checked companies, discovered filings, new filings, skipped existing filings and evidence rows. Company-level failures are stored in `failures_json`; fatal worker exceptions mark the run failed and are re-raised.

Search worker logs for `sec_ingestion`. Stable scheduled events are:
- `event=watchlist_started`: number of configured watchlist items.
- `event=company_discovered`: ticker, CIK and discovered filing count.
- `event=filing_created`: ticker, accession and form for a newly persisted filing.
- `event=filing_existing`: ticker, accession and form for the idempotent duplicate path.
- `event=form4_parsed`: ticker, accession and normalized transaction count.
- `event=company_failed`: ticker, CIK, `stage=watchlist_company`, exception type and bounded error message.
- `event=watchlist_completed`: checked/discovered/new/skipped/evidence/failure totals.

For a scheduled incident, start with the latest `IngestionRun`. If status is `completed_with_errors`, inspect `failures_json`, then search logs by ticker/CIK. If an accession exists, trace `filing_created|filing_existing -> form4_parsed`. A `company_failed` event is isolated: verify later watchlist tickers still emit `company_discovered` and that the completed run's `checked` count covers the full configured watchlist.

## Direct company-sync diagnostics
The direct `sync_company_filings()` path emits `sync_started`, `filing_created`, `filing_existing`, `form4_parsed`, `form4_failed`, and `sync_completed`. `form4_failed` uses `stage=form4_document`. This path is useful for targeted/manual synchronization; scheduled production execution should be debugged through `IngestionRun` plus the scheduled events above.

## Failure tracing
### SEC metadata exists but no transaction evidence
Match the accession in evidence/filing metadata and logs. On direct sync inspect `form4_failures`/`event=form4_failed`. On scheduled execution inspect the `IngestionRun` and worker events. Common causes include HTTP failure, invalid/empty document, malformed ownership XML, parser rejection, or upstream SEC response problems.

### Insider sale expected but warning absent
Inspect normalized evidence fields: transaction code/direction, economic type, `signal_eligible`, derivative status and classification reasons. A valid warning requires a signal-eligible non-derivative open-market sale; dispositions for tax withholding, gifts, grants or exercises are not equivalent.

### STRONG signal becomes WITHHELD
Inspect `gate_reasons`. `fewer_than_two_independent_evidence_confirmations` means evidence-family diversity failed. `market_data_withhold` means the provenance/freshness gate failed. Then inspect per-asset provenance.

### Portfolio risk missing
Inspect Decision Ledger `risk_data_status`. `withheld:data_quality:withhold` means risk was intentionally not calculated because provenance failed; this is not a numerical risk-engine failure.

## Debugging data to preserve
When adding ingestion/signal components, preserve stable IDs, source family, source URL, source record/accession ID, observed timestamp, normalized classification, gate status/reasons, human-review state and durable run status. Errors should include a machine-readable stage/code plus bounded message; never store secrets or full uncontrolled remote responses.

## Testing expectations
Every change to this path should test success, idempotency, malformed input, upstream failure, classification edge cases, source-family deduplication, stale/unconfirmed market data, fail-closed behavior, durable `IngestionRun` state, observable lifecycle/failure events, and per-company failure isolation. CI must pass backend tests, frontend build, migrations, Docker/Compose startup/health, worker checks and teardown before advancing.

## Maintenance rule
Update this runbook and nearby docstrings whenever an invariant, stage name, event name, payload field, durable audit field or failure behavior changes. Prefer explicit reason/event codes over prose-only failures so future logs and dashboards remain searchable.
