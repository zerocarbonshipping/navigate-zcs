# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Building and reading calculator tables.

Covers the input a table refuses, the rebasing of a dated Forecast to the
start date, the Timetable's current time, and the reverse lookup the speed
limits read from a propulsion Curve.
"""

from __future__ import annotations

import numpy as np
import pytest

from navigate.core.nodes.curve import Curve
from navigate.core.nodes.forecast import Forecast
from navigate.core.nodes.timetable import Timetable
from navigate.core.table_data import TableData

INF = np.inf
NAN = np.nan


# gives a Curve tables that cannot be interpolated (one row, repeated or
# decreasing x, infinite x, NaN y) and expects each to be refused.
# catches: a validation rule removed, e.g. a NaN y accepted, which then slips
# through every bound check later.
@pytest.mark.parametrize(
    ("rows", "match"),
    [
        ([[0.0, 1.0]], "must be at least of length 2"),
        ([[0.0, 1.0], [0.0, 2.0]], "'x' must be strictly increasing"),
        ([[1.0, 1.0], [0.0, 2.0]], "'x' must be strictly increasing"),
        # interpolating across an infinite x gives NaN
        ([[0.0, 1.0], [INF, 2.0]], "'x' must be finite"),
        # NaN passes every bound, as any comparison with it is false
        ([[0.0, 1.0], [1.0, NAN]], "'y' must not be NaN"),
    ],
    ids=["single_row", "repeated_x", "decreasing_x", "infinite_x", "nan_y"],
)
def test_curve_refuses_a_table(rows, match):
    with pytest.raises(ValueError, match=match):
        Curve("c").set_table(TableData(rows=rows))


# gives a Forecast a dated table and a start date 30 days earlier; the rows move
# to days 30 and 395, and day 130 interpolates by day count.
# catches: dates counted from the wrong reference, e.g. from the first row, so
# every value shifts by 30 days.
def test_dated_forecast_is_rebased_to_the_start_date():
    forecast = Forecast("f")
    forecast.set_table(TableData(rows=[["01-01-2026", 0.0], ["01-01-2027", 365.0]]))
    forecast.replace_reference_table(np.datetime64("2025-12-02"))

    # 2 Dec 2025 -> 1 Jan 2026 is 30 days, so the rows sit at day 30 and 395
    np.testing.assert_allclose(forecast.x, [30.0, 395.0])
    # day 130 is 100 days past the first row, rising one per day: 100
    assert forecast.get(130.0) == pytest.approx(100.0)


# reads a Forecast without an input before and after its value is calculated for
# day 40; before the first step it is NaN, then 20.
# catches: the cached value not updated by precalculate, so every step reads the
# value of the first step.
def test_forecast_get_without_input_reads_the_precalculated_step():
    forecast = Forecast("f")
    forecast.set_table(TableData(rows=[[0.0, 0.0], [100.0, 50.0]]))
    forecast.replace_reference_table(np.datetime64("2026-01-01"))

    # nothing is cached before the first step
    assert np.isnan(forecast.get())

    forecast.precalculate(40.0)
    # 40 days at 0.5 per day: 20
    assert forecast.get() == pytest.approx(20.0)


# reads a Timetable with only y given; before its clock is set it raises, after
# set_current_time(50) it uses day 50 as x.
# catches: the current time ignored, so the lookup always reads day 0 (5 instead
# of 55).
def test_timetable_reads_the_current_time():
    # header row holds y = [0, 1]; rows at x = 0 and x = 100, so z = x + 10 * y
    timetable = Timetable("t")
    timetable.set_table(
        TableData(rows=[[0.0, 1.0], [0.0, 0.0, 10.0], [100.0, 100.0, 110.0]])
    )
    timetable.replace_reference_table(np.datetime64("2026-01-01"))

    with pytest.raises(ValueError, match="requires a time, unset before the first"):
        timetable.get(y=0.5)

    timetable.set_current_time(50.0)
    # 50 + 10 * 0.5 = 55
    assert timetable.get(y=0.5) == pytest.approx(55.0)


# asks a Curve which x gives a y; a rising table answers by interpolation, a
# table that goes up then down answers None.
# catches: a reverse lookup on a non-monotonic curve returning an arbitrary x,
# which would give wrong speed limits.
@pytest.mark.parametrize(
    ("rows", "y", "expected"),
    [
        # 25 is halfway from 10 (x = 1) to 40 (x = 2): x = 1.5
        ([[0.0, 0.0], [1.0, 10.0], [2.0, 40.0]], 25.0, 1.5),
        # not strictly increasing, so no unique x answers a y
        ([[0.0, 0.0], [1.0, 10.0], [2.0, 5.0]], 7.0, None),
    ],
    ids=["monotonic", "non_monotonic"],
)
def test_curve_reverse_lookup(rows, y, expected):
    curve = Curve("c")
    curve.set_table(TableData(rows=rows))
    curve.build_table()

    assert curve.reverse_lookup(y) == (
        expected if expected is None else pytest.approx(expected)
    )
