"""Persistent normalized evidence storage for cross-cycle correlation."""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .evidence_roles import ClassifiedEvidence, EvidenceRole, classify_uninterpreted
from .provenance import NormalizedRecord, SourceIdentity, normalize_record


class EvidenceStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS normalized_evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    independent_group TEXT,
                    observed_at TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    reference TEXT,
                    quality TEXT NOT NULL,
                    evidence_role TEXT NOT NULL DEFAULT 'context',
                    role_rationale TEXT NOT NULL DEFAULT 'legacy/unclassified persisted evidence',
                    UNIQUE(asset, metric, source_id, observed_at, reference)
                )"""
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(normalized_evidence)")}
            if "evidence_role" not in columns:
                connection.execute(
                    "ALTER TABLE normalized_evidence ADD COLUMN evidence_role TEXT NOT NULL DEFAULT 'context'"
                )
            if "role_rationale" not in columns:
                connection.execute(
                    "ALTER TABLE normalized_evidence ADD COLUMN role_rationale TEXT NOT NULL "
                    "DEFAULT 'legacy/unclassified persisted evidence'"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_asset_time ON normalized_evidence(asset, observed_at)"
            )

    def append(self, record: NormalizedRecord) -> bool:
        return self.append_classified(classify_uninterpreted(record))

    def append_classified(self, item: ClassifiedEvidence) -> bool:
        record = item.record
        observed_at = record.observation.observed_at
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        with sqlite3.connect(self.database) as connection:
            cursor = connection.execute(
                """INSERT OR IGNORE INTO normalized_evidence
                (asset, metric, value_json, source_id, provider, channel, independent_group,
                 observed_at, statement, reference, quality, evidence_role, role_rationale)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.observation.asset.strip().upper(),
                    record.observation.metric,
                    json.dumps(record.observation.value, sort_keys=True, separators=(",", ":")),
                    record.source.source_id,
                    record.source.provider,
                    record.source.channel,
                    record.source.independent_group,
                    observed_at.astimezone(timezone.utc).isoformat(),
                    record.evidence.statement,
                    record.evidence.reference,
                    record.observation.quality,
                    item.role.value,
                    item.rationale,
                ),
            )
            return cursor.rowcount == 1

    def recent_classified(self, asset: str, *, since: datetime) -> list[ClassifiedEvidence]:
        normalized_asset = asset.strip().upper()
        if not normalized_asset:
            raise ValueError("asset is required")
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        with sqlite3.connect(self.database) as connection:
            rows = connection.execute(
                """SELECT metric, value_json, source_id, provider, channel, independent_group,
                          observed_at, statement, reference, quality, evidence_role, role_rationale
                   FROM normalized_evidence
                   WHERE asset = ? AND observed_at >= ?
                   ORDER BY observed_at ASC, id ASC""",
                (normalized_asset, since.astimezone(timezone.utc).isoformat()),
            ).fetchall()
        items: list[ClassifiedEvidence] = []
        for row in rows:
            metric, value_json, source_id, provider, channel, group, observed_at, statement, reference, quality, role, rationale = row
            record = normalize_record(
                asset=normalized_asset,
                metric=metric,
                value=json.loads(value_json),
                source=SourceIdentity(source_id, provider, channel, group),
                observed_at=datetime.fromisoformat(observed_at),
                statement=statement,
                reference=reference,
                quality=quality,
            )
            try:
                evidence_role = EvidenceRole(role)
            except ValueError:
                evidence_role = EvidenceRole.CONTEXT
                rationale = f"unknown persisted role {role!r}; failed closed to context"
            items.append(ClassifiedEvidence(record, evidence_role, rationale))
        return items

    def recent(self, asset: str, *, since: datetime) -> list[NormalizedRecord]:
        return [item.record for item in self.recent_classified(asset, since=since)]

    def window_classified(
        self, asset: str, *, now: datetime | None = None, hours: int = 24
    ) -> list[ClassifiedEvidence]:
        if hours < 1:
            raise ValueError("hours must be positive")
        now = now or datetime.now(timezone.utc)
        return self.recent_classified(asset, since=now - timedelta(hours=hours))

    def window(self, asset: str, *, now: datetime | None = None, hours: int = 24) -> list[NormalizedRecord]:
        return [item.record for item in self.window_classified(asset, now=now, hours=hours)]
