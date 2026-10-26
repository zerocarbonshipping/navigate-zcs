# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The results layer for the cargo carriers: the vessel and fleet results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.results.base_results import BaseResults, result

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class _TransportResults(BaseResults):
    """Transport work, speeds and freight rate of a vessel or a fleet."""

    cargo_miles: FloatArray = result("cargo-miles/year")

    # speeds
    reference_speed: FloatArray = result("knots")
    minimum_speed: FloatArray = result("knots")
    maximum_speed: FloatArray = result("knots")
    actual_speed: FloatArray = result("knots")
    optimal_speed: FloatArray = result("knots")
    lowest_speed: FloatArray = result("knots")
    highest_speed: FloatArray = result("knots")

    instantaneous_freight_rate: FloatArray = result("USD/cargo-mile")

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
