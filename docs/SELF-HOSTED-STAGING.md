# Zero-Cost Self-Hosted Staging Runbook

This runbook prepares a production-like Sentinel Alpha staging instance without purchasing hosting. It does **not** authorize public exposure, live trading, brokerage connectivity, leverage, options, or unattended financial actions.

## Safety boundary

- Use a supported operating system with current security updates for any network-exposed host.
- An unsupported Windows host may be used only for isolated/LAN testing; do not expose it directly to the Internet.
- Keep staging on a private LAN initially.
- Do not commit `.env`, SQLite databases, backups, MFA keys, bootstrap credentials, provider keys, or recovery material.
- Keep `SENTINEL_AUTOMATIC_TRADING=false` and `SENTINEL_HUMAN_APPROVAL_REQUIRED=true`.
- Providers blocked by the provider-readiness report remain disabled.

## Host prerequisites

- Python 3.11 or 3.12.
- Supported, patched operating system.
- A dedicated non-administrator/non-root service account where practical.
- Repository checkout at the exact approved commit.
- Writable private directories for runtime database and backups.
- Host firewall enabled. During private staging, permit only the minimum LAN access required for testing.

Record the OS/version, Python version, commit SHA, hostname, test date, and operator in the staging acceptance record in `SECURITY-REPORT.md`.

## Install

Create an isolated virtual environment and install the project plus test dependencies using the repository's supported Python tooling. Run the complete test suite before starting staging. Do not continue on a failing test.

## Runtime layout

Use directories outside the repository checkout, for example:

- runtime database: `<private-runtime>/sentinel-alpha/staging.db`
- backups: `<private-backup>/sentinel-alpha/`
- secrets/environment: a host-protected environment file or service manager secret store

Restrict these locations to the Sentinel Alpha service account and the administrator responsible for recovery.

## Secrets and environment

Start from `.env.example`, but store the populated copy outside source control.

Generate a new staging MFA encryption key. Never reuse a production key. Configure exact trusted browser origins. Leave trusted proxies empty unless a specific reverse proxy is deployed and its direct address is known.

Do not enable provider credentials merely because a field exists. Follow `docs/PROVIDER-TERMS-READINESS.md`.

## Private startup gate

Before any public exposure:

1. Run the full test suite successfully.
2. Start the application bound only to loopback or a deliberately selected private-LAN interface.
3. Verify `GET /health` returns the Sentinel Alpha healthy response.
4. Verify `GET /v1/rules` reports at minimum:
   - two independent confirmations,
   - maximum two new entries per week,
   - options disabled,
   - leverage disabled,
   - human approval required,
   - automatic trading disabled.
5. Complete administrator login and MFA.
6. Verify browser session expiry/revocation behavior and CSRF-protected mutations.
7. Verify the dashboard loads and both the audit chain and paper ledger report valid.
8. Create only test/paper data. Confirm no brokerage or execution action exists.

A failed item stops promotion.\n\nThe automated acceptance gate requires both `audit_chain_valid=true` and `paper_ledger_valid=true`; either integrity failure stops promotion.\n\nRun `scripts/staging_acceptance.py` with `--commit <approved-sha>` and `--evidence-file <private-path>/acceptance.json` to retain a machine-readable record. Store the evidence outside the repository with restricted access; it may contain host and topology metadata. A failed run is still evidence and should be retained for diagnosis rather than rewritten as PASS.

## Backup/restore drill

Follow `docs/BACKUP-RESTORE.md`.

Create a verified backup from the staging database and restore it to a **new** path. Start a disposable instance against the restored copy. Verify authentication, audit-chain reads, evaluation/journal reads, dashboard reads, and paper-history reads. Record the backup and restore integrity results. Never overwrite the active database as part of the drill.

## Network promotion

Private-LAN success does not authorize Internet exposure.

Before an externally reachable staging endpoint is allowed:

1. Use a supported patched host.
2. Put TLS termination in front of the application.
3. Configure the exact HTTPS origin in `SENTINEL_TRUSTED_ORIGINS`.
4. Configure `SENTINEL_TRUSTED_PROXIES` only for the actual direct proxy, if one exists.
5. Verify HTTP-to-HTTPS behavior, certificate validity, HSTS/security headers, Secure/HttpOnly/SameSite cookies, origin rejection, and forwarded-client-IP behavior externally.
6. Do not expose the SQLite file, backup directory, environment file, source-control metadata, logs containing secrets, or management ports.
7. Run the non-destructive authenticated and unauthenticated staging security assessment.

Public exposure is a separate approval gate.

## Rollback

If staging fails acceptance, stop the staging process, preserve relevant logs without secrets, retain the failed database for investigation, and return to the last approved commit/database. Do not destructively replace a database automatically.

If a secret may have been exposed, treat it as compromised and rotate it before restarting.

## Acceptance result

Update the deployment acceptance record in `SECURITY-REPORT.md` with actual evidence. Leave an item NOT VERIFIED until it has been exercised on the target host. Production remains blocked while any launch blocker is FAIL or NOT VERIFIED.
