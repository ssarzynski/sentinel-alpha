from datetime import datetime, timedelta, timezone

from sentinel_alpha.evidence_roles import ClassifiedEvidence, EvidenceRole
from sentinel_alpha.evidence_store import EvidenceStore
from sentinel_alpha.provenance import SourceIdentity, normalize_record


def make_record(asset, provider, source_id, observed_at, reference):
    return normalize_record(
        asset=asset,
        metric="signal",
        value={"direction": "up"},
        source=SourceIdentity(source_id, provider, "market"),
        observed_at=observed_at,
        statement=f"{provider} evidence",
        reference=reference,
        quality="high",
    )


def test_evidence_persists_across_store_restarts(tmp_path):
    database = tmp_path / "sentinel.db"
    now = datetime(2026, 9, 17, 18, tzinfo=timezone.utc)
    first = EvidenceStore(database)
    assert first.append(make_record("BTC", "SEC", "sec-filings", now, "sec:1")) is True

    restarted = EvidenceStore(database)
    records = restarted.window("btc", now=now + timedelta(hours=1), hours=24)
    assert len(records) == 1
    assert records[0].observation.asset == "BTC"
    assert records[0].source.provider == "SEC"


def test_classified_role_persists_across_store_restarts(tmp_path):
    database = tmp_path / "sentinel.db"
    now = datetime(2026, 9, 17, 18, tzinfo=timezone.utc)
    record = make_record("BTC", "Messari", "messari-market", now, "messari:1")
    first = EvidenceStore(database)
    assert first.append_classified(
        ClassifiedEvidence(record, EvidenceRole.SUPPORT, "explicit directional market rule")
    ) is True

    restarted = EvidenceStore(database)
    items = restarted.window_classified("BTC", now=now + timedelta(hours=1), hours=24)
    assert len(items) == 1
    assert items[0].role is EvidenceRole.SUPPORT
    assert items[0].rationale == "explicit directional market rule"
    assert items[0].record.source.provider == "Messari"


def test_unclassified_append_persists_as_context(tmp_path):
    database = tmp_path / "sentinel.db"
    now = datetime(2026, 9, 17, 18, tzinfo=timezone.utc)
    store = EvidenceStore(database)
    store.append(make_record("NVDA", "SEC", "sec-filings", now, "sec:1"))
    item = store.window_classified("NVDA", now=now, hours=1)[0]
    assert item.role is EvidenceRole.CONTEXT


def test_window_combines_independent_sources_from_different_cycles(tmp_path):
    database = tmp_path / "sentinel.db"
    now = datetime(2026, 9, 17, 18, tzinfo=timezone.utc)
    store = EvidenceStore(database)
    store.append(make_record("BTC", "SEC", "sec-filings", now - timedelta(hours=3), "sec:1"))
    store.append(make_record("BTC", "Messari", "messari-market", now - timedelta(hours=1), "messari:1"))

    records = store.window("BTC", now=now, hours=6)
    assert [record.source.provider for record in records] == ["SEC", "Messari"]
    assert {record.source.independence_key for record in records} == {"sec", "messari"}


def test_duplicate_evidence_is_idempotent(tmp_path):
    database = tmp_path / "sentinel.db"
    now = datetime(2026, 9, 17, 18, tzinfo=timezone.utc)
    store = EvidenceStore(database)
    record = make_record("ETH", "Messari", "messari-market", now, "messari:eth:1")
    assert store.append(record) is True
    assert store.append(record) is False
    assert len(store.window("ETH", now=now, hours=1)) == 1


def test_window_excludes_stale_evidence(tmp_path):
    database = tmp_path / "sentinel.db"
    now = datetime(2026, 9, 17, 18, tzinfo=timezone.utc)
    store = EvidenceStore(database)
    store.append(make_record("BTC", "SEC", "sec-filings", now - timedelta(hours=25), "sec:old"))
    store.append(make_record("BTC", "Messari", "messari-market", now - timedelta(hours=2), "messari:new"))
    records = store.window("BTC", now=now, hours=24)
    assert len(records) == 1
    assert records[0].source.provider == "Messari"
