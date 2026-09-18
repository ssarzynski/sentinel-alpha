# Persistence Architecture Decision

Status: **Accepted for consolidation**

## Decision

Sentinel Alpha will converge on **one SQLAlchemy-managed relational persistence layer with Alembic migrations for application/research data**, while preserving the behavior and security guarantees of the hardened `main` authentication/session/audit implementation during migration.

This is not approval to replace security code wholesale. Security storage is migrated only after equivalent regression coverage proves that Argon2id password handling, account states, password-expiration policy, admin approval, MFA, server-side session revocation, CSRF controls, brute-force blocking, and tamper-evident audit behavior remain intact.

## Why

`main` currently uses direct SQLite stores that create and evolve tables inside service constructors. This has produced strong focused behavior, especially in security and evidence, but schema ownership is distributed across modules. The feature branch introduced a centralized SQLAlchemy model graph and ordered Alembic migrations supporting evidence, rule evaluations, predictions, outcomes, research journal, ingestion runs, portfolios, market observations and policy decisions.

For the intended long-lived historical/research platform, centralized migrations and explicit relational models provide the stronger foundation for:

- reproducible schema upgrades and rollback planning,
- PostgreSQL-compatible production deployment,
- transaction boundaries spanning related records,
- backup/recovery documentation,
- historical warehouse growth,
- point-in-time research queries,
- test database creation and migration verification,
- eliminating hidden runtime DDL spread across services.

## What is retained from `main`

The following are behavioral requirements, not disposable implementation details:

1. Argon2id password hashing and comparable work for unknown-user authentication.
2. Deny-by-default roles/account states.
3. Pending approval, disabled, locked and rejected account states.
4. Password expiration policy and mandatory password changes.
5. Server-side session creation/revocation.
6. CSRF protections for browser mutation paths.
7. MFA and recovery-code behavior.
8. Brute-force throttling/blocking and generic login failures.
9. Security audit events and tamper-evidence guarantees.
10. Evidence classification, independent source grouping and fail-closed unknown evidence roles.

## Canonical schema principles

### Identity

Application identity will use stable integer primary keys plus externally meaningful unique keys where needed. Authentication identity must not be reduced to the feature branch's simple `email/password_hash/is_active` user model.

### Evidence

The canonical evidence record must combine the strongest properties of both branches:

- stable unique evidence key,
- normalized asset and metric/category,
- structured value/payload,
- provider/source/channel identity,
- independent source family/group,
- provider source-record identity,
- observation timestamp,
- ingestion timestamp,
- reference/source URL,
- quality status,
- evidence role and rationale,
- idempotent uniqueness.

Unknown persisted roles must fail closed to context/non-confirming behavior.

### Market observations

Historical market observations retain asset, timestamp, price/value, currency, provider/source family, provider record identity, quality status, metadata and ingestion timestamp. Research queries must support an explicit point-in-time cutoff so future observations cannot enter historical feature computation.

### Research records

Predictions, outcomes, rule evaluations and research journal versions are append-oriented historical records. Research-journal versions are not overwritten. Production-rule authorization remains explicit and defaults false.

### Transactions

Multi-record ingestion/evaluation operations should commit atomically where partial state would make a later decision misleading. Network acquisition remains outside long database transactions.

## Migration strategy

1. **Do not import the feature branch's `User` model.** Design canonical security tables from `main` behavior first.
2. Port SQLAlchemy/Alembic infrastructure into the consolidation branch without changing runtime behavior.
3. Define canonical models for security, evidence and audit data.
4. Add migration tests against a fresh database and an upgrade fixture representing existing `main` SQLite tables.
5. Adapt one store at a time behind its existing public interface; keep existing security tests unchanged where possible.
6. Migrate evidence storage next and prove idempotency/source-independence behavior.
7. Only then port market warehouse, portfolio, prediction/outcome and research models.
8. Remove constructor-time schema mutation only after its replacement migration has passed upgrade tests.

## Rejected alternatives

### Keep distributed raw SQLite stores permanently

Rejected as the final architecture. It is simple locally but makes schema evolution, cross-domain transactions, production database portability and historical warehouse management increasingly difficult.

### Replace `main` with the feature branch database wholesale

Rejected. The feature branch's security model is materially weaker and does not represent the hardened account/session/MFA/admin behavior already present on `main`.

### Maintain two permanent databases/ORM systems

Rejected. It would preserve the exact duplication this consolidation is intended to eliminate and complicate atomicity, backup/recovery and debugging.

## Integration gate

No portfolio, signal-priority, historical-learning or Studio port proceeds until the SQLAlchemy/Alembic foundation is introduced on the consolidation branch and the existing hardened security test suite remains green.
