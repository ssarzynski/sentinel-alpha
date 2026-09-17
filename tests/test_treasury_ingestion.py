from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest

from sentinel_alpha.macro_regime import MacroInput
from sentinel_alpha.treasury_ingestion import (
    TreasuryClient,
    cross_validate_yields,
    treasury_macro_inputs,
)

XML = b'''<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
 xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"
 xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices">
 <entry><content type="application/xml"><m:properties>
  <d:NEW_DATE>2026-09-16T00:00:00</d:NEW_DATE>
  <d:BC_2YEAR>3.75</d:BC_2YEAR><d:BC_10YEAR>4.12</d:BC_10YEAR>
 </m:properties></content></entry>
 <entry><content type="application/xml"><m:properties>
  <d:NEW_DATE>2026-09-17T00:00:00</d:NEW_DATE>
  <d:BC_2YEAR>3.72</d:BC_2YEAR><d:BC_10YEAR>4.10</d:BC_10YEAR>
 </m:properties></content></entry>
</feed>'''


class Response(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_treasury_client_reads_latest_complete_yields():
    seen = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        return Response(XML)

    item = TreasuryClient(opener=opener).latest(year=2026)
    assert item.treasury_2y == 3.72
    assert item.treasury_10y == 4.10
    assert item.observed_at == datetime(2026, 9, 17, tzinfo=timezone.utc)
    assert "data=daily_treasury_yield_curve" in seen["url"]
    assert "field_tdr_date_value=2026" in seen["url"]


def test_treasury_observation_becomes_macro_inputs():
    item = TreasuryClient(opener=lambda request, timeout: Response(XML)).latest(year=2026)
    inputs = treasury_macro_inputs(item, max_age=timedelta(days=5))
    assert inputs["treasury_2y"].source == "treasury:daily_treasury_yield_curve"
    assert inputs["treasury_10y"].value == 4.10


def _input(metric, value):
    return MacroInput(
        metric,
        value,
        datetime(2026, 9, 17, tzinfo=timezone.utc),
        "test",
        timedelta(days=5),
    )


def test_cross_validation_reports_difference_without_overwriting():
    primary = {
        "treasury_2y": _input("treasury_2y", 3.72),
        "treasury_10y": _input("treasury_10y", 4.10),
    }
    comparison = {
        "treasury_2y": _input("treasury_2y", 3.74),
        "treasury_10y": _input("treasury_10y", 4.18),
    }
    checks = cross_validate_yields(primary, comparison, tolerance=0.05)
    assert checks[0].within_tolerance is True
    assert checks[1].within_tolerance is False
    assert primary["treasury_10y"].value == 4.10


def test_cross_validation_fails_closed_on_missing_metric():
    with pytest.raises(ValueError, match="missing treasury_10y"):
        cross_validate_yields(
            {
                "treasury_2y": _input("treasury_2y", 3.7),
                "treasury_10y": _input("treasury_10y", 4.1),
            },
            {"treasury_2y": _input("treasury_2y", 3.7)},
        )


def test_negative_tolerance_is_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        cross_validate_yields({}, {}, tolerance=-0.01)
