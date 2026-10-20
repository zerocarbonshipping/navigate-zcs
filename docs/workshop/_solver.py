# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0
"""A run-time workaround for a solver hang in this version of Navigate.

Navigate starts each year's bunkering look-ahead with HiGHS's interior-point
method, with no iteration or time limit. On a few combinations of Session 1's
levers (about 1 in 20 pairs) that method gets within 2e-8 of the optimum,
just short of its 1e-8 stopping rule, and then alternates between two points
for ever, so the notebook cell never finishes.

`guard_interior_point()` caps that method and, when it stops without an
optimum, solves the same problem again with simplex. A solve that finishes
today is untouched, so results that already solve do not change. Nothing in
Navigate's package is edited: the cap is applied to HiGHS in this Python
session only.
"""
import math

import highspy
from highspy import HighsModelStatus

# A healthy look-ahead solve takes a few dozen interior-point iterations.
IPM_ITERATIONS = 10_000
IPM_SECONDS = 30.0

_original_run = highspy.Highs.run


def _option(highs, name):
    value = highs.getOptionValue(name)
    return value[1] if isinstance(value, tuple) else value


def _run_with_fallback(highs):
    if _option(highs, "solver") != "ipm":
        return _original_run(highs)
    highs.setOptionValue("ipm_iteration_limit", IPM_ITERATIONS)
    # time_limit counts from the creation of this Highs object, not from run()
    highs.setOptionValue("time_limit", highs.getRunTime() + IPM_SECONDS)
    try:
        status = _original_run(highs)
    finally:
        highs.setOptionValue("ipm_iteration_limit", 2**31 - 1)
        highs.setOptionValue("time_limit", math.inf)
    if highs.getModelStatus() != HighsModelStatus.kOptimal:
        guard_interior_point.fallbacks += 1
        highs.setOptionValue("solver", "simplex")
        highs.setOptionValue("run_crossover", "off")
        status = _original_run(highs)
    return status


def guard_interior_point():
    """Cap HiGHS's interior-point method and fall back to simplex. Safe to call twice."""
    if highspy.Highs.run is not _run_with_fallback:
        highspy.Highs.run = _run_with_fallback


guard_interior_point.fallbacks = 0
