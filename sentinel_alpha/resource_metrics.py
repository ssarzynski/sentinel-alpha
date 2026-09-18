"""Lightweight in-memory resource accounting.

Metrics are deliberately ephemeral by default: they help control operating cost
without creating another persistent telemetry dataset or storing market payloads,
credentials, request bodies, or other sensitive content.
"""
from __future__ import annotations

from dataclasses import dataclass

from sentinel_alpha.resource_budget import ResourceBudget, validate_budget


@dataclass
class ResourceMetrics:
    sql_statements: int = 0
    provider_calls: int = 0
    records_processed: int = 0
    canonical_bytes_added: int = 0

    def record_sql(self, count: int = 1) -> None:
        self.sql_statements += _nonnegative(count)

    def record_provider_call(self, count: int = 1) -> None:
        self.provider_calls += _nonnegative(count)

    def record_records(self, count: int) -> None:
        self.records_processed += _nonnegative(count)

    def record_canonical_bytes(self, count: int) -> None:
        self.canonical_bytes_added += _nonnegative(count)

    def budget_violations(self, budget: ResourceBudget) -> tuple[str, ...]:
        validate_budget(budget)
        violations: list[str] = []
        if self.sql_statements > budget.max_research_sql_statements:
            violations.append("research_sql_statements")
        if self.provider_calls > budget.max_provider_calls_per_run:
            violations.append("provider_calls")
        return tuple(violations)

    def snapshot(self) -> dict[str, int]:
        """Return counters only; never include payloads, symbols, URLs, or secrets."""
        return {
            "sql_statements": self.sql_statements,
            "provider_calls": self.provider_calls,
            "records_processed": self.records_processed,
            "canonical_bytes_added": self.canonical_bytes_added,
        }


def _nonnegative(value: int) -> int:
    if value < 0:
        raise ValueError("resource metric increments cannot be negative")
    return value
