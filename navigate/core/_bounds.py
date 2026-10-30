# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Attribute bounds a value is held to, each end inclusive or exclusive.

The validators in `assign` resolve an attribute's bounds once and check a scalar
against them at assignment; the calculator nodes (`_Calculator`) and `Expression`
clamp to them each time they evaluate. Every message is a fragment the caller
prefixes with the owner of the value.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, overload

import numpy as np

if TYPE_CHECKING:
    from typing import Literal

    from navigate.util.types_ import FloatArray, FloatLike


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
    def is_empty(self) -> bool:
        """Whether no value lies within the bounds."""
        if self.lower == self.upper:
            return not (self.inclusive_lower and self.inclusive_upper)

        return self.lower > self.upper

    def check(self, value: float) -> None:
        """
        Reject a value outside the bounds.

        Parameters
        ----------
        value
            The value checked.

        Raises
        ------
        ValueError
            If the value is beyond an inclusive bound, or at or beyond an
            exclusive one.
        """
        if self.inclusive_lower and value < self.lower:
            raise ValueError(f"must be ≥ {self.lower}, but got {value}")

        if self.inclusive_upper and value > self.upper:
            raise ValueError(f"must be ≤ {self.upper}, but got {value}")

        self._check_exclusive(value)

    @overload
    def clamp(self, value: float) -> float: ...

    @overload
    def clamp(self, value: FloatArray) -> FloatArray: ...

    def clamp(self, value: FloatLike) -> FloatLike:
        """
        Clamp a value to the inclusive bounds, rejecting one at an exclusive bound.

        An exclusive bound is never clamped to, as the value it would clamp onto
        is the one the bound forbids.

        Parameters
        ----------
        value
            The value clamped, a float or an array of them.

        Returns
        -------
        FloatLike
            The clamped value, in the shape of ``value``.

        Raises
        ------
        ValueError
            If the value, or any entry of it, is at or beyond an exclusive bound;
            the message names the extreme entry, NaN ignored.
        """
        # inclusive bounds only clamp, so the check is skipped where both are
        if not (self.inclusive_lower and self.inclusive_upper):
            self._check_exclusive(value)

        return np.maximum(np.minimum(value, self.upper), self.lower)

    def tightened(self, offer: Bounds) -> Bounds:
        """
        Tighten the bounds by an offer, end by end.

        A strictly tighter end of the offer replaces the bound and its inclusive flag,
        an equal one is exclusive if either is, and a looser one changes nothing.

        Parameters
        ----------
        offer
            The bounds offered.

        Returns
        -------
        Bounds
            The tighter of the two at each end.
        """
        lower = max(self.lower, offer.lower)
        upper = min(self.upper, offer.upper)

        # an end includes its bound only where the bound passes both ends it meets
        inclusive_lower = self._passes_lower(lower) and offer._passes_lower(lower)
        inclusive_upper = self._passes_upper(upper) and offer._passes_upper(upper)

        return Bounds(lower, upper, inclusive_lower, inclusive_upper)

    def _passes_lower(self, value: float) -> bool:
        """Whether a value passes the lower bound."""
        return value > self.lower or (self.inclusive_lower and value == self.lower)

    def _passes_upper(self, value: float) -> bool:
        """Whether a value passes the upper bound."""
        return value < self.upper or (self.inclusive_upper and value == self.upper)

    def _check_exclusive(self, value: FloatLike) -> None:
        """Reject a value, or any entry of it, at or beyond an exclusive bound."""
        # most values are floats, which plain comparisons check far faster
        # than numpy's reductions
        if isinstance(value, float):
            breaks_lower = not self.inclusive_lower and value <= self.lower
            breaks_upper = not self.inclusive_upper and value >= self.upper
        else:
            breaks_lower = not self.inclusive_lower and np.any(value <= self.lower)
            breaks_upper = not self.inclusive_upper and np.any(value >= self.upper)

        if breaks_lower:
            raise ValueError(_exclusive_message(">", self.lower, np.nanmin(value)))

        if breaks_upper:
            raise ValueError(_exclusive_message("<", self.upper, np.nanmax(value)))


def _exclusive_message(relation: Literal[">", "<"], bound: float, value: float) -> str:
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
    if math.isinf(bound):
        return f"must be finite, but got {value}"

    return f"must be {relation} {bound}, but got {value}"
