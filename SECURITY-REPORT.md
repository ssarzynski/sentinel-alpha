# Sentinel Alpha Security Launch Report

Assessment date: 2026-09-18  
Scope: repository and CI-verifiable launch controls. Deployment-specific claims remain NOT VERIFIED until exercised in staging/production.

## Executive status

**REVIEW — application security controls are substantially implemented and CI-tested, but production launch is not yet approved.** No finding in this report authorizes live trading; Sentinel Alpha remains decision support with automatic execution disabled and human approval required.

| Control area | Status | Evidence / remaining gate |
|---|---|---|
| Password storage | PASS | Argon2id authentication; bootstrap credential is environment-only and forced to change. |
| Password lifecycle | PASS | Expiration policy, history, forced change, session revocation, and compromised-password screening are covered by automated tests. |
| Administrator authorization | PASS | Deny-by-default protected admin routes, account-state enforcement, last-active-admin protection. |
| MFA | PASS | Administrator TOTP, encrypted secrets, recovery codes, session MFA gate, and recovery throttling are implemented and tested. |
| Browser sessions | PASS | Server-side sessions, hashed tokens, idle/absolute expiry, rotation/revocation, Secure/HttpOnly/SameSite cookie controls. |
| CSRF / trusted origin | PASS | State-changing browser/admin flows use session-bound CSRF and trusted-origin validation. |
| Login abuse resistance | PASS | Generic failures, dummy Argon2 timing path, account/IP throttling, trusted-proxy-aware client IP handling. |
| Input/request hardening | PASS | Bounded auth inputs and validated request IDs with mutation traceability. |
| Security headers | PASS | Application middleware covers browser security headers; deployment TLS behavior remains separate. |
| Audit integrity | PASS | Tamper-evident security/evaluation chains and rollback regression tests. |
| Paper ledger integrity | PASS | Paper-only lifecycle is linked to evaluations, validates price/quantity/position state, and detects tampering. |
| Financial execution isolation | PASS | Repository architecture retains no automatic trade execution path; rules prohibit leverage/options and require human approval. |
| Evidence independence | PASS | Confirmation provenance fails closed on ambiguous mixed lineage; strong alerts require independent confirmations. |
| SQLite backup tooling | PASS | Verified online backup and restore helpers perform SQLite integrity checks and refuse unsafe overwrite. |
| Backup recovery drill | NOT VERIFIED | Must restore a real staging backup, start the app against it, and verify auth/audit/journal/paper reads. |
| TLS / HTTPS termination | NOT VERIFIED | Requires selected production host/reverse proxy and external verification. |
| Production secret injection | NOT VERIFIED | MFA encryption key, bootstrap provisioning, provider keys, filesystem permissions, and secret rotation require deployment verification. |
| Production trusted origins/proxies | NOT VERIFIED | Exact origin and proxy allowlists depend on deployment topology. |
| Production database permissions/encryption | NOT VERIFIED | Host filesystem permissions and backup-at-rest encryption require infrastructure verification. |
| Provider automation rights | REVIEW | SEC/FRED/Treasury have documented controls; Messari remains conditional; Alpha Vantage, Finviz, and Invo remain blocked pending permission/identity verification. |
| Staging acceptance | NOT VERIFIED | Full deployment acceptance has not yet been run against a production-like environment. |
| External/non-destructive penetration test | NOT VERIFIED | Repository attack/regression tests exist, but an externally reachable staging target does not yet exist. |

## CI evidence

The repository CI runs on Python 3.11 and 3.12 and executes the complete pytest suite on pull requests and main. Launch-critical macro ingestion modules also receive Ruff checks. PRs are merged only after successful CI and review-thread inspection in the current engineering workflow.

Automated coverage includes authentication state transitions, password changes and history, compromised-password behavior, MFA and recovery, session lifecycle, CSRF/origin handling, request traceability, administrator mutations, audit rollback behavior, evidence/risk rules, frontend/API contracts, backup integrity, and paper-ledger integrity.

## Launch blockers

Production deployment must remain gated until all of the following are completed:

1. Select and approve the deployment host/topology, including any recurring cost.
2. Configure HTTPS/TLS and verify redirect, HSTS, cookie, and origin behavior from outside the host.
3. Inject production secrets without committing them; verify key ownership, filesystem permissions, and rotation/recovery procedure.
4. Configure exact trusted origins and, only if needed, explicit trusted proxy addresses.
5. Perform a staging restore drill from a verified backup and record the result.
6. Run the full staging acceptance suite plus a non-destructive authenticated/unauthenticated security assessment against the deployed target.
7. Re-check provider terms immediately before enabling each provider. Providers marked blocked remain disabled.
8. Record PASS/FAIL results and resolve every FAIL before production approval.

## Explicit non-goals

This report does not approve brokerage connectivity, automatic execution, leverage, options, or unattended financial action. No security role—including administrator—may bypass Sentinel Alpha's human financial-approval boundary.

## Deployment acceptance record

Populate after a production-like staging environment exists:

- Host/topology:
- Build/commit:
- Test date:
- Tester:
- HTTPS/TLS:
- Security headers:
- Trusted origins:
- Trusted proxies:
- Secret injection:
- Database permissions:
- Backup restore drill:
- Authentication/MFA:
- Session/CSRF:
- Admin authorization:
- Audit-chain verification:
- Paper-ledger verification:
- Provider gates:
- External security test:
- Final result: NOT VERIFIED
