# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Regulation node, read by the bunkering LP and policy layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.expectations._expectation import _Expectation

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from navigate.core.nodes.route import Route
    from navigate.core.nodes.vessel import Vessel


class RegulationExpectation(_Expectation):
    """The inputs a regulation gives the bunkering LP and the results it gets back."""

    def __init__(
        self,
        length: int,
        emission_names: Collection[str],
        routes: Mapping[str, Route],
        vessels: Mapping[str, Vessel],
    ) -> None:
        super().__init__(length)

        port_names = [port.name for route in routes.values() for port in route.ports]
        legs = [leg for route in routes.values() for leg in route.get_leg_keys()]

        vessel_ports: list[tuple[str, str]] = []
        vessel_fuel_emissions: list[tuple[str, str, str]] = []
        vessel_converter_fuels: list[tuple[str, str, str]] = []
        vessel_converter_fuel_emissions: list[tuple[str, str, str, str]] = []

        for vessel_name, vessel in vessels.items():
            for port in vessel.route.distinct_ports:
                vessel_ports.append((vessel_name, port.name))

            for fuel_name in vessel.usable_fuels:
                for emission_name in emission_names:
                    key = (vessel_name, fuel_name, emission_name)
                    vessel_fuel_emissions.append(key)

            for converter_name, burned in vessel.fuels_per_converter.items():
                for fuel_name in burned:
                    fuel_key = (vessel_name, converter_name, fuel_name)
                    vessel_converter_fuels.append(fuel_key)

                    for emission_name in emission_names:
                        key = (*fuel_key, emission_name)
                        vessel_converter_fuel_emissions.append(key)

        self.global_warming_potential = self._values(emission_names)

        self.wtt = self._paths(vessel_fuel_emissions)
        self.ttw_consumption = self._paths(vessel_converter_fuel_emissions)
        self.ttw_slip = self._paths(vessel_converter_fuel_emissions)

        # the threshold adjustment rewrites the spend coefficients at its LP's step
        self.emission_coefficient = self._paths(vessel_converter_fuels)
        self.spend_coefficient = self._paths(vessel_converter_fuels)

        self.shore_power_emission_coefficient = self._paths(port_names)
        self.shore_power_spend_coefficient = self._paths(vessel_ports)

        # the belief is NaN until its first update: zero is a real shadow price
        self.flexibility_cost = self._path()
        self.belief_flexibility_cost = self._path(default=np.nan)
        self.vessel_net_flexibility_units = self._paths(vessels)
        self.remedial_cost = self._path()

        # a leg is keyed by the names of its departure and arrival port
        self.port_fraction = self._paths(port_names)
        self.leg_fraction = self._paths(legs)

        # per vessel; threshold in the regulation's unit, kg emission/GJ under INTENSITY
        self.vessel_threshold = self._paths(vessels)
        self.vessel_capacity = self._paths(vessels)
        self.vessel_measure = self._paths(vessels)

        # the threshold adjustment rewrites the allowance at its LP's step
        self.vessel_allowance = self._paths(vessels)

        # results of the bunkering LP of each time step
        self.vessel_emissions = self._paths(vessels)
        self.vessel_energy = self._paths(vessels)
        self.vessel_remedial_units = self._paths(vessels)
        self.pooled_remedial_units = self._path()
        self.pooled_shadow_price = self._path()

        # NaN where the threshold adjustment does not apply
        self.adjusted_vessel_threshold = self._paths(vessels, default=np.nan)
        self.adjusted_shared_threshold = self._path(default=np.nan)

    def reset_expected_bunkering(self) -> None:
        """Clear the flexibility market outcomes of the expected bunkering LPs."""
        vessel_names = self.vessel_net_flexibility_units.keys()

        self.flexibility_cost = self._path()
        self.vessel_net_flexibility_units = self._paths(vessel_names)
