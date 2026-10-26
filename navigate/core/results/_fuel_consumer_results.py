# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The results layer for the fuel consumers: the vessel, fleet and global results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from navigate.core.enum_ import PORT_ENERGY_DEMANDS, EnergyDemandID, FuelTypeID
from navigate.core.results.base_results import BaseResults, accumulate, result

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.util.types_ import FloatArray, FloatLike


@dataclass(eq=False, repr=False)
class _FuelConsumerResults(BaseResults):
    """Energy demand, fuel burnt, emissions and fuel expenses of a fuel consumer."""

    # raw energy demand
    raw_energy_sea: dict[EnergyDemandID, FloatArray] = result("GJ/year")
    raw_energy_port: dict[EnergyDemandID, FloatArray] = result("GJ/year")
    raw_energy: FloatArray = result("GJ/year")

    # operational energy demand: after operational savings, before technology
    operational_energy_sea: dict[EnergyDemandID, FloatArray] = result("GJ/year")
    operational_energy_port: dict[EnergyDemandID, FloatArray] = result("GJ/year")
    operational_energy: FloatArray = result("GJ/year")

    # energy demand
    energy_sea: dict[EnergyDemandID, FloatArray] = result("GJ/year")
    energy_port: dict[EnergyDemandID, FloatArray] = result("GJ/year")
    energy: FloatArray = result("GJ/year")

    # counterfactual raw energy: the year-0 raw energy intensity times the transport
    # work performed
    baseline_energy: FloatArray = result("GJ/year")

    # savings: 1 less the energy over the raw energy, per energy demand, and the
    # energy intensity savings against the baseline
    saving: dict[EnergyDemandID, FloatArray] = result("-")
    speed_energy_intensity_saving: FloatArray = result("-")
    operational_energy_intensity_saving: FloatArray = result("-")
    technology_energy_intensity_saving: FloatArray = result("-")
    energy_intensity_saving: FloatArray = result("-")

    # fuel consumed: the mass is written, the energy computed from it
    consumed_mass: dict[str, FloatArray] = field(init=False)
    consumed_energy: dict[str, FloatArray] = result("GJ/year")
    fuel_type_energy: dict[FuelTypeID, FloatArray] = result("GJ/year")
    total_consumed_energy: FloatArray = result("GJ/year")

    # fuel burnt in converters, per vessel fuel type and fuel; the energy is keyed by
    # (vessel fuel type, fuel)
    converter_mass: dict[FuelTypeID, dict[str, FloatArray]] = field(init=False)
    converter_energy: dict[tuple[FuelTypeID, str], FloatArray] = result("GJ/year")
    pilot_fuel_share: dict[FuelTypeID, FloatArray] = result("-")

    # expenses
    fuel_expenses: dict[str, FloatArray] = result("USD/year")
    levy_expenses: dict[str, FloatArray] = result("USD/year")
    fuel_related_expenses: dict[str, FloatArray] = result("USD/year")
    remedial_expenses: FloatArray = result("USD/year")
    flexibility_expenses: FloatArray = result("USD/year")
    surplus_revenue: FloatArray = result("USD/year")
    regulation_expenses: FloatArray = result("USD/year")
    total_fuel_expenses: FloatArray = result("USD/year")
    total_fuel_related_expenses: FloatArray = result("USD/year")

    # CO2-equivalents under the policy's own global warming potential; a levy unit is
    # the levy collected over its level
    remedial_units: dict[str, FloatArray] = result("tCO2e/year")
    levy_units: dict[str, FloatArray] = result("tCO2e/year")

    # emissions, keyed by (fuel, emission): the tons of each emission are written,
    # the CO2-equivalents computed from them; the intensities are the totals per
    # total energy consumed
    wtt: dict[tuple[str, str], FloatArray] = field(init=False)
    ttw: dict[tuple[str, str], FloatArray] = field(init=False)

    equivalent_wtt: dict[tuple[str, str], FloatArray] = result("tCO2e/year")
    intensity_total_equivalent_wtt: FloatArray = result("gCO2e/MJ")

    equivalent_ttw: dict[tuple[str, str], FloatArray] = result("tCO2e/year")
    intensity_total_equivalent_ttw: FloatArray = result("gCO2e/MJ")

    # the total includes the shore power emissions, which have no
    # (fuel, emission) attribution
    equivalent_wtw: dict[tuple[str, str], FloatArray] = result("tCO2e/year")
    total_equivalent_wtw: FloatArray = result("tCO2e/year")
    intensity_total_equivalent_wtw: FloatArray = result("gCO2e/MJ")

    # shore power: a WTW-lumped emission per gas, unweighted and with no fuel
    # attribution
    shore_power_energy: FloatArray = result("GJ/year")
    shore_power_expenses: FloatArray = result("USD/year")
    shore_power_emission: dict[str, FloatArray] = result("t/year")

    def _initialize_fuel_consumer(
        self, regulation_names: Sequence[str], levy_names: Sequence[str]
    ) -> None:
        fuels = self.context.fuels
        emissions = self.context.emissions

        self.raw_energy_sea = self._default_dict(EnergyDemandID)
        self.raw_energy_port = self._default_dict(PORT_ENERGY_DEMANDS)

        self.operational_energy_sea = self._default_dict(EnergyDemandID)
        self.operational_energy_port = self._default_dict(PORT_ENERGY_DEMANDS)

        self.energy_sea = self._default_dict(EnergyDemandID)
        self.energy_port = self._default_dict(PORT_ENERGY_DEMANDS)

        self.consumed_mass = self._default_dict(fuels)
        self.converter_mass = self._default_nested_dict(FuelTypeID, fuels)

        self.fuel_expenses = self._default_dict(fuels)
        self.levy_expenses = self._default_dict(fuels)
        self.remedial_expenses = self._default_array()
        self.flexibility_expenses = self._default_array()
        self.surplus_revenue = self._default_array()

        self.remedial_units = self._default_dict(regulation_names)
        self.levy_units = self._default_dict(levy_names)

        self.wtt = self._default_tuple_dict(fuels, emissions)
        self.ttw = self._default_tuple_dict(fuels, emissions)

        self.shore_power_energy = self._default_array()
        self.shore_power_expenses = self._default_array()
        self.shore_power_emission = self._default_dict(emissions)

    def add_fuel_consumer_results(
        self, results: _FuelConsumerResults, multiplier: FloatLike = 1.0
    ) -> None:
        """
        Add another fuel consumer's results into this one.

        Parameters
        ----------
        results
            Consumer results from another node.
        multiplier
            Multiplier on the other results; a scalar, or a weight per time step.
        """
        accumulate(self.raw_energy_sea, results.raw_energy_sea, multiplier)
        accumulate(self.raw_energy_port, results.raw_energy_port, multiplier)

        accumulate(
            self.operational_energy_sea, results.operational_energy_sea, multiplier
        )
        accumulate(
            self.operational_energy_port, results.operational_energy_port, multiplier
        )

        accumulate(self.energy_sea, results.energy_sea, multiplier)
        accumulate(self.energy_port, results.energy_port, multiplier)

        accumulate(self.consumed_mass, results.consumed_mass, multiplier)
        accumulate(self.converter_mass, results.converter_mass, multiplier)

        accumulate(self.fuel_expenses, results.fuel_expenses, multiplier)
        accumulate(self.levy_expenses, results.levy_expenses, multiplier)
        accumulate(self.remedial_expenses, results.remedial_expenses, multiplier)
        accumulate(self.flexibility_expenses, results.flexibility_expenses, multiplier)
        accumulate(self.surplus_revenue, results.surplus_revenue, multiplier)

        accumulate(self.remedial_units, results.remedial_units, multiplier)
        accumulate(self.levy_units, results.levy_units, multiplier)

        accumulate(self.wtt, results.wtt, multiplier)
        accumulate(self.ttw, results.ttw, multiplier)

        accumulate(self.shore_power_energy, results.shore_power_energy, multiplier)
        accumulate(self.shore_power_expenses, results.shore_power_expenses, multiplier)
        accumulate(self.shore_power_emission, results.shore_power_emission, multiplier)
