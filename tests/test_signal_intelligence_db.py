from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Evidence
from app.services.signal_intelligence import evidence_fact, signal_intelligence_for_asset

NOW=datetime(2026,9,18,12,0,tzinfo=timezone.utc)

@pytest.fixture
def db_session():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session=sessionmaker(bind=engine)
    db=Session()
    try: yield db
    finally:
        db.close();engine.dispose()


def row(key,family,*,days=0,payload=None):
    return Evidence(evidence_key=key,asset="NVDA",category="test",source=family,source_family=family,source_record_id=key,title=key,source_url="https://example.test/"+key,observed_at=NOW-timedelta(days=days),payload_json=payload or {})


def test_persisted_duplicate_sec_rows_remain_one_confirmation(db_session):
    db_session.add_all([row("sec-1","SEC"),row("sec-2","SEC"),row("sec-3","SEC")]);db_session.commit()
    result=signal_intelligence_for_asset(db_session,"NVDA",now=NOW)
    assert result.evidence_count==3
    assert result.confirmation_count==1
    assert result.source_families==("SEC",)
    assert result.state=="developing"


def test_persisted_independent_family_supplies_second_confirmation(db_session):
    db_session.add_all([row("sec-1","SEC"),row("market-1","MARKET")]);db_session.commit()
    result=signal_intelligence_for_asset(db_session,"nvda",now=NOW)
    assert result.confirmation_count==2
    assert result.state=="confirmed_review"
    assert result.human_review_required is True


def test_persisted_stale_family_cannot_confirm(db_session):
    db_session.add_all([row("sec-1","SEC"),row("market-old","MARKET",days=8)]);db_session.commit()
    result=signal_intelligence_for_asset(db_session,"NVDA",now=NOW)
    assert result.confirmation_count==1
    assert result.state=="developing"


def test_normalized_open_market_sale_sets_warning_without_extra_confirmation():
    fact=evidence_fact(row("sale","SEC",payload={"classification":{"signal_eligible":True,"economic_type":"open_market","direction":"sale"}}))
    assert fact.signal_eligible is True
    assert fact.insider_sale is True


def test_ineligible_normalized_transaction_does_not_set_sale_warning():
    fact=evidence_fact(row("tax","SEC",payload={"classification":{"signal_eligible":False,"economic_type":"open_market","direction":"sale"}}))
    assert fact.signal_eligible is False
    assert fact.insider_sale is False
