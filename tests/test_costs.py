import pytest

from swarm.costs import BudgetExceeded, CostTracker, cost_usd


def test_pricing_for_known_models():
    assert cost_usd("claude-opus-4-5", 1_000_000, 1_000_000) == 90.0
    assert cost_usd("claude-sonnet-4-5", 1_000_000, 1_000_000) == 18.0


def test_unknown_model_costs_zero():
    assert cost_usd("not-a-model", 1000, 1000) == 0.0


def test_tracker_lines_have_total():
    c = CostTracker()
    c.add("claude-opus-4-5", 1000, 500)
    c.add("claude-sonnet-4-5", 2000, 1000)
    lines = c.lines()
    assert any("opus" in line for line in lines)
    assert any("sonnet" in line for line in lines)
    assert any(line.startswith("total:") for line in lines)


def test_budget_cap_raises_when_exceeded():
    c = CostTracker(max_usd=0.05)
    with pytest.raises(BudgetExceeded) as ei:
        c.add("claude-opus-4-5", 10_000, 10_000)
    assert ei.value.cap == 0.05
    assert ei.value.spent > 0.05


def test_budget_cap_allows_when_under():
    c = CostTracker(max_usd=10.0)
    c.add("claude-sonnet-4-5", 1000, 1000)
    assert c.total_usd() < 10.0


def test_no_cap_is_unlimited():
    c = CostTracker()
    c.add("claude-opus-4-5", 1_000_000, 1_000_000)
    assert c.total_usd() == 90.0
