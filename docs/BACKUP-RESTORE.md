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
6. Record the drill date and result in operational records.

## Production cutover

A production restore requires explicit operator approval. Stop application writers, preserve the failed database for investigation, restore to a new path, verify it, then deliberately update the deployment database path. Do not automate destructive replacement.

## Security

Backups contain authentication hashes, encrypted MFA material, audit history, and market research data. Treat them as sensitive. Restrict filesystem permissions, encrypt backup storage at the infrastructure layer, and never place backups or encryption keys in source control.
