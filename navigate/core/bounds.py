# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Attribute bounds a value is held to, each end inclusive or exclusive.

Used by the calculator nodes (`_Calculator`) and by `Expression`, the two
kinds of value an attribute evaluates rather than checks once at assignment;
`assign` rejects a scalar at an exclusive bound in the same words.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
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

    def check_exclusive(self, value: FloatLike, owner: str) -> None:
        """
        Raise where a value reaches an exclusive bound.

        An inclusive bound passes every value, as the caller clamps to it.

        Parameters
        ----------
        value
            Value before clamping, a float or an array of them.
        owner
            Text leading the error message, naming the node or expression the
            value belongs to.

        Raises
        ------
        ValueError
            If the value, or any entry of it, is at or beyond an exclusive bound;
            the message reports the extreme entry.
        """
        if not self.inclusive_lower and np.any(value <= self.lower):
            raise ValueError(
                f"{owner}: {exclusive_bound_message('>', self.lower, np.min(value))}"
            )

        if not self.inclusive_upper and np.any(value >= self.upper):
            raise ValueError(
                f"{owner}: {exclusive_bound_message('<', self.upper, np.max(value))}"
            )


def exclusive_bound_message(relation: str, bound: float, value: FloatLike) -> str:
    """
    Spell the rejection of a value at or beyond an exclusive bound.

    An exclusive bound at infinity rejects only infinity itself, so its
    rejection asks for a finite value rather than one below infinity.

    Parameters
    ----------
    relation
        Comparison the value must satisfy against the bound, '>' or '<'.
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
