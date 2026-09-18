"""Central resource budgets for cost-conscious Sentinel operation.

Budgets constrain avoidable work and duplication. They must never be used to
weaken validation, provenance, auditability, security, or canonical data.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceBudget:
    max_research_sql_statements: int = 5
    max_research_examples: int = 5_000
    max_backfill_batch: int = 500
    max_provider_calls_per_run: int = 25
    persist_derived_research: bool = False


DEFAULT_RESOURCE_BUDGET = ResourceBudget()


def validate_budget(budget: ResourceBudget) -> None:
    """Reject budgets that are invalid or likely to create runaway work."""
    if not 1 <= budget.max_research_sql_statements <= 20:
        raise ValueError("max_research_sql_statements must be between 1 and 20")
    if not 1 <= budget.max_research_examples <= 50_000:
        raise ValueError("max_research_examples must be between 1 and 50000")
    if not 1 <= budget.max_backfill_batch <= 5_000:
        raise ValueError("max_backfill_batch must be between 1 and 5000")
    if not 1 <= budget.max_provider_calls_per_run <= 1_000:
        raise ValueError("max_provider_calls_per_run must be between 1 and 1000")
