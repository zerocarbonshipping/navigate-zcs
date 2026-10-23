# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Core type vocabulary: the calculator union and the setter input kinds.

Aliases here are built over core classes; `navigate/util/types_.py` holds
the dependency-free ones.

Each calculator-backed attribute has two kinds. The storage kind ('*Input')
is what 'assign_value' returns and the attribute holds; it carries 'Scalar'
rather than 'float', because the setter wraps a bare number through
'as_scalar' before storing. The argument kind ('*Argument') is what the
setter is handed, before that wrap: the same set with 'float' in place of
'Scalar'. The comment above each pair gives the 'type_' argument that spells
the set at the boundary. Every pair but the Curve table one carries
'Expression', as 'assign_value' accepts an expression wherever a setter takes
a number.
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

# the node classes 'CALCULATOR_TYPES' names
type Calculator = Curve | Forecast | Surface | Timetable | Variable

# setters passing type_ VARIABLE
type ScalarInput = Scalar | Variable | Expression
type ScalarArgument = float | Variable | Expression

# setters passing type_ FORECAST or VARIABLE
type ForecastInput = Scalar | Forecast | Variable | Expression
type ForecastArgument = float | Forecast | Variable | Expression

# setters passing type_ CURVE or VARIABLE
type CurveInput = Scalar | Curve | Variable | Expression
type CurveArgument = float | Curve | Variable | Expression

# setters passing type_ CURVE, FORECAST, or VARIABLE
type CurveForecastInput = Scalar | Curve | Forecast | Variable | Expression
type CurveForecastArgument = float | Curve | Forecast | Variable | Expression

# setters passing type_ CURVE, SURFACE, or VARIABLE
type SurfaceInput = Scalar | Curve | Surface | Variable | Expression
type SurfaceArgument = float | Curve | Surface | Variable | Expression

# setters passing type_ FORECAST, TIMETABLE, or VARIABLE
type TimetableInput = Scalar | Forecast | Timetable | Variable | Expression
type TimetableArgument = float | Forecast | Timetable | Variable | Expression

# setters passing no type_, which take no calculator and store the number
# unwrapped, so the one kind is both argument and storage
type NumberInput = float | Expression

# setters passing type_ CURVE with allow_expression False: they read the
# Curve as a table, so take neither a Variable nor an Expression
type CurveTableInput = Scalar | Curve
type CurveTableArgument = float | Curve
