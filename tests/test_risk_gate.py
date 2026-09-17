from sentinel_alpha.decision_engine import Decision
from sentinel_alpha.risk_gate import TradeProposal, evaluate_risk_gate


def confirmed_decision() -> Decision:
    return Decision(
        status="confirmed",
        confirmation_count=2,
        strong_alert=True,
        blocked=False,
        requires_human_approval=True,
        reasons=("minimum_confirmation_threshold_met",),
    )


def test_clean_spot_proposal_is_eligible_for_human_review():
    result = evaluate_risk_gate(
        confirmed_decision(),
        TradeProposal(asset="NVDA", stop_loss_defined=True),
        new_entries_this_week=0,
    )
    assert result.eligible_for_review is True
    assert result.blocked is False
    assert result.requires_human_approval is True


def test_options_and_leverage_are_blocked():
    result = evaluate_risk_gate(
        confirmed_decision(),
        TradeProposal(
            asset="NVDA",
            instrument_type="options",
            leverage=2.0,
            stop_loss_defined=True,
        ),
        new_entries_this_week=0,
    )
    assert result.blocked is True
    assert "options_prohibited" in result.reasons
    assert "leverage_prohibited" in result.reasons


def test_weekly_limit_blocks_third_new_entry():
    result = evaluate_risk_gate(
        confirmed_decision(),
        TradeProposal(asset="BTC", stop_loss_defined=True),
        new_entries_this_week=2,
    )
    assert result.blocked is True
    assert "weekly_entry_limit_reached" in result.reasons


def test_missing_stop_loss_blocks_entry():
    result = evaluate_risk_gate(
        confirmed_decision(),
        TradeProposal(asset="ETH", stop_loss_defined=False),
        new_entries_this_week=0,
    )
    assert result.blocked is True
    assert "risk_control_required_before_entry" in result.reasons


def test_insider_selling_is_warning_not_automatic_block():
    result = evaluate_risk_gate(
        confirmed_decision(),
        TradeProposal(
            asset="NVDA",
            stop_loss_defined=True,
            insider_selling_warning=True,
        ),
        new_entries_this_week=0,
    )
    assert result.blocked is False
    assert result.warnings == ("insider_selling_warning",)
    assert result.requires_human_approval is True


def test_ineligible_signal_is_blocked_before_review():
    decision = Decision(
        status="watch",
        confirmation_count=1,
        strong_alert=False,
        blocked=True,
        requires_human_approval=True,
        reasons=("insufficient_independent_confirmations",),
    )
    result = evaluate_risk_gate(
        decision,
        TradeProposal(asset="NVDA", stop_loss_defined=True),
        new_entries_this_week=0,
    )
    assert result.blocked is True
    assert "signal_not_eligible" in result.reasons
