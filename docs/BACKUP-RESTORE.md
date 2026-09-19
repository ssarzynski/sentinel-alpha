# SQLite Backup and Restore Runbook

Sentinel Alpha uses SQLite for the launch architecture. Backups must be created with SQLite's backup API rather than by copying a live database file.

## Backup

1. Choose a destination outside the active database directory and on storage with appropriate access controls.
2. Call `create_verified_backup(source, destination)`.
3. The helper refuses to overwrite an existing file.
4. The resulting backup is accepted only after `PRAGMA integrity_check` returns `ok`.
5. Retain multiple dated backups according to the deployment's retention policy. Do not commit database backups to Git.

## Restore drill

1. Never restore over the active production database.
2. Call `restore_verified_backup(backup, new_destination)`.
3. The source backup is integrity-checked before restore and the restored database is checked again.
4. Start a disposable/staging Sentinel Alpha instance against the restored database.
5. Verify authentication, security audit integrity, signal/journal reads, and paper-ledger reads before considering the backup recoverable.
6. Run `scripts/backup_restore_drill.py` with distinct source, backup, restored, and private evidence paths to automate the non-destructive SQLite integrity and row-count preservation checks.\n7. Store its JSON evidence outside the repository with restricted access. A failed drill remains evidence and must not be rewritten as PASS.\n8. The script verifies database integrity and table row-count preservation only. Authentication, audit-chain, journal, dashboard, and paper-history behavior must still be exercised against the restored staging instance before the recovery launch blocker can be marked PASS. After starting the disposable restored instance, run `scripts/verify_restored_instance.py --base-url <private-url> --commit <approved-sha> --evidence-file <private-path>/restored-instance.json`. The verifier performs GET-only application checks and requires valid audit and paper-ledger integrity plus disabled automatic trading and required human approval. Store its evidence outside the repository.

## Production cutover

A production restore requires explicit operator approval. Stop application writers, preserve the failed database for investigation, restore to a new path, verify it, then deliberately update the deployment database path. Do not automate destructive replacement.

## Security

Backups contain authentication hashes, encrypted MFA material, audit history, and market research data. Treat them as sensitive. Restrict filesystem permissions, encrypt backup storage at the infrastructure layer, and never place backups or encryption keys in source control.
