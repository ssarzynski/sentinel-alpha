# Sentinel Alpha Module Reconciliation Matrix

This inventory governs selective migration from `feat/milestone-7-portfolio-intelligence` into the `main`-based consolidation baseline. Classification is architectural, not merely filename-based.

## Classification

- **RETAIN** — current `main` responsibility remains authoritative.
- **PORT** — feature-branch capability has no equivalent authoritative implementation and should be migrated deliberately.
- **RECONCILE** — both branches implement related responsibilities; establish one contract before moving code.
- **REVIEW** — inspect existing implementation/tests before deciding whether any port is needed.
- **RETIRE** — do not carry forward after replacement is proven.

| Capability | Main implementation | Feature implementation | Decision | Dependency / note |
| --- | --- | --- | --- | --- |
| Authentication | `sentinel_alpha/auth.py`, `auth_service.py` | `backend/app/auth.py` | RETAIN main; RETIRE feature auth | Security baseline; all browser/API integration must adapt to hardened auth |
| Browser sessions / CSRF | `browser_auth.py` | bearer-token Studio client | RETAIN main | Must precede Studio integration |
| MFA / admin security | `mfa.py`, `admin_accounts.py`, `admin_api.py` | none equivalent | RETAIN main | Non-regression security tests required |
| API surface | `sentinel_alpha/api.py` | `backend/app/api.py` | RECONCILE | Preserve main auth contract; port endpoints individually |
| Persistence / models | main package models/storage | SQLAlchemy `backend/app/models.py` + Alembic 0001-0011 | RECONCILE FIRST | Highest-risk contract boundary; no service ports until canonical persistence is chosen |
| SEC Form 4 | parsers/ingestion on main | EDGAR discovery/XML/orchestrator/worker/services | RECONCILE | Keep provenance, idempotency, observability and tests |
| SEC 8-K | `eightk_parser.py`, `eightk_facts.py` | no equivalent mature path | RETAIN main | Later connect to canonical evidence contract |
| Evidence | `evidence_store.py`, `evidence_roles.py` | `services/evidence.py`, SEC/insider evidence | RECONCILE | One evidence identity/provenance schema required |
| Rule/decision engine | `decision_engine.py` and existing rules | scoring/rules, rule audit, signal evaluation/quality gate | RECONCILE | Preserve hard confirmation/human-control rules |
| Signal intelligence | existing market/signal slices | `signal_intelligence.py`, `signal_priority.py` | PORT AFTER evidence/rules | Attention score cannot override confirmation gate |
| Predictions/outcomes | main calibration/journal facilities | predictions, outcomes, accuracy services/tables | RECONCILE | Point-in-time and anti-look-ahead constraints mandatory |
| Research journal | `journal.py` | `research_journal.py` + DB table | RECONCILE | One immutable/versioned research record contract |
| Macro ingestion | `fred_ingestion.py`, `macro_provenance.py` | not yet mature | RETAIN/REVIEW main | Validate point-in-time/vintage handling before extension |
| Macro regime | `macro_regime.py` | planned only | RETAIN/REVIEW main | Do not rebuild until evaluated |
| Crypto | `btc_slice.py`, `messari_ingestion.py` | core assets in Studio only | RETAIN/REVIEW main | Adapt to canonical market warehouse later |
| Market history | provider/main market ingestion | `market_data.py`, `market_prices.py`, `market_warehouse.py` | RECONCILE | Canonical observation identity and provenance first |
| Market feature engine | limited/related main analytics | `services/market_features.py` | PORT AFTER warehouse | Must consume point-in-time bounded history only |
| Portfolio analytics | limited/no equivalent mature path | portfolio, risk, policy, decisions, provenance | PORT | Depends on canonical persistence + market observations |
| Studio frontend | main dashboard/browser UI | React/Vite Studio | RECONCILE | Feature presentation may be reused; main security/session model stays authoritative |
| Ingestion observability | existing main pipeline facilities | ingestion runs/monitor/scheduler/job lock | RECONCILE | One operational status contract |
| Deployment | main package CI/runtime | Docker Compose/backend/frontend/nginx CI | REVIEW/RECONCILE | Do after runtime architecture is settled |

## Dependency order

```text
Security baseline
    -> canonical persistence/models
        -> canonical evidence/provenance
            -> ingestion contracts
            -> rule/signal contracts
        -> canonical market observations
            -> portfolio intelligence
            -> market feature engine
            -> historical research
        -> prediction/outcome/journal contracts
            -> calibration/backtesting
    -> API contract
        -> Studio UI
    -> deployment/operations
```

## Immediate integration gate

No feature-branch production service should be ported yet. The next slice is **canonical persistence and evidence contracts** because nearly every feature-branch capability depends on its SQLAlchemy/Alembic model graph, while `main` evolved a different storage architecture.

Before selecting a persistence implementation we must compare:

1. transaction semantics and concurrency,
2. migration/versioning support,
3. evidence identity/idempotency,
4. auditability and immutable history,
5. security-account/session storage requirements,
6. point-in-time market-data requirements,
7. operational backup/recovery implications,
8. compatibility with existing tests and deployment.

## Retirement rule

A duplicate implementation is not deleted merely because another implementation is preferred. Retirement occurs only after its required behavior is represented in the canonical implementation and covered by passing regression tests.
