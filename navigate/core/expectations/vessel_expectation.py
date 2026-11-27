# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Vessel node, read by the fleet, the bunkering LP and policy."""

from __future__ import annotations

from functools import partial
from itertools import product
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import (
    PORT_ENERGY_DEMANDS,
    EnergyDemandID,
    ExpenseID,
    FuelTypeID,
)
from navigate.core.expectations._expectation import _Expectation

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from navigate.core.nodes.route import Route


class VesselExpectation(_Expectation):
    """Voyage, energy, bunkering and investment paths of one vessel of the type."""

    def __init__(
        self,
        length: int,
        route: Route,
        fuel_names: Collection[str],
        usable_fuel_names: Collection[str],
        fuels_per_converter: Mapping[str, Collection[str]],
        emission_names: Collection[str],
    ) -> None:
        super().__init__(length)

        conditions = len(route.get_conditions())
        legs = len(route.get_legs())
        port_calls = len(route.ports)

        # paths per energy demand type and per sailing condition, leg or port call
        per_condition = partial(self._path_lists, EnergyDemandID, conditions)
        per_leg = partial(self._path_lists, EnergyDemandID, legs)
        per_port_call = partial(self._path_lists, PORT_ENERGY_DEMANDS, port_calls)

        # NaN until the first step sets them
        unset = partial(self._values, default=np.nan)

        port_names = [port.name for port in route.distinct_ports]
        port_fuels = list(product(port_names, fuel_names))
        port_fuel_types = list(product(port_names, FuelTypeID))
        usable_fuel_emissions = list(product(usable_fuel_names, emission_names))

        # each converter with each fuel it burns, and for the TTW each emission too
        converter_fuels: list[tuple[str, str]] = []
        converter_fuel_emissions: list[tuple[str, str, str]] = []

        for converter_name, burned in fuels_per_converter.items():
            for fuel_name in burned:
                converter_fuels.append((converter_name, fuel_name))

                for emission_name in emission_names:
                    key = (converter_name, fuel_name, emission_name)
                    converter_fuel_emissions.append(key)

        self.voyages = self._path()  # voyages/year

        self.cargo_miles = self._path()  # cargo-miles/year
        self.cargo_miles_leg = self._path_list(legs)  # cargo-miles/year
        self.cargo_miles_leg_nominal = self._path_list(legs)  # cargo-miles/year

        self.speed_mean = np.nan  # knots
        self.speed_anchor_reference = np.nan  # knots
        self.speed_anchor_optimal = np.nan  # knots
        self.speeds_condition = self._path_list(conditions)  # knots

        self.time_sea_condition = self._path_list(conditions)  # days/year
        self.time_port = self._path_list(port_calls)  # days/year

        # converter output, at sea per condition and per leg, in port per port call
        self.raw_energy_sea_condition = per_condition()  # GJ/year
        self.raw_energy_port = per_port_call()  # GJ/year

        self.operational_energy_sea_condition = per_condition()  # GJ/year
        self.operational_energy_sea_leg = per_leg()  # GJ/year
        self.operational_energy_port = per_port_call()  # GJ/year

        self.operational_saving_fraction_sea = self._values(EnergyDemandID)  # -
        self.operational_saving_fraction_port = self._values(PORT_ENERGY_DEMANDS)  # -

        self.energy_sea_condition = per_condition()  # GJ/year
        self.energy_sea_leg = per_leg()  # GJ/year
        self.energy_port = per_port_call()  # GJ/year

        # energy conservation, at sea per leg, in port per port call
        self.energy_conservation_pi_sea = per_leg()  # currency/GJ
        self.energy_conservation_pi_port = per_port_call()  # currency/GJ
        self.energy_conservation_rhs_sea = per_leg()  # GJ/year
        self.energy_conservation_rhs_port = per_port_call()  # GJ/year

        # NaN until the first update: zero is a real shadow price, not a missing one
        self.belief_pi_sea_technology = per_leg(default=np.nan)  # currency/GJ
        self.belief_pi_port_technology = per_port_call(default=np.nan)  # currency/GJ
        self.belief_pi_sea_speed = per_leg(default=np.nan)  # currency/GJ
        self.belief_pi_port_speed = per_port_call(default=np.nan)  # currency/GJ
        self.belief_pi_shore_power_limit_technology = self._path_list(
            port_calls, default=np.nan
        )  # currency/GJ

        self.effective_lhv = unset(converter_fuels)  # GJ/t
        self.ttw_consumption = unset(converter_fuel_emissions)  # t/t
        self.ttw_slip = unset(converter_fuel_emissions)  # t/t

        # the vessel's means over its converters
        self.mean_effective_lhv = unset(usable_fuel_names)  # GJ/t
        self.mean_ttw_consumption = unset(usable_fuel_emissions)  # t/t
        self.mean_ttw_slip = unset(usable_fuel_emissions)  # t/t

        self.bunker_mass_expected = self._paths(port_fuels)  # t/year
        self.bunker_mass_existing = self._values(port_fuels)  # t/year
        self.spend_energy = self._values(fuels_per_converter)  # GJ/year of fuel

        # potential fuel-type demand at each port of the route
        self.potential_fuel_type_demand = self._paths(port_fuel_types)  # GJ/year

        # fair-share fuel supply, and the existing bunkering's allocation of it
        self.fair_share_fuel_existing = self._values(port_fuels)  # -
        self.fair_share_fuel_expected = self._paths(port_fuels)  # -
        self.allocation_fuel_existing = self._values(port_fuels)  # t/year

        # what the expected bunkering supplies, and its fuel and policy expenses
        self.total_energy = self._path()  # GJ/year of fuel and shore power
        self.expenses = self._paths(ExpenseID)  # currency/year

        self.shore_power_potential_port = self._path_list(port_calls)  # GJ/year
        self.shore_power_limit_port = self._path_list(port_calls)  # GJ/year
        self.shore_power_limit_pi_port = self._path_list(port_calls)  # currency/GJ

        self.asset_charter_npv = self._path()  # currency
        self.capex_npv = self._path()  # currency
        self.asset_charter_rate = self._path()  # currency/year
        self.freight_rate = self._path()  # currency/cargo-mile
        self.technology_charter_rate = self._path()  # currency/year

        # per time step, the capital a vessel ordered then ties up each year in service
        self.tied_capital = [self._path() for _ in range(length)]  # currency

    def reset_expected_bunkering(self) -> None:
        """Clear the bunker masses, energy and expenses of the expected bunkering."""
        self.bunker_mass_expected = self._paths(self.bunker_mass_expected)

        self.total_energy = self._path()
        self.expenses = self._paths(ExpenseID)

    def reset_bunker_mass_existing(self) -> None:
        """Zero the bunker masses of the existing bunkering."""
        self.bunker_mass_existing = self._values(self.bunker_mass_existing)

    def reset_spend_energy(self) -> None:
        """Zero the energy each converter spent."""
        self.spend_energy = self._values(self.spend_energy)

    def reset_allocation_fuel_existing(self) -> None:
        """Zero the existing bunkering's allocation of the fair-share fuel supply."""
        self.allocation_fuel_existing = self._values(self.allocation_fuel_existing)
