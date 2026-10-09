# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The transform every calculator applies to its raw value, and its bounds.

output = clamp(Multiplier * (value + Addition)) to the tighter of the public
bounds (LowerBound/UpperBound) and the internal bounds pushed on by the
attribute the calculator is assigned to. An exclusive internal bound is never
clamped to: a value reaching it raises.
"""

from __future__ import annotations

import numpy as np
import pytest

from navigate.core.nodes.curve import Curve
from navigate.core.nodes.variable import Variable
from navigate.core.table_data import TableData


def _variable(value: float) -> Variable:
    variable = Variable("v")
    variable.set_value(value)
    return variable


def _curve() -> Curve:
    # y = 10 * x on 0 <= x <= 2
    curve = Curve("c")
    curve.set_table(TableData(rows=[[0.0, 0.0], [1.0, 10.0], [2.0, 20.0]]))
    curve.build_table()
    return curve


# sets Multiplier 3 and Addition -1 on a Variable of 4, then adds public and
# internal bounds; the result is 3 * (4 - 1) clamped to the tighter bound.
# catches: Addition applied after the multiplier (11 instead of 9), or the
# looser of two bounds used (8 instead of 6).
@pytest.mark.parametrize(
    ("public", "internal", "expected"),
    [
        # 3 * (4 + (-1)) = 9; adding after multiplying would give 3 * 4 - 1 = 11
        ((-np.inf, np.inf), (-np.inf, np.inf), 9.0),
        # the public upper bound clamps 9 down to 8
        ((-np.inf, 8.0), (-np.inf, np.inf), 8.0),
        # the tighter internal upper bound 6 wins over the public 8
        ((-np.inf, 8.0), (-np.inf, 6.0), 6.0),
        # the tighter public lower bound 12 wins over the internal 10
        ((12.0, np.inf), (10.0, np.inf), 12.0),
    ],
    ids=["unbounded", "public_upper", "internal_tighter", "public_tighter"],
)
def test_addition_applies_inside_the_multiplier_then_the_tighter_bound(
    public, internal, expected
):
    variable = _variable(4.0)
    variable.set_multiplier(3.0)
    variable.set_addition(-1.0)
    variable.set_lower_bound(public[0])
    variable.set_upper_bound(public[1])
    variable.set_internal_bounds(*internal)

    assert variable.get() == pytest.approx(expected)


# sets Multiplier and Addition on a Curve and looks up an array of x values;
# each entry gets the same 2 * (value + 1).
# catches: the transform skipped for array lookups, so a vector read returns
# the raw table values [5, 15] instead of [12, 32].
def test_transform_applies_to_a_table_lookup_entrywise():
    curve = _curve()
    curve.set_multiplier(2.0)
    curve.set_addition(1.0)

    # table [5, 15] at x = [0.5, 1.5]: 2 * (5 + 1) = 12, 2 * (15 + 1) = 32
    np.testing.assert_allclose(curve.get(np.array([0.5, 1.5])), [12.0, 32.0])


# gives a Variable and a Curve an exclusive lower bound of 0 and reads a value
# of exactly 0; the error names the node.
# catches: an exclusive bound treated as inclusive, so a value of 0 passes where
# it must be strictly above 0 (e.g. a divisor).
@pytest.mark.parametrize(
    ("make_node", "args", "owner"),
    [
        (lambda: _variable(0.0), (), r'Variable\("v"\)'),
        # y = 10 * x, so only the entry at x = 0 sits on the bound
        (_curve, (np.array([1.0, 0.0, 2.0]),), r'Curve\("c"\)'),
    ],
    ids=["scalar", "array_entry"],
)
def test_a_value_on_an_exclusive_bound_raises(make_node, args, owner):
    node = make_node()
    node.set_internal_bounds(0.0, np.inf, inclusive_lower=False)

    with pytest.raises(ValueError, match=rf"{owner}: must be > 0\.0, but got 0\.0"):
        node.get(*args)


# sets an exclusive internal lower bound of 0 and a public lower bound of 1 on a
# Variable of -1; the public bound wins and the value clamps to 1.
# catches: the exclusive check run against the wrong bound, so -1 raises an
# error instead of clamping to 1.
def test_a_public_bound_inside_an_exclusive_bound_clamps():
    # the public bound 1 is the one applied, so -1 clamps up to 1 instead of
    # raising against the exclusive 0
    variable = _variable(-1.0)
    variable.set_internal_bounds(0.0, np.inf, inclusive_lower=False)
    variable.set_lower_bound(1.0)

    assert variable.get() == pytest.approx(1.0)
