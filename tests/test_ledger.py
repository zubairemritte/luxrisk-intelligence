import hashlib
import sqlite3

import pytest
from conftest import batch

from luxrisk.connectors import EurostatConnector, SourceError
from luxrisk.pipeline import CollectionService
from luxrisk.reporting import compare_countries, export_pack, series_report


def test_atomic_publish_preserves_raw_bytes_and_isolates_modes(store):
    live = batch(values=(1.0, 2.0))
    run = store.publish((live,), "live", "authored live-path test")
    store.publish((batch(values=(50.0, 60.0)),), "demo", "authored demo-path test")
    assert store.read_series("DE", "inflation", "live")["rows"][-1]["value"] == 2.0
    assert store.read_series("DE", "inflation", "live")["run_id"] == run
    with sqlite3.connect(store.path) as conn:
        payload, digest = conn.execute(
            "SELECT payload,sha256 FROM raw_response WHERE run_id=?", (run,)
        ).fetchone()
    assert payload == live.payload
    assert digest == hashlib.sha256(payload).hexdigest()


def test_duplicate_publish_rolls_back_entire_vintage(store):
    original = store.publish((batch(),), "live", "first")
    with pytest.raises(sqlite3.IntegrityError):
        store.publish(
            (batch(values=(5.0, 6.0)), batch(values=(9.0, 10.0))), "live", "invalid duplicate"
        )
    assert store.vintages("DE", "inflation", "live") == [original]


def test_failure_after_first_fetch_does_not_publish_partial_batch(store, eurostat_payload):
    original = store.publish((batch(),), "live", "original")
    requests = []

    def fetch(url):
        requests.append(url)
        if len(requests) == 2:
            raise SourceError("authored failure")
        return eurostat_payload

    with pytest.raises(SourceError, match="authored failure"):
        CollectionService(store, EurostatConnector(fetch)).collect(
            "DE", ["inflation", "unemployment"], "2025-01", "2025-03"
        )
    assert len(requests) == 2
    assert store.vintages("DE", "inflation", "live") == [original]
    with sqlite3.connect(store.path) as conn:
        assert (
            conn.execute("SELECT COUNT(*) FROM collection WHERE status='failed'").fetchone()[0] == 1
        )


def test_peer_comparison_uses_actual_common_period(store):
    store.publish(
        (
            batch(values=(3.0, 2.0)),
            batch(country="FR", values=(4.0, 5.0), periods=["2025-01", "2025-03"]),
        ),
        "demo",
        "different calendars",
    )
    result = compare_countries(store, ["DE", "FR"], "inflation", "demo")
    assert result["period"] == "2025-01"
    assert [peer["value"] for peer in result["peers"]] == [3.0, 4.0]


def test_exact_vintage_and_revision_explanation(store):
    old = store.publish((batch(values=(1.0, 2.0)),), "demo", "old")
    new = store.publish((batch(values=(1.0, 3.0), statuses=["p", ""]),), "demo", "new")
    report = series_report(store, "DE", "inflation", "demo")
    assert report["run_id"] == new
    assert {r["kind"] for r in report["revisions"]} == {"status_revision", "value_revision"}
    assert series_report(store, "DE", "inflation", "demo", old)["summary"]["value"] == 2.0


def test_export_pins_vintages_and_refuses_existing_destination(store, tmp_path):
    import csv
    import json

    run = store.publish((batch(),), "demo", "tiny export")
    target = tmp_path / "export"
    result = export_pack(store, "demo", target)
    assert result["observations"] == 2
    manifest = json.loads((target / "manifest.json").read_text())
    assert manifest["sources"][0]["run_id"] == run
    with (target / "fact_observation.csv").open(encoding="utf-8-sig", newline="") as stream:
        assert list(csv.DictReader(stream))[0]["period_end"] == "2025-01-31"
    with pytest.raises(FileExistsError):
        export_pack(store, "demo", target)
