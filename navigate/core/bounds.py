# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Attribute bounds a value is held to, each end inclusive or exclusive.

Used by the calculator nodes (`_Calculator`) and by `Expression`, the two
kinds of value an attribute evaluates rather than checks once at assignment.
The message fragments are shared by `assign`, the calculators and
`Expression`, each prefixing its own owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from typing import Literal

    from navigate.util.types_ import FloatLike


@dataclass(frozen=True)
class Bounds:
    """
    Lower and upper bound of a value, each inclusive or exclusive.

    Parameters
    ----------
    lower
        Lower bound.
    upper
        Upper bound.
    inclusive_lower
        Whether the value may equal the lower bound.
    inclusive_upper
        Whether the value may equal the upper bound.
    """

    lower: float = -np.inf
    upper: float = np.inf
    inclusive_lower: bool = True
    inclusive_upper: bool = True

    @property
    def exclusive(self) -> bool:
        """Whether either bound excludes the value it equals."""
        return not (self.inclusive_lower and self.inclusive_upper)

    def exclusive_violation(self, value: FloatLike) -> str | None:
        """
        Spell how a value breaks an exclusive bound, if it does.

        An inclusive bound passes every value, as the caller clamps to it.

        Parameters
        ----------
        value
            Value before clamping, a float or an array of them.

        Returns
        -------
        str or None
            Message fragment naming the extreme entry breaking the bound, NaN
            ignored; None where the value is within the bounds.
        """
        # most values are floats, which plain comparisons check far faster
        # than numpy's reductions
        if isinstance(value, float):
            breaks_lower = not self.inclusive_lower and value <= self.lower
            breaks_upper = not self.inclusive_upper and value >= self.upper
        else:
            breaks_lower = not self.inclusive_lower and np.any(value <= self.lower)
            breaks_upper = not self.inclusive_upper and np.any(value >= self.upper)

        if breaks_lower:
            return exclusive_bound_message(">", self.lower, np.nanmin(value))

        if breaks_upper:
            return exclusive_bound_message("<", self.upper, np.nanmax(value))

        return None


def exclusive_bound_message(
    relation: Literal[">", "<"], bound: float, value: FloatLike
) -> str:
    """
    Spell the rejection of a value at or beyond an exclusive bound.

    An exclusive bound at infinity rejects only infinity itself, so its
    rejection asks for a finite value rather than one below infinity.

    Parameters
    ----------
    relation
        Comparison the value must satisfy against the bound.
    bound
        The exclusive bound.
    value
        The rejected value.

    Returns
    -------
    str
        Message fragment the caller prefixes with the owner of the value.
    """
    if np.isinf(bound):
        return f"must be finite, but got {value}"

    return f"must be {relation} {bound}, but got {value}"
