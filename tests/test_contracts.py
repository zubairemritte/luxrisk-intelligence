import json
from pathlib import Path

import pytest
from conftest import batch

from luxrisk.catalog import indicator_spec
from luxrisk.connectors import ECBConnector, EurostatConnector, SourceError, get_bytes
from luxrisk.models import Observation, period_end
from luxrisk.pipeline import CollectionService, validate_batch


def test_jsonstat_preserves_missing_values_flags_and_dimension_order(eurostat_payload):
    rows = EurostatConnector().normalize(eurostat_payload, indicator_spec("inflation"), "DE")
    assert [row.value for row in rows] == [1.0, None, 3.0]
    assert rows[-1].status == "p"


def test_wrong_geography_or_extra_dimension_is_rejected(eurostat_payload):
    raw = json.loads(eurostat_payload)
    raw["dimension"]["geo"]["category"]["index"] = {"FR": 0}
    with pytest.raises(SourceError, match="selector"):
        EurostatConnector().normalize(json.dumps(raw).encode(), indicator_spec("inflation"), "DE")
    raw["id"].append("unexpected")
    raw["size"].append(1)
    with pytest.raises(SourceError, match="dimensions"):
        EurostatConnector().normalize(json.dumps(raw).encode(), indicator_spec("inflation"), "DE")


def test_ecb_unit_and_direction_are_enforced():
    payload = Path(__file__).with_name("fixtures").joinpath("ecb-authored.csv").read_bytes()
    rows = ECBConnector().normalize(payload)
    assert rows[0].country == "EA" and rows[0].value == 1.1
    assert rows[1].value is None
    with pytest.raises(SourceError, match="scaling"):
        ECBConnector().normalize(payload.replace(b"USD,0", b"USD,2"))


def test_domain_duplicate_and_calendar_validation():
    with pytest.raises(ValueError):
        Observation("DE", "inflation", "2025-13", 1.0)
    with pytest.raises(ValueError):
        Observation("DE", "inflation", "2025-01", float("nan"))
    with pytest.raises(ValueError, match="0..100"):
        validate_batch(batch(indicator="unemployment", values=(101.0,)))
    with pytest.raises(ValueError, match="duplicate"):
        validate_batch(batch(periods=["2025-01", "2025-01"]))
    assert str(period_end("2024-02")) == "2024-02-29"


def test_mixed_frequency_request_is_rejected_before_network(store, eurostat_payload):
    requests = []

    def fetch(url):
        requests.append(url)
        return eurostat_payload

    with pytest.raises(ValueError, match="separate"):
        CollectionService(store, EurostatConnector(fetch)).collect(
            "DE", ["inflation", "gdp"], "2025-01", "2025-03"
        )
    assert requests == []
    assert not store.path.exists()


def test_unapproved_endpoint_is_rejected_without_request():
    with pytest.raises(SourceError, match="official"):
        get_bytes("https://example.com/not-an-approved-provider")


def test_long_retry_after_never_retries_early(monkeypatch):
    from email.message import Message
    from urllib.error import HTTPError

    headers = Message()
    headers["Retry-After"] = "60"
    requests = []

    def failed_open(*args, **kwargs):
        requests.append(1)
        raise HTTPError("url", 429, "slow down", headers, None)

    monkeypatch.setattr("luxrisk.connectors.urlopen", failed_open)
    with pytest.raises(SourceError, match="429"):
        get_bytes("https://data-api.ecb.europa.eu/service/data/test")
    assert len(requests) == 1
