import pytest

from sentinel_alpha.resource_budget import DEFAULT_RESOURCE_BUDGET
from sentinel_alpha.resource_metrics import ResourceMetrics


def test_metrics_track_counts_without_payload_storage():
    metrics = ResourceMetrics()
    metrics.record_sql(2)
    metrics.record_provider_call()
    metrics.record_records(500)
    metrics.record_canonical_bytes(4096)
    assert metrics.snapshot() == {
        "sql_statements": 2,
        "provider_calls": 1,
        "records_processed": 500,
        "canonical_bytes_added": 4096,
    }
    assert metrics.budget_violations(DEFAULT_RESOURCE_BUDGET) == ()


def test_budget_violations_are_named_and_compact():
    metrics = ResourceMetrics(sql_statements=6, provider_calls=26)
    assert metrics.budget_violations(DEFAULT_RESOURCE_BUDGET) == (
        "research_sql_statements", "provider_calls"
    )


def test_negative_metric_increments_are_rejected():
    metrics = ResourceMetrics()
    with pytest.raises(ValueError):
        metrics.record_records(-1)
