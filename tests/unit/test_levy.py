# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for Levy's per-time-step threshold consistency check."""

from __future__ import annotations

import numpy as np
import pytest

from navigate.core.nodes.forecast import Forecast
from navigate.core.nodes.levy import Levy
from navigate.core.table_data import TableData

# a short four-step timeline; TIMES is what '.get()' takes, DATES the matching
# calendar dates. The two arrays are only paired by index here, as
# 'check_dynamic_consistency' does, not derived from one another
TIMES = np.array([0.0, 365.0, 730.0, 1095.0])
DATES = np.array(
    ["2024-01-01", "2025-01-01", "2026-01-01", "2027-01-01"], dtype="datetime64[D]"
)


def _forecast(name: str, y: list[float]) -> Forecast:
    """Build a Forecast over TIMES with the given y-values, one per step."""
    forecast = Forecast(name)
    rows = [[x, yi] for x, yi in zip(TIMES, y, strict=True)]
    forecast.set_table(TableData(rows=rows))
    forecast.replace_reference_table(np.datetime64("2024-01-01"))
    return forecast


def _make_levy(lower, upper=None, *, scheme=None, active=True):
    """Build a Levy with the given thresholds, scheme and active flag."""
    levy = Levy("levy")
    levy.set_lower_threshold(lower)
    if upper is not None:
        levy.set_upper_threshold(upper)
    if scheme is not None:
        levy.set_scheme(scheme)
    if not active:
        levy.set_active("FALSE")
    return levy


@pytest.mark.parametrize(
    ("make_lower", "make_upper", "expected_date"),
    [
        # lower overtakes upper between day 365 and day 730: at day 730 lower
        # is 80 while upper is only 70, the first step where upper < lower
        (
            lambda: _forecast("lower", [10.0, 20.0, 80.0, 90.0]),
            lambda: _forecast("upper", [50.0, 60.0, 70.0, 95.0]),
            "2026-01-01",
        ),
        # transient cross: upper (70) dips below lower (80) only at day 365,
        # and both sides recover by day 730 (lower 20 <= upper 60); the first
        # (and only) offending step is still reported
        (
            lambda: _forecast("lower_transient", [10.0, 80.0, 20.0, 30.0]),
            lambda: _forecast("upper_transient", [50.0, 70.0, 60.0, 70.0]),
            "2025-01-01",
        ),
        # constant scalars: upper (30) is below lower (50) at every step, so
        # the first step, day 0, is already inconsistent
        (lambda: 50.0, lambda: 30.0, "2024-01-01"),
    ],
)
def test_check_dynamic_consistency_raises_when_upper_falls_below_lower(
    make_lower, make_upper, expected_date
):
    # explicit PENALTY: the check must not depend on Levy's default scheme
    levy = _make_levy(make_lower(), make_upper(), scheme="PENALTY")

    with pytest.raises(
        ValueError, match=rf"'UpperThreshold'.*'LowerThreshold'.*{expected_date}"
    ):
        levy.check_dynamic_consistency(TIMES, DATES)


@pytest.mark.parametrize(
    ("make_lower", "make_upper", "scheme", "active"),
    [
        # thresholds touch at day 365 (20 == 20, equality allowed) but upper
        # stays >= lower at every other step: touching is not a cross
        (
            lambda: _forecast("lower_touching", [10.0, 20.0, 30.0, 40.0]),
            lambda: _forecast("upper_touching", [50.0, 20.0, 60.0, 70.0]),
            "PENALTY",
            True,
        ),
        # no UpperThreshold assigned: nothing to compare the lower one
        # against, whatever the scheme or active flag
        (lambda: 100.0, None, None, True),
        # thresholds cross, but the levy is inactive: an event that
        # activates it later is checked from that step on, over the
        # remaining timeline, not before
        (
            lambda: _forecast("lower_inactive", [10.0, 20.0, 80.0, 90.0]),
            lambda: _forecast("upper_inactive", [50.0, 60.0, 70.0, 95.0]),
            None,
            False,
        ),
        # thresholds cross, but under a SUBSIDY scheme the coefficient never
        # reads upper_threshold, so a crossing is not a contradiction
        (
            lambda: _forecast("lower_subsidy", [10.0, 20.0, 80.0, 90.0]),
            lambda: _forecast("upper_subsidy", [50.0, 60.0, 70.0, 95.0]),
            "SUBSIDY",
            True,
        ),
    ],
)
def test_check_dynamic_consistency_passes_when_the_cross_does_not_apply(
    make_lower, make_upper, scheme, active
):
    upper = make_upper() if make_upper is not None else None
    levy = _make_levy(make_lower(), upper, scheme=scheme, active=active)

    levy.check_dynamic_consistency(TIMES, DATES)  # does not raise
