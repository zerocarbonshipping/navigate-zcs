# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The profile layer that sums vessels into a fleet or the whole model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from navigate.core.enum_ import FuelTypeID
from navigate.core.profiles._base_profile import accumulate, result
from navigate.core.profiles._fuel_consumer_profile import _FuelConsumerProfile

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class _VesselAggregateProfile(_FuelConsumerProfile):
    """Installed power, fleet turnover and expenses summed over a set of vessels."""

    # power
    installed_power: dict[FuelTypeID, FloatArray] = result("MW")
    newbuild_power: dict[FuelTypeID, FloatArray] = result("MW/year", per_step=True)
    scrapped_power: dict[FuelTypeID, FloatArray] = result("MW/year", per_step=True)
    fuel_converted_power: dict[tuple[FuelTypeID, FuelTypeID], FloatArray] = result(
        "MW/year", per_step=True
    )

    # expenses
    vessel_expenses: FloatArray = result("USD/year")
    technology_expenses: FloatArray = result("USD/year")
    fuel_conversion_expenses: FloatArray = result("USD/year")
    vessel_related_expenses: FloatArray = result("USD/year")
    expenses: FloatArray = result("USD/year")
    vessel_tied_capital: FloatArray = result("USD")

    # power-weighted average age, kept as numerator and denominator so that it
    # aggregates
    weighted_age_numerator: dict[FuelTypeID, FloatArray] = field(init=False)
    weighted_age_denominator: dict[FuelTypeID, FloatArray] = field(init=False)
    weighted_average_age: dict[FuelTypeID, FloatArray] = result("years")

    fuel_type_capacity: dict[FuelTypeID, FloatArray] = result("GJ/year")

    def _initialize_vessel_aggregate(self) -> None:
        # the global profile sums its fleets' baselines; a fleet computes its own
        self.baseline_energy = self._default_array()

        self.installed_power = self._default_dict(FuelTypeID)
        self.newbuild_power = self._default_dict(FuelTypeID)
        self.scrapped_power = self._default_dict(FuelTypeID)
        self.fuel_converted_power = self._default_tuple_dict(FuelTypeID, FuelTypeID)

        self.vessel_expenses = self._default_array()
        self.technology_expenses = self._default_array()
        self.fuel_conversion_expenses = self._default_array()
        self.vessel_tied_capital = self._default_array()

        self.weighted_age_numerator = self._default_dict(FuelTypeID)
        self.weighted_age_denominator = self._default_dict(FuelTypeID)

        self.fuel_type_capacity = self._default_dict(FuelTypeID)

    def add_vessel_aggregate_profile(self, profile: _VesselAggregateProfile) -> None:
        """
        Add another vessel aggregate profile's values into this one.

        Parameters
        ----------
        profile
            Vessel aggregate profile from another node.
        """
        accumulate(self.baseline_energy, profile.baseline_energy)
        accumulate(self.installed_power, profile.installed_power)
        accumulate(self.newbuild_power, profile.newbuild_power)
        accumulate(self.scrapped_power, profile.scrapped_power)
        accumulate(self.fuel_converted_power, profile.fuel_converted_power)
        accumulate(self.vessel_expenses, profile.vessel_expenses)
        accumulate(self.technology_expenses, profile.technology_expenses)
        accumulate(self.fuel_conversion_expenses, profile.fuel_conversion_expenses)
        accumulate(self.vessel_tied_capital, profile.vessel_tied_capital)
        accumulate(self.weighted_age_numerator, profile.weighted_age_numerator)
        accumulate(self.weighted_age_denominator, profile.weighted_age_denominator)
        accumulate(self.fuel_type_capacity, profile.fuel_type_capacity)
