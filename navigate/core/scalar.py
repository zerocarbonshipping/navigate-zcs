# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Scalar, the float wrapper that setters store in place of a calculator node."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

import numpy as np

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray, FloatLike


class Scalar:
    """
    A float wrapped in the two-argument getter every calculator node answers.

    Parameters
    ----------
    value
        The number the scalar answers with.
    """

    def __init__(self, value: float) -> None:

        self._value: float = value

    def __repr__(self) -> str:
        return f"Scalar({self._value!s})"

    @overload
    def get(self, x: FloatArray, y: FloatLike | None = None) -> FloatArray: ...

    @overload
    def get(self, x: float | None = None, y: FloatLike | None = None) -> float: ...

    def get(self, x: FloatLike | None = None, y: FloatLike | None = None) -> FloatLike:
        """
        Return the wrapped number, broadcast to the shape of an array input.

        Parameters
        ----------
        x
            Dummy first input matching the calculator getters; an array sets
            the output shape.
        y
            Dummy second input matching the calculator getters.

        Returns
        -------
        float or FloatArray
            The wrapped number, or an array of it in the shape of ``x``.
        """
        # broadcasting is what keeps a Scalar substitutable for a calculator
        # node, whose getter answers an array input with an array
        if isinstance(x, np.ndarray):
            return np.full_like(x, self._value)

        return self._value
