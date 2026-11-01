"""Explainable, frequency-aware calculations; no networking, persistence or hidden imputation."""

import math
import statistics
from datetime import date

from luxrisk.catalog import indicator_spec
from luxrisk.models import JsonObject, Observation, period_end, period_number


def contiguous_tail(rows: tuple[Observation, ...]) -> tuple[Observation, ...]:
    """Select the latest usable contiguous segment without filling calendar gaps.

    Args:
        rows: Unique observations from one country, indicator and frequency.

    Returns:
        A sorted suffix ending at the latest supplied period; empty if its value is missing.
        A source break/different-definition flag starts a new segment.

    Raises:
        ValueError: Series identities, frequencies or period uniqueness differ.

    Side effects:
        None; never modifies rows or bridges missing periods.

    """
    if not rows:
        return ()
    identities: set[tuple[str, str, bool]] = {
        (r.country, r.indicator, "Q" in r.period) for r in rows
    }
    if len(identities) != 1 or len({r.period for r in rows}) != len(rows):
        raise ValueError("Analysis requires one unique single-frequency series")
    ordered: list[Observation] = sorted(rows, key=lambda row: row.period)
    if ordered[-1].value is None:
        return ()
    tail: list[Observation] = []
    next_number: int | None = None
    for row in reversed(ordered):
        number: int = period_number(row.period)
        if row.value is None or (next_number is not None and number != next_number - 1):
            break
        tail.append(row)
        if set(row.status.replace(",", " ").split()) & {"b", "d"}:
            break
        next_number = number
    return tuple(reversed(tail))


def summarize(rows: tuple[Observation, ...], today: date | None = None) -> JsonObject:
    """Describe observed levels, percentage-point movements and freshness honestly.

    Args:
        rows: One series; explicit null cells remain missing.
        today: Optional reference date for reproducible freshness checks.

    Returns:
        Latest usable period/value, last returned period, missing-cell count, consecutive
        change and a project-defined freshness warning; empty state when no values exist.

    Raises:
        ValueError: Mixed series reach the analysis contract.

    Side effects:
        Reads today's date only when no reference is provided; no file writes.

    """
    contiguous_tail(rows)
    usable: list[Observation] = [
        row for row in sorted(rows, key=lambda row: row.period) if row.value is not None
    ]
    if not usable:
        return {"available": False, "missing": len(rows)}
    latest: Observation = usable[-1]
    spec = indicator_spec(latest.indicator)
    age: int = ((today or date.today()) - period_end(latest.period)).days
    change: float | None = None
    if (
        len(usable) >= 2
        and period_number(latest.period) - period_number(usable[-2].period) == 1
        and not set(latest.status.replace(",", " ").split()) & {"b", "d"}
    ):
        assert latest.value is not None and usable[-2].value is not None
        change = latest.value - usable[-2].value
    return {
        "available": True,
        "period": latest.period,
        "value": latest.value,
        "last_returned_period": max(row.period for row in rows),
        "status": latest.status,
        "unit": spec.unit,
        "change": change,
        "change_unit": "USD per EUR" if spec.id == "eurusd" else "percentage points",
        "missing": len(rows) - len(usable),
        "age_days": age,
        "freshness_limit_days": spec.lag_days,
        "stale": age > spec.lag_days,
        "freshness_rule": "Project threshold from period end; not an official publication deadline",
    }


def anomaly_signal(
    rows: tuple[Observation, ...], window: int = 12, threshold: float = 3.0
) -> JsonObject:
    """Compare the latest value with a strictly earlier, contiguous reference window.

    Args:
        rows: One series with no cross-frequency mixing.
        window: Number of prior periods, between 4 and 60.
        threshold: Positive absolute z-score threshold, default 3.

    Returns:
        Availability, mean, sample standard deviation, observed value and a transparent flag.
        A flat reference produces no z-score; a changed value is labelled a flat-baseline shift.

    Raises:
        ValueError: Invalid window/threshold or mixed series.

    Side effects:
        None; this is an investigation rule, not a labelled anomaly classifier.

    """
    if not 4 <= window <= 60 or not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("Use a 4..60 reference window and a positive finite threshold")
    tail = contiguous_tail(rows)
    if len(tail) < window + 1:
        return {
            "available": False,
            "reason": "Insufficient contiguous history or a missing latest value",
        }
    values: list[float] = [float(row.value) for row in tail[-window - 1 :] if row.value is not None]
    reference: list[float] = values[:-1]
    mean: float = statistics.mean(reference)
    scale: float = statistics.stdev(reference)
    observed: float = values[-1]
    score: float | None = (observed - mean) / scale if scale > 0 else None
    return {
        "available": True,
        "period": tail[-1].period,
        "observed": observed,
        "reference_start": tail[-window - 1].period,
        "reference_end": tail[-2].period,
        "window": window,
        "mean": mean,
        "sample_std": scale,
        "z_score": score,
        "threshold": threshold,
        "flagged": abs(score) >= threshold if score is not None else observed != mean,
        "rule": "prior_window_z_score" if scale else "flat_baseline_shift",
        "latest_source_status": tail[-1].status,
    }


