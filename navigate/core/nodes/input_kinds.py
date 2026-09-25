# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Input kinds: the value sets the DSL setters on the node classes accept.

Each alias is the set one 'assign_value' call admits, and the comment above
it gives the 'type_' argument that spells that set at the boundary. Every
alias but the last carries 'Scalar' rather than 'float', because the setter
wraps through 'as_scalar' before storing.
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

# setters passing type_ FORECAST or VARIABLE
type ForecastInput = Scalar | Forecast | Variable | Expression

# setters passing type_ CURVE or VARIABLE
type CurveInput = Scalar | Curve | Variable | Expression

# setters passing type_ CURVE, SURFACE, or VARIABLE
type SurfaceInput = Scalar | Curve | Surface | Variable | Expression

# setters passing type_ FORECAST, TIMETABLE, or VARIABLE
type TimetableInput = Scalar | Forecast | Timetable | Variable | Expression

# setters passing type_ VARIABLE, storing the number handed to them unwrapped
type NumberInput = float | Expression
