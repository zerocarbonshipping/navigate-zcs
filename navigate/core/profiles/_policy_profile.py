# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import numpy as np

from navigate.core.misc import EMPTY_FLOAT
from navigate.core.profiles._base_profile import _BaseProfile


class _PolicyProfile(_BaseProfile):
    def __init__(self):
        super().__init__()

        # offsetting
        self._offsetting_units: np.ndarray = EMPTY_FLOAT      # ton emissions/year, physically offset emissions
        self._offsetting_expenses: np.ndarray = EMPTY_FLOAT   # USD/year, total expenses from purchasing offsets

    def _initialize_policy_profile(self) -> None:
        self._offsetting_units = self._default_array()
        self._offsetting_expenses = self._default_array()

    def set_offsetting_units(self, idx: int, units: float) -> None:
        self._offsetting_units[idx] = units

    def set_offsetting_expenses(self, idx: int, expenses: float) -> None:
        self._offsetting_expenses[idx] = expenses

    def get_offsetting_units(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._offsetting_units[idx]

    def get_offsetting_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._offsetting_expenses[idx]
