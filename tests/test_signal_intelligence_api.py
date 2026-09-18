from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.api import studio_signal_intelligence

NOW=datetime(2026,9,18,12,0,tzinfo=timezone.utc)


def call(assets, *, max_age_hours=168):
    db=Mock(); user=Mock()
    with patch("app.api.datetime") as clock, patch("app.api.signal_intelligence_watchlist") as service:
        clock.now.return_value=NOW
        service.return_value=[{"asset":"NVDA","evidence_count":3,"confirmation_count":1,"source_families":["SEC"],"state":"developing","human_review_required":False,"insider_sale_warning":False,"reasons":["fewer_than_two_independent_evidence_confirmations"]}]
        result=studio_signal_intelligence(assets=assets,max_age_hours=max_age_hours,db=db,user=user)
        service.assert_called_once()
        args,kwargs=service.call_args
        return result,args,kwargs


def test_signal_endpoint_returns_read_only_projection_and_normalizes_assets():
    result,args,kwargs=call([" nvda ","BTC"])
    assert result[0]["state"]=="developing"
    assert result[0]["confirmation_count"]==1
    assert args[1]==["NVDA","BTC"]
    assert kwargs["max_age"].total_seconds()==168*3600


def test_signal_endpoint_rejects_empty_asset_request():
    with pytest.raises(HTTPException) as exc:
        studio_signal_intelligence(assets=["  "],max_age_hours=168,db=Mock(),user=Mock())
    assert exc.value.status_code==422


def test_signal_endpoint_rejects_more_than_100_assets():
    with pytest.raises(HTTPException) as exc:
        studio_signal_intelligence(assets=[f"A{i}" for i in range(101)],max_age_hours=168,db=Mock(),user=Mock())
    assert exc.value.status_code==422


def test_signal_endpoint_has_no_mutating_side_effect_contract():
    result,_,_=call(["NVDA"])
    assert set(result[0])=={"asset","evidence_count","confirmation_count","source_families","state","human_review_required","insider_sale_warning","reasons"}
