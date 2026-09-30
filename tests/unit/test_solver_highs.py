# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the column upper bound of the HiGHS solver shim."""

from __future__ import annotations

import pytest

from navigate.bunker import solver_highs

# the LPs below have vertex optima; HiGHS returns them to within its default
# primal feasibility tolerance of 1e-7
SOLUTION_TOLERANCE = 1e-6


def _build_capped_sum():
    """
    Build max 2x + y subject to x + y <= 10, x, y >= 0.

    With x capped at u (0 <= u <= 10) the optimum is x = u, y = 10 - u: every
    unit moved from y to x gains 1, so x rises to its cap and y takes the rest
    of the shared budget.
    """
    model = solver_highs.Model()
    x = model.addVar()
    y = model.addVar()
    x.Obj = -2.0
    y.Obj = -1.0
    model.addConstr(x + y <= 10.0)
    return model, x, y


@pytest.mark.parametrize(
    ("upper_bounds", "expected_solutions"),
    [
        ([3.0], [(3.0, 7.0)]),
        ([3.0, 6.0], [(3.0, 7.0), (6.0, 4.0)]),
        ([6.0, 3.0], [(6.0, 4.0), (3.0, 7.0)]),
        ([3.0, 0.0], [(3.0, 7.0), (0.0, 10.0)]),
    ],
)
def test_upper_bound_caps_variable_across_solves(upper_bounds, expected_solutions):
    model, x, y = _build_capped_sum()

    for upper_bound, (expected_x, expected_y) in zip(
        upper_bounds, expected_solutions, strict=True
    ):
        x.UB = upper_bound
        model.optimize()

        solution = (x.X, y.X)

        assert model.Status == solver_highs.OPTIMAL
        assert solution == pytest.approx(
            (expected_x, expected_y), abs=SOLUTION_TOLERANCE
        )


def test_optimum_below_upper_bound_is_not_raised_to_it():
    # min x + 2y subject to x + y >= 2: x is the cheaper way to cover the
    # demand, so x = 2 and y = 0; the cap of 5 does not bind, and a lower bound
    # raised to the cap would force x = 5 instead
    model = solver_highs.Model()
    x = model.addVar()
    y = model.addVar()
    x.Obj = 1.0
    y.Obj = 2.0
    model.addConstr(x + y >= 2.0)

    x.UB = 5.0
    model.optimize()
    solution = (x.X, y.X)

    assert model.Status == solver_highs.OPTIMAL
    assert solution == pytest.approx((2.0, 0.0), abs=SOLUTION_TOLERANCE)


def test_upper_bound_change_does_not_mark_model_grown():
    model, x, _ = _build_capped_sum()
    model.optimize()

    x.UB = 3.0

    assert not model._model_grew


def test_removed_variable_stays_at_zero_despite_pending_upper_bound():
    # min y subject to x + y >= 5: any x the bounds allow lowers y, so y = 5
    # only if the removal pins x to zero; x capped at 3 would give y = 2
    model = solver_highs.Model()
    x = model.addVar()
    y = model.addVar()
    y.Obj = 1.0
    model.addConstr(x + y >= 5.0)

    x.UB = 3.0
    model.remove(x)
    model.optimize()
    solution = (x.X, y.X)

    assert solution == pytest.approx((0.0, 5.0), abs=SOLUTION_TOLERANCE)