def evaluate_forecast(
    rows: tuple[Observation, ...], min_train: int = 12, max_origins: int = 24
) -> JsonObject:
    """Evaluate naive and drift one-step baselines on identical expanding-window origins.

    Args:
        rows: One series; only its latest contiguous, nonmissing segment is usable.
        min_train: Minimum training observations, from 4 to 120.
        max_origins: Evaluation budget from 1 to 60 most recent one-step origins.

    Returns:
        MAE/RMSE for both models, audited origin predictions, selected baseline and next-step
        conditional estimate. Scores use the currently selected vintage, not historic releases.

    Raises:
        ValueError: Invalid budgets or mixed series.

    Side effects:
        None; no training artifact, network request or future value enters an origin's fit.

    """
    if not 4 <= min_train <= 120 or not 1 <= max_origins <= 60:
        raise ValueError("Invalid expanding-window evaluation budget")
    tail = contiguous_tail(rows)
    if len(tail) <= min_train:
        return {"available": False, "reason": "Need more contiguous observations than min_train"}
    values: list[float] = [float(row.value) for row in tail if row.value is not None]
    origins: list[JsonObject] = []
    for position in range(max(min_train, len(values) - max_origins), len(values)):
        train: list[float] = values[:position]
        origins.append(
            {
                "train_end": tail[position - 1].period,
                "target": tail[position].period,
                "actual": values[position],
                "naive": train[-1],
                "drift": train[-1] + (train[-1] - train[0]) / (len(train) - 1),
            }
        )
    metrics: JsonObject = {}
    for model in ("naive", "drift"):
        errors: list[float] = [float(origin[model]) - float(origin["actual"]) for origin in origins]
        metrics[model] = {
            "mae": statistics.mean(abs(error) for error in errors),
            "rmse": math.sqrt(statistics.mean(error * error for error in errors)),
        }
    selected: str = "drift" if metrics["drift"]["mae"] < metrics["naive"]["mae"] else "naive"
    estimate: float = (
        values[-1]
        if selected == "naive"
        else values[-1] + (values[-1] - values[0]) / (len(values) - 1)
    )
    return {
        "available": True,
        "models": metrics,
        "selected": selected,
        "origins": origins,
        "train_end": tail[-1].period,
        "horizon_periods": 1,
        "estimate": estimate,
        "evaluation_basis": "Current-vintage rolling-origin errors; model selection uses the same evaluation window",
        "limitation": "No historical publication vintages or independent final holdout; no calibrated interval",
    }


def revision_diff(
    previous: tuple[Observation, ...], current: tuple[Observation, ...]
) -> list[JsonObject]:
    """Explain added, removed, revised and flag-only cells between two collected vintages.

    Args:
        previous: Earlier successful slice.
        current: Later successful slice for the same entity and indicator.

    Returns:
        Changed periods with old/new value and flags. Removed rows may reflect a different
        requested window; they are not automatically classified as provider revisions.

    Raises:
        ValueError: Either input mixes identities/frequencies, or their series differ.

    Side effects:
        None; an absent cell and a present null cell are distinct.

    """
    contiguous_tail(previous)
    contiguous_tail(current)
    if (
        previous
        and current
        and (previous[0].country, previous[0].indicator)
        != (current[0].country, current[0].indicator)
    ):
        raise ValueError("Cannot compare vintages of different series")
    old: dict[str, Observation] = {row.period: row for row in previous}
    new: dict[str, Observation] = {row.period: row for row in current}
    changes: list[JsonObject] = []
    for period in sorted(old.keys() | new.keys()):
        before: Observation | None = old.get(period)
        after: Observation | None = new.get(period)
        if before == after:
            continue
        kind: str = (
            "added"
            if before is None
            else "outside_new_slice"
            if after is None
            else "value_revision"
            if before.value != after.value
            else "status_revision"
        )
        changes.append(
            {
                "period": period,
                "kind": kind,
                "old_value": before.value if before else None,
                "new_value": after.value if after else None,
                "old_status": before.status if before else None,
                "new_status": after.status if after else None,
            }
        )
    return changes


def exposure_scenario(
    imports_usd: float,
    eurusd: float,
    fx_shock_pct: float,
    floating_debt_eur: float,
    rate_shock_bps: float,
) -> JsonObject:
    """Translate explicit currency/rate assumptions into mechanical EUR exposure changes.

    Args:
        imports_usd: Fixed USD invoice amount, nonnegative.
        eurusd: Baseline USD per EUR, strictly positive.
        fx_shock_pct: Percentage change in USD per EUR, greater than -100.
        floating_debt_eur: Floating-rate debt principal, nonnegative.
        rate_shock_bps: Change in annual rate in basis points; 100 bps equals 1 percentage point.

    Returns:
        Base/stressed EUR invoice, invoice delta, annual interest delta and separate assumptions.
        Invoice change and annual interest change are deliberately not summed across time bases.

    Raises:
        ValueError: Inputs are nonfinite, negative amounts or imply a nonpositive FX rate.

    Side effects:
        None; no pass-through, hedging, refinancing or behavioural response is inferred.

    """
    inputs: tuple[float, ...] = (
        imports_usd,
        eurusd,
        fx_shock_pct,
        floating_debt_eur,
        rate_shock_bps,
    )
    if (
        not all(math.isfinite(value) for value in inputs)
        or min(imports_usd, floating_debt_eur) < 0
        or eurusd <= 0
        or fx_shock_pct <= -100
    ):
        raise ValueError(
            "Use finite nonnegative exposures, positive EURUSD and FX shock above -100%"
        )
    stressed: float = eurusd * (1 + fx_shock_pct / 100)
    return {
        "base_eurusd": eurusd,
        "stressed_eurusd": stressed,
        "base_invoice_eur": imports_usd / eurusd,
        "stressed_invoice_eur": imports_usd / stressed,
        "invoice_delta_eur": imports_usd / stressed - imports_usd / eurusd,
        "annual_interest_delta_eur": floating_debt_eur * rate_shock_bps / 10_000,
        "assumptions": "Fixed USD invoice; unhedged; entire stated debt reprices for one year; no forecast or credit rating",
    }
