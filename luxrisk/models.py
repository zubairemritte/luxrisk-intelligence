"""Shared data contracts and calendar validation; no network or database operations."""

import math
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Literal

type JsonObject = dict[str, Any]
type Mode = Literal["demo", "live"]


def period_end(period: str) -> date:
    """Translate an observation period to its final calendar day.

    Args:
        period: ISO-like month (2025-01) or quarter (2025-Q1).

    Returns:
        The period's final calendar date; does not imply publication availability.

    Raises:
        ValueError: The period has an invalid shape or calendar component.

    Side effects:
        None.

    """
    import calendar

    match: re.Match[str] | None = re.fullmatch(r"(\d{4})-(\d{2}|Q[1-4])", period)
    if match is None:
        raise ValueError(f"Unsupported period: {period!r}")
    year: int = int(match[1])
    month: int = int(match[2][1:]) * 3 if "Q" in match[2] else int(match[2])
    return date(year, month, calendar.monthrange(year, month)[1])


def period_number(period: str) -> int:
    """Map a monthly or quarterly label to an integer within its frequency.

    Args:
        period: Valid month or quarter label.

    Returns:
        A consecutive integer useful for detecting missing periods.

    Raises:
        ValueError: The calendar label is invalid.

    Side effects:
        None; do not compare monthly numbers with quarterly numbers.

    """
    period_end(period)
    year: int = int(period[:4])
    return year * 4 + int(period[-1]) - 1 if "Q" in period else year * 12 + int(period[-2:]) - 1


def utc_now() -> str:
    """Return the current UTC ingestion timestamp as an ISO 8601 string.

    Returns:
        A timezone-aware timestamp; not an observation publication time.

    Side effects:
        Reads the system clock and changes no files.

    """
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class Indicator:
    """Describe one precisely defined series; instances contain metadata, not observations."""

    id: str
    title: str
    provider: str
    dataset: str
    frequency: str
    unit: str
    definition: str
    filters: tuple[tuple[str, str], ...]
    lag_days: int


@dataclass(frozen=True, slots=True)
class Observation:
    """Represent one validated value or an explicit missing observation."""

    country: str
    indicator: str
    period: str
    value: float | None
    status: str = ""

    def __post_init__(self) -> None:
        """Validate a normalized row immediately after construction.

        Raises:
            ValueError: Period, entity, identifier or numeric value is invalid.

        Side effects:
            None; frozen fields are never modified.

        """
        period_end(self.period)
        if not re.fullmatch(r"[A-Z]{2}", self.country) or not self.indicator:
            raise ValueError("Use a two-letter entity and a nonempty indicator ID")
        if self.value is not None and (
            isinstance(self.value, bool) or not math.isfinite(self.value)
        ):
            raise ValueError("Values must be finite numbers or None")


@dataclass(frozen=True, slots=True)
class SourceBatch:
    """Keep exact source bytes and normalized observations together until atomic publication."""

    indicator: str
    country: str
    url: str
    retrieved_at: str
    payload: bytes
    observations: tuple[Observation, ...]
