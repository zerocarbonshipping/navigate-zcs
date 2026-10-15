# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Vessel expectations calculated once at the start of each step, for other domains."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.vessel import Vessel


def calculate_fleet_expectations(
    vessels: dict[str, Vessel], fuels: dict[str, Fuel]
) -> None:
    """
    Calculate the vessel expectations set once at the start of the step.

    Effective lower heating values, net of slip, are set for every converter and each
    fuel it burns.

    Parameters
    ----------
    vessels
        All vessels in the simulation.
    fuels
        All fuels in the simulation.
    """
    for vessel in vessels.values():
        _calculate_effective_lhv(vessel, fuels)


def _calculate_effective_lhv(vessel: Vessel, fuels: dict[str, Fuel]) -> None:
    """Set each converter-fuel pair's heating value net of slip, in GJ/ton fuel-in."""
    expectation = vessel.expectation

    for converter in vessel.power_system.get_converters():
        fuel_types = converter.get_fuel_types()

        for fuel in fuels.values():
            if fuel.fuel_type not in fuel_types:
                continue

            slip = converter.slip_fraction[fuel.fuel_type].get()
            effective_lhv = (1.0 - slip) * fuel.lower_heating_value.get()
            expectation.set_effective_lhv(converter.name, fuel.name, effective_lhv)
