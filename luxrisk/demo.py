"""Deterministic authored demonstration, kept separate from collected official statistics."""

import json
import math
from dataclasses import asdict

from luxrisk.models import Observation, SourceBatch, utc_now
from luxrisk.pipeline import validate_batch
from luxrisk.warehouse import Warehouse


def create_demo(store: Warehouse) -> int:
    """Publish a labelled illustrative ledger on the user's own machine.

    Args:
        store: Local ledger owner; existing vintages are preserved.

    Returns:
        Run ID for 13 synthetic series: four countries with three indicators, plus shared FX.

    Raises:
        ValueError: Generated data violates a shared validation contract.
        sqlite3.Error: Atomic publication fails.

    Side effects:
        Generates 36 monthly or 12 quarterly periods and appends one demo vintage.
        Does not call a source API; numbers are authored illustrations, not economic estimates.

    """
    batches: list[SourceBatch] = []
    for country_index, country in enumerate(("DE", "FR", "ES", "NL")):
        for indicator in ("inflation", "unemployment", "gdp"):
            count: int = 12 if indicator == "gdp" else 36
            rows: list[Observation] = []
            for index in range(count):
                period: str = (
                    f"{2023 + index // 4}-Q{index % 4 + 1}"
                    if indicator == "gdp"
                    else f"{2023 + index // 12}-{index % 12 + 1:02}"
                )
                value: float = (
                    0.3 + 0.25 * math.sin(index / 2) - country_index * 0.04
                    if indicator == "gdp"
                    else 4.0 + country_index * 0.5 - index * 0.045 + math.sin(index / 3) * 0.25
                    if indicator == "inflation"
                    else 4.8 + country_index * 0.8 + math.sin(index / 5) * 0.2
                )
                rows.append(Observation(country, indicator, period, round(value, 3), "demo"))
            payload: bytes = json.dumps([asdict(row) for row in rows], sort_keys=True).encode()
            batches.append(
                SourceBatch(
                    indicator,
                    country,
                    "demo://authored/" + indicator,
                    utc_now(),
                    payload,
                    tuple(rows),
                )
            )
    fx: tuple[Observation, ...] = tuple(
        Observation(
            "EA",
            "eurusd",
            f"{2023 + index // 12}-{index % 12 + 1:02}",
            round(1.08 + math.sin(index / 6) * 0.025, 4),
            "demo",
        )
        for index in range(36)
    )
    batches.append(
        SourceBatch(
            "eurusd",
            "EA",
            "demo://authored/eurusd",
            utc_now(),
            json.dumps([asdict(row) for row in fx], sort_keys=True).encode(),
            fx,
        )
    )
    for batch in batches:
        validate_batch(batch)
    return store.publish(
        tuple(batches), "demo", "Deterministic authored illustration; not official data"
    )
