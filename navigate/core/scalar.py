# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np


class Scalar:
    def __init__(self, value=None):

        self._value = value

    def __repr__(self):
        return f"Scalar({str(self._value)})"

    def get(self, x=None, y=None) -> float | np.ndarray:
        """
        Return the number associated to a Value.

        Parameters
        ----------
        x : float or np.ndarray or str
            Dummy input variable for calculations with getters of 1 input.
        y : float or np.ndarray or str
            Dummy input variable for calculations with getters of 2 input.

        Returns
        -------
        float
            Assigned scalar value.
        """

        # no need to check against y
        # as y can never be passed
        # without x and will always
        # have the same size
        if (x is not None) and isinstance(x, np.ndarray):

            return np.full_like(x, self._value)

        else:

            return self._value

    @staticmethod
    def is_forecast():
        return False
