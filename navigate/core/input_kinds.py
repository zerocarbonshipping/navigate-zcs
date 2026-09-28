# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Input kinds: the value sets the DSL setters on the node classes accept.

Each calculator-backed attribute has two kinds. The storage kind ('*Input')
is what 'assign_value' returns and the attribute holds; it carries 'Scalar'
rather than 'float', because the setter wraps a bare number through
'as_scalar' before storing. The argument kind ('*Argument') is what the
setter is handed, before that wrap: the same set with 'float' in place of
'Scalar'. The comment above each pair gives the 'type_' argument that spells
the set at the boundary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.core.expression import Expression
    from navigate.core.nodes.curve import Curve
    from navigate.core.nodes.forecast import Forecast
    from navigate.core.nodes.surface import Surface
    from navigate.core.nodes.timetable import Timetable
    from navigate.core.nodes.variable import Variable
    from navigate.core.scalar import Scalar

# 'Expression' is a member of every alias below: 'assign_value' accepts an
# expression wherever the setter accepts scalars or a calculator type, and
# every alias here spells such a setter.

# setters passing type_ VARIABLE
type ScalarInput = Scalar | Variable | Expression
type ScalarArgument = float | Variable | Expression

# setters passing type_ FORECAST or VARIABLE
type ForecastInput = Scalar | Forecast | Variable | Expression
type ForecastArgument = float | Forecast | Variable | Expression

# setters passing type_ CURVE or VARIABLE
type CurveInput = Scalar | Curve | Variable | Expression
type CurveArgument = float | Curve | Variable | Expression

# setters passing type_ CURVE, SURFACE, or VARIABLE
type SurfaceInput = Scalar | Curve | Surface | Variable | Expression
type SurfaceArgument = float | Curve | Surface | Variable | Expression

# setters passing type_ FORECAST, TIMETABLE, or VARIABLE
type TimetableInput = Scalar | Forecast | Timetable | Variable | Expression
type TimetableArgument = float | Forecast | Timetable | Variable | Expression

# the argument kind of plain-number setters, which pass no type_ and take no
# calculator; a setter that stores its number unwrapped holds it as this kind
# too
type NumberInput = float | Expression
