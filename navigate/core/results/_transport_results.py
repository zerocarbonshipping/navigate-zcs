# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The results layer for the cargo carriers: the vessel and fleet results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.results.base_results import BaseResults, Unit, result

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class _TransportResults(BaseResults):
    """Transport work, speeds and freight rate of a vessel or a fleet."""

    cargo_miles: FloatArray = result(Unit.CARGO_MILES_PER_YEAR)

    # speeds
    reference_speed: FloatArray = result(Unit.KNOTS)
    minimum_speed: FloatArray = result(Unit.KNOTS)
    maximum_speed: FloatArray = result(Unit.KNOTS)
    actual_speed: FloatArray = result(Unit.KNOTS)
    optimal_speed: FloatArray = result(Unit.KNOTS)
    lowest_speed: FloatArray = result(Unit.KNOTS)
    highest_speed: FloatArray = result(Unit.KNOTS)

    instantaneous_freight_rate: FloatArray = result(Unit.USD_PER_CARGO_MILE)

    def _initialize_transport(self) -> None:
        self.cargo_miles = self._default_array()

        self.reference_speed = self._default_array(default=np.nan)
        self.minimum_speed = self._default_array(default=np.nan)
        self.maximum_speed = self._default_array(default=np.nan)
        self.actual_speed = self._default_array(default=np.nan)
        self.optimal_speed = self._default_array(default=np.nan)
        self.lowest_speed = self._default_array(default=np.nan)
        self.highest_speed = self._default_array(default=np.nan)

        self.instantaneous_freight_rate = self._default_array(default=np.nan)
