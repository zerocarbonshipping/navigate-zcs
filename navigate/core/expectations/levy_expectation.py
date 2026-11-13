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
    """The level a levy charges and its cost per ton of each fuel a vessel bunkers."""

    def __init__(
        self,
        length: int,
        emission_names: Collection[str],
        fuel_names: Collection[str],
        port_names: Collection[str],
        vessels: Mapping[str, Vessel],
    ) -> None:
        super().__init__(length)

        vessel_fuel_emissions: list[tuple[str, str, str]] = []
        vessel_port_fuels: list[tuple[str, str, str]] = []

        for vessel_name, vessel in vessels.items():
            for fuel_name in vessel.usable_fuels:
                for emission_name in emission_names:
                    key = (vessel_name, fuel_name, emission_name)
                    vessel_fuel_emissions.append(key)

                for port in vessel.route.distinct_ports:
                    key = (vessel_name, port.name, fuel_name)
                    vessel_port_fuels.append(key)

        self.global_warming_potential = self._values(emission_names)

        self.wtt = self._paths(product(port_names, fuel_names, emission_names))
        self.ttw_consumption = self._paths(vessel_fuel_emissions)
        self.ttw_slip = self._paths(vessel_fuel_emissions)

        self.level = self._path()
        self.cost = self._paths(vessel_port_fuels)
