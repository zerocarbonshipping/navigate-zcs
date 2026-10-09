# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The kinds of value a numeric attribute accepts, and the ones it refuses.

A numeric setter takes a float, a calculator node of the types it lists, or an
expression, and its consumer reads each through the same `get(x, y)`. Every
kind below is built to answer the same hand value, so a kind read differently
from the others shows up as a wrong number.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

from navigate.core.expression import Expression
from navigate.core.nodes.curve import Curve
from navigate.core.nodes.forecast import Forecast
from navigate.core.nodes.levy import Levy
from navigate.core.nodes.surface import Surface
from navigate.core.nodes.variable import Variable
from navigate.core.nodes.vessel import Vessel
from navigate.core.table_data import TableData

if TYPE_CHECKING:
    from collections.abc import Callable

# every propulsion load below answers 8 MW at 10 knots and utilization 0.5
SPEED = 10.0
UTILIZATION = 0.5
LOAD = 8.0


def _variable(value: float) -> Variable:
    variable = Variable("v")
    variable.set_value(value)
    return variable


def _curve(rows: list[list[float | str]]) -> Curve:
    curve = Curve("c")
    curve.set_table(TableData(rows=rows))
    curve.build_table()
    return curve


def _surface() -> Surface:
    # z rises 16 over x 0 -> 20 and is flat in y: z(10, 0.5) = 8
    surface = Surface("s")
    surface.set_table(TableData(rows=[[0.0, 1.0], [0.0, 0.0, 0.0], [20.0, 16.0, 16.0]]))
    surface.build_table()
    return surface


def _expression(
    text: str, reference: Variable | Curve | None
) -> Callable[[Vessel], Expression]:
    """Return a builder resolving the expression the way the parser does."""

    def build(vessel: Vessel) -> Expression:
        expression = Expression(text)
        vessel.set_propulsion_load(expression)
        expression.resolve(vessel, lambda reference_string, location: reference)
        return expression

    return build


def _assign(value):
    """Return a builder assigning a ready-made value to the vessel."""

    def build(vessel: Vessel):
        vessel.set_propulsion_load(value)
        return value

    return build


# sets a vessel's PropulsionLoad as a float, Variable, Curve, Surface and two
# expressions, all built to give 8 MW at the same speed and utilization.
# catches: one kind read with the wrong inputs, e.g. a Surface given
# (utilization, speed), so it reads a different number than the rest.
@pytest.mark.parametrize(
    "build",
    [
        _assign(LOAD),
        _assign(_variable(LOAD)),
        # 16 over 0 -> 20 knots: 16 * 10 / 20 = 8
        _assign(_curve([[0.0, 0.0], [20.0, 16.0]])),
        _assign(_surface()),
        # 2 * 4 = 8
        _expression('2 * Variable("v")', _variable(4.0)),
        # the expression passes the speed on: 32 * 10 / 20 / 2 = 8
        _expression('Curve("c") / 2', _curve([[0.0, 0.0], [20.0, 32.0]])),
    ],
    ids=["float", "variable", "curve", "surface", "expression", "expression_of_curve"],
)
def test_every_accepted_kind_reads_the_same_load(build):
    vessel = Vessel("v")
    build(vessel)

    assert vessel.propulsion_load.get(SPEED, UTILIZATION) == pytest.approx(LOAD)


# sets a Levy level to a Forecast calculated for day 50 and reads the level
# without input; it returns that step's value, 8.
# catches: a Forecast assigned to an attribute read at the wrong time, e.g. at
# day 0, giving 0 instead of 8.
def test_forecast_reads_the_value_of_the_current_step():
    # 16 over days 0 -> 100: 16 * 50 / 100 = 8 on day 50
    forecast = Forecast("f")
    forecast.set_table(TableData(rows=[[0.0, 0.0], [100.0, 16.0]]))
    forecast.replace_reference_table(np.datetime64("2026-01-01"))
    forecast.precalculate(50.0)

    levy = Levy("l")
    levy.set_level(forecast)

    assert levy.level.get() == pytest.approx(LOAD)


# gives a setter a node type it does not accept (a Forecast for a vessel load, a
# Curve for a levy level, a stray word) and expects an error naming the types.
# catches: the type check removed, so a Curve on a levy level is read without an
# x and fails later with a confusing error.
@pytest.mark.parametrize(
    ("setter", "value", "match"),
    [
        (
            Vessel.set_propulsion_load,
            Forecast("f"),
            "nodes of type Curve, Surface or Variable, but got Forecast",
        ),
        (
            Levy.set_level,
            Curve("c"),
            "nodes of type Forecast or Variable, but got Curve",
        ),
        # an unrecognized token such as a misplaced ID reaches the setter as text
        (Vessel.set_propulsion_load, "FLAT", "but got FLAT"),
    ],
    ids=["vessel_forecast", "levy_curve", "token"],
)
def test_a_kind_outside_the_setter_types_is_refused(setter, value, match):
    owner = Vessel("v") if setter is Vessel.set_propulsion_load else Levy("l")

    with pytest.raises(ValueError, match=match):
        setter(owner, value)


# puts an expression that reads a Curve on a Levy level, which only takes
# Forecast and Variable, and expects the reference to be refused.
# catches: expressions used as a back door around the setter's type check.
def test_an_expression_referencing_a_refused_type_is_refused():
    # the Levy level takes Forecast and Variable, so neither may an expression
    # assigned to it read a Curve
    levy = Levy("l")
    expression = Expression('Curve("c")')
    levy.set_level(expression)

    with pytest.raises(ValueError, match="references unacceptable type Curve"):
        expression.resolve(levy, lambda reference_string, location: Curve("c"))
