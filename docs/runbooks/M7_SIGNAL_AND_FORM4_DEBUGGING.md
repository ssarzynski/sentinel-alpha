# M7 Signal + Form 4 Debugging Runbook

## Purpose
This runbook documents the Milestone 7 market-provenance, signal-gating, and SEC Form 4 pipeline so a future maintainer can diagnose failures without reverse-engineering the implementation.

## Canonical flow
1. `ingestion/sec_edgar.py` retrieves SEC submissions and bounded Form 4 primary documents.
2. `ingestion/form4_xml.py` is the canonical ownership-XML parser. Do not create a second XML parser.
3. `ingestion/form4.py` classifies normalized transactions economically. P/S open-market transactions are distinct from F tax withholding, A grants, G gifts, M/X exercises, and derivatives.
4. `services/evidence.py` persists append-only filing and transaction evidence. Transaction evidence retains accession number, primary document, filing URL and transaction index.
5. `services/sec_signal_evidence.py` adapts eligible evidence into signal confirmations. Multiple SEC rows remain one SEC source family.
6. `data_quality_gate.py` evaluates market provenance/freshness.
7. `signal_quality_gate.py` prevents STRONG alerts without >=2 independent evidence families and acceptable market data.
8. `signal_evaluation.py` is the canonical signal evaluation path. It never executes a trade.
9. Portfolio policy decisions use the same market-quality gate and record withheld risk in the Decision Ledger.

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

## Failure tracing
### SEC metadata exists but no transaction evidence
Inspect `sync_company_filings()` result `form4_failures`. Match `accession_number`, then check stage `form4_document`. Common causes: HTTP error, invalid primary-document name, document > configured size, non-UTF-8 response, non-ownership XML, or parser rejection.

### Insider sale expected but warning absent
Inspect transaction evidence payload: `form`, `transaction_code`, `transaction_direction`, `economic_type`, `signal_eligible`, `is_derivative`, and `classification_reasons`. A valid warning requires Form 4 + signal eligible + `open_market_sale` + `sell`.

### STRONG signal becomes WITHHELD
Inspect `gate_reasons`. `fewer_than_two_independent_evidence_confirmations` means evidence-family diversity failed. `market_data_withhold` means the provenance/freshness gate failed. Then inspect per-asset provenance.

### Portfolio risk missing
Inspect Decision Ledger `risk_data_status`. `withheld:data_quality:withhold` means risk was intentionally not calculated because provenance failed; this is not a numerical risk-engine failure.

## Debugging data to preserve
When adding new ingestion/signal components, preserve stable IDs, source family, source URL, source record/accession ID, observed timestamp, normalized classification, gate status/reasons, and human-review state. Errors should include a machine-readable stage/code plus a bounded message; do not store secrets or full uncontrolled remote responses.

## Testing expectations
Every change to this path should test: success, idempotency/duplicate ingestion, malformed input, upstream HTTP failure, classification edge cases, source-family deduplication, stale/unconfirmed market data, and fail-closed behavior. CI must pass backend tests, frontend build, migrations, Docker/Compose startup/health, worker checks, and teardown before advancing.

## Maintenance rule
Update this runbook and nearby function/module docstrings whenever an invariant, stage name, payload field, or failure behavior changes. Prefer explicit reason codes over prose-only failures so future logs and dashboards remain searchable.
