# Sentinel Alpha Architecture Consolidation

## Purpose

This branch is the controlled integration baseline for reconciling `main` with `feat/milestone-7-portfolio-intelligence` without blindly merging two independently evolved architectures.

## Non-negotiable controls

- No automatic trading or order execution.
- Human approval remains required for financial actions.
- Strong alerts require at least two independent confirmations.
- Insider selling remains a warning, not positive confirmation.
- No leverage or options automation.
- Research code may propose changes but may not silently modify production rules.
- Point-in-time research must prevent look-ahead leakage.
- Existing hardened authentication/security controls on `main` must not be weakened during integration.

## Authoritative direction by domain

| Domain | Direction |
| --- | --- |
| Authentication, sessions, MFA, CSRF, RBAC, admin controls | Preserve `main` hardened architecture |
| Security audit trail | Preserve and extend `main` |
| SEC / Form 4 / 8-K ingestion | Reconcile both implementations; retain provenance and tests |
| Evidence / provenance | Reconcile into one canonical evidence contract |
| Signal intelligence | Port feature-branch intelligence only behind existing production controls |
| Portfolio intelligence | Port feature-branch implementation after data contracts are reconciled |
| Historical market warehouse | Port feature-branch point-in-time warehouse |
| Market feature engine | Port feature-branch implementation after warehouse |
| Predictions / outcomes / calibration | Reconcile; preserve anti-look-ahead behavior |
| Macro intelligence | Reuse and validate `main` FRED/provenance/regime work before adding code |
| Crypto | Reuse `main` BTC/Messari work and reconcile feature-branch interfaces |
| Studio UI | Reconcile presentation without replacing hardened browser authentication |
| Research/adaptive learning | Isolate from production; promotion requires validation and human approval |

## Integration order

1. Inventory and dependency map.
2. Security/authentication baseline tests.
3. Canonical data/evidence contracts.
4. Historical market warehouse.
5. Portfolio intelligence.
6. Signal/prediction/outcome intelligence.
7. Studio presentation.
8. Macro/crypto/historical intelligence reconciliation.
9. Documentation and operational hardening.
10. Full CI, security, migration and container verification.

## Definition of Done for every consolidation slice

A slice is not complete until:

1. Its authoritative implementation is identified.
2. Duplicate responsibilities are documented or removed deliberately.
3. Unit/integration tests pass.
4. Database migration compatibility is verified when applicable.
5. Security controls are not weakened.
6. API/data contracts are documented.
7. Architecture documentation is updated.
8. CI passes before the next slice begins.

## Current rule

Do not merge or rebase the old feature branch wholesale. Port reviewed components into this branch in dependency order. Every port must be small enough to test and revert independently.
