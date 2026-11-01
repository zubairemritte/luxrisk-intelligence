import math
from datetime import date

import pytest

from luxrisk.analysis import (
    anomaly_signal,
    contiguous_tail,
    evaluate_forecast,
    exposure_scenario,
    revision_diff,
    summarize,
)
from luxrisk.models import Observation


def rows(values, start=1):
    return tuple(
        Observation("DE", "inflation", f"2025-{i + start:02}", value)
        for i, value in enumerate(values)
    )


def test_anomaly_uses_prior_window_and_sample_standard_deviation():
    result = anomaly_signal(rows([1.0, 2.0, 3.0, 4.0, 10.0]), window=4)
    assert result["mean"] == 2.5
    assert result["sample_std"] == pytest.approx(math.sqrt(5 / 3))
    assert result["z_score"] == pytest.approx(7.5 / math.sqrt(5 / 3))
    assert result["flagged"] is True


def test_flat_reference_is_explicit_and_never_produces_infinity():
    result = anomaly_signal(rows([2.0, 2.0, 2.0, 2.0, 3.0]), window=4)
    assert result["rule"] == "flat_baseline_shift" and result["z_score"] is None
    assert result["flagged"] is True


def test_forecast_has_hand_calculated_errors_and_no_future_leakage():
    result = evaluate_forecast(rows([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]), min_train=4)
    assert result["models"]["naive"]["mae"] == 1.0
    assert result["models"]["drift"]["rmse"] == 0.0
    assert result["selected"] == "drift" and result["estimate"] == 7.0
    perturbed = evaluate_forecast(rows([1.0, 2.0, 3.0, 4.0, 5.0, 90.0]), min_train=4)
    assert result["origins"][0] == perturbed["origins"][0]
    assert result["origins"][1]["drift"] == perturbed["origins"][1]["drift"]


def test_missing_periods_and_breaks_prevent_bridging():
    assert len(contiguous_tail(rows([1.0, None, 3.0, 4.0]))) == 2
    assert not evaluate_forecast(rows([1.0, 2.0, 3.0, 4.0, None]), min_train=4)["available"]
    gap = rows([1.0, 2.0]) + (Observation("DE", "inflation", "2025-04", 4.0),)
    assert len(contiguous_tail(gap)) == 1
    assert summarize(gap, date(2025, 5, 1))["change"] is None
    broken = rows([1.0, 2.0]) + (Observation("DE", "inflation", "2025-03", 3.0, "b"),)
    assert len(contiguous_tail(broken)) == 1
    assert summarize(broken, date(2025, 4, 1))["change"] is None
    assert (
        len(
            contiguous_tail(
                tuple(
                    Observation(r.country, r.indicator, r.period, r.value, "demo")
                    for r in rows([1.0, 2.0, 3.0])
                )
            )
        )
        == 3
    )


def test_scenario_direction_and_basis_points_are_hand_calculated():
    result = exposure_scenario(110_000, 1.1, -10.0, 500_000, 100.0)
    assert result["base_invoice_eur"] == pytest.approx(100_000.0)
    assert result["stressed_invoice_eur"] == pytest.approx(111_111.111111)
    assert result["annual_interest_delta_eur"] == 5_000.0
    with pytest.raises(ValueError):
        exposure_scenario(100.0, 1.1, -100.0, 500.0, 100.0)


def test_missing_vs_absent_cells_and_flag_revisions_are_distinct():
    previous = rows([1.0, None])
    current = (Observation("DE", "inflation", "2025-01", 1.0, "p"),)
    result = revision_diff(previous, current)
    assert [row["kind"] for row in result] == ["status_revision", "outside_new_slice"]
