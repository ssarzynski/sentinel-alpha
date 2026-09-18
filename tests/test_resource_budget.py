import pytest

from sentinel_alpha.resource_budget import DEFAULT_RESOURCE_BUDGET, ResourceBudget, validate_budget


def test_default_budget_is_lean_and_valid():
    validate_budget(DEFAULT_RESOURCE_BUDGET)
    assert DEFAULT_RESOURCE_BUDGET.max_research_sql_statements == 5
    assert DEFAULT_RESOURCE_BUDGET.max_research_examples == 5_000
    assert DEFAULT_RESOURCE_BUDGET.max_backfill_batch == 500
    assert DEFAULT_RESOURCE_BUDGET.max_provider_calls_per_run == 25
    assert DEFAULT_RESOURCE_BUDGET.persist_derived_research is False


@pytest.mark.parametrize("budget", [
    ResourceBudget(max_research_sql_statements=0),
    ResourceBudget(max_research_examples=50_001),
    ResourceBudget(max_backfill_batch=5_001),
    ResourceBudget(max_provider_calls_per_run=1_001),
])
def test_invalid_or_runaway_budgets_are_rejected(budget):
    with pytest.raises(ValueError):
        validate_budget(budget)
