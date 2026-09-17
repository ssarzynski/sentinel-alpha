import json
from urllib.parse import parse_qs, urlparse

import pytest

from sentinel_alpha.fred_ingestion import FRED_SERIES, FredClient, load_macro_inputs


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_latest_skips_missing_values_and_requests_json():
    seen = {}

    def opener(request, timeout):
        seen.update(parse_qs(urlparse(request.full_url).query))
        return Response(
            {
                "observations": [
                    {"date": "2026-09-17", "value": "."},
                    {"date": "2026-09-16", "value": "4.25"},
                ]
            }
        )

    observation = FredClient("a" * 32, opener=opener).latest("DGS10")
    assert observation.value == 4.25
    assert observation.date.isoformat() == "2026-09-16T00:00:00+00:00"
    assert seen["series_id"] == ["DGS10"]
    assert seen["file_type"] == ["json"]
    assert seen["sort_order"] == ["desc"]


def test_cpi_is_requested_as_year_over_year_percent_change():
    calls = []

    def opener(request, timeout):
        calls.append(parse_qs(urlparse(request.full_url).query))
        return Response({"observations": [{"date": "2026-09-01", "value": "2.4"}]})

    inputs = load_macro_inputs(FredClient("b" * 32, opener=opener))
    cpi_series = FRED_SERIES["inflation_yoy"]
    cpi_call = next(call for call in calls if call["series_id"] == [cpi_series])
    assert cpi_call["units"] == ["pc1"]
    assert inputs["inflation_yoy"].value == 2.4
    assert inputs["inflation_yoy"].source == "fred:CPIAUCSL"


def test_no_numeric_observation_fails_closed():
    def opener(request, timeout):
        return Response({"observations": [{"date": "2026-09-17", "value": "."}]})

    with pytest.raises(ValueError, match="no numeric observations"):
        FredClient("c" * 32, opener=opener).latest("DGS2")


def test_api_key_is_required():
    with pytest.raises(ValueError, match="API key"):
        FredClient("  ")
