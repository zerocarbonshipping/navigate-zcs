# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Levy node, read by the bunkering LP and the policy layer."""

from __future__ import annotations

from itertools import product
from typing import TYPE_CHECKING

from navigate.core.expectations._expectation import _Expectation

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from navigate.core.nodes.vessel import Vessel


class LevyExpectation(_Expectation):
    """A levy's level and its cost per ton of fuel or GJ of shore power to a vessel."""

    def __init__(
        self,
        length: int,
        emission_names: Collection[str],
        fuel_names: Collection[str],
        port_names: Collection[str],
        vessels: Mapping[str, Vessel],
    ) -> None:
        super().__init__(length)

        port_fuel_emissions = list(product(port_names, fuel_names, emission_names))
        vessel_fuel_emissions: list[tuple[str, str, str]] = []
        vessel_port_fuels: list[tuple[str, str, str]] = []
        vessel_ports: list[tuple[str, str]] = []

        for vessel_name, vessel in vessels.items():
            for fuel_name in vessel.usable_fuels:
                for emission_name in emission_names:
                    key = (vessel_name, fuel_name, emission_name)
                    vessel_fuel_emissions.append(key)

                for port in vessel.route.distinct_ports:
                    key = (vessel_name, port.name, fuel_name)
                    vessel_port_fuels.append(key)

            for port in vessel.route.distinct_ports:
                vessel_ports.append((vessel_name, port.name))

        self.global_warming_potential = self._values(emission_names)  # tCO2e/t emission

        self.wtt = self._paths(port_fuel_emissions)  # tCO2e/t
        self.ttw_consumption = self._paths(vessel_fuel_emissions)  # tCO2e/t
        self.ttw_slip = self._paths(vessel_fuel_emissions)  # tCO2e/t

        self.level = self._path()  # currency/tCO2e
        self.cost = self._paths(vessel_port_fuels)  # currency/t
        self.shore_power_cost = self._paths(vessel_ports)  # currency/GJ
