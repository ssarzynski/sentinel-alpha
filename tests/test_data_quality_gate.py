from app.data_quality_gate import evaluate_data_quality_gate


def row(asset="NVDA", accepted=10, rejected=0, families=2, fresh=True):
    return {"asset": asset, "accepted_observations": accepted, "rejected_observations": rejected, "independent_source_families": families, "fresh": fresh}


def test_pass_requires_fresh_independently_confirmed_data():
    result = evaluate_data_quality_gate([row()])
    assert result.status == "PASS"
    assert result.risk_signals_allowed is True
    assert result.findings == ()


def test_confirmation_gap_withholds_risk_signals():
    result = evaluate_data_quality_gate([row(families=1)])
    assert result.status == "WITHHOLD"
    assert result.risk_signals_allowed is False
    assert any(f.code == "insufficient_independent_confirmation" for f in result.findings)


def test_stale_data_withholds_risk_signals():
    result = evaluate_data_quality_gate([row(fresh=False)])
    assert result.status == "WITHHOLD"
    assert any(f.code == "stale_market_data" for f in result.findings)


def test_no_accepted_data_is_explicit_block():
    result = evaluate_data_quality_gate([row(accepted=0, families=0, fresh=False)])
    assert result.status == "WITHHOLD"
    assert any(f.code == "no_accepted_data" for f in result.findings)


def test_rejected_observations_degrade_but_do_not_replace_accepted_consensus():
    result = evaluate_data_quality_gate([row(rejected=3)])
    assert result.status == "DEGRADED"
    assert result.risk_signals_allowed is True
    assert result.findings[0].severity == "warning"


def test_any_blocking_asset_withholds_portfolio_risk_signals():
    result = evaluate_data_quality_gate([row("NVDA"), row("BTC", families=1)])
    assert result.status == "WITHHOLD"
    assert result.risk_signals_allowed is False
