"""Tiny authored fixtures; no full demo or public-provider request is used by tests."""

import json
from pathlib import Path

import pytest

from luxrisk.models import Observation, SourceBatch
from luxrisk.warehouse import Warehouse


@pytest.fixture
def store(tmp_path):
    """Provide an isolated ledger path; construction creates no database."""
    return Warehouse(tmp_path / "test.sqlite")


@pytest.fixture
def eurostat_payload():
    """Provide two authored inflation values and one explicit missing cell."""
    return Path(__file__).with_name("fixtures").joinpath("eurostat-authored.json").read_bytes()


def batch(country="DE", indicator="inflation", values=(1.0, 2.0), periods=None, statuses=None):
    """Build a minimal auditable test batch, independent of the full demo generator."""
    periods = periods or [f"2025-{index + 1:02}" for index in range(len(values))]
    statuses = statuses or [""] * len(values)
    rows = tuple(
        Observation(country, indicator, period, value, status)
        for period, value, status in zip(periods, values, statuses, strict=True)
    )
    payload = json.dumps({"fixture": "authored", "values": values}).encode()
    return SourceBatch(
        indicator, country, "fixture://authored", "2026-11-01T12:00:00+00:00", payload, rows
    )
