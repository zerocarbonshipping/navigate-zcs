# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Vessel expectations calculated once at the start of each step, for other domains."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.vessel import Vessel


def calculate_fleet_expectations(
    vessels: dict[str, Vessel], fuels: dict[str, Fuel], emissions: dict[str, Emission]
) -> None:
    """
    Calculate the vessel expectations set once at the start of the step.

    For every converter and each fuel it burns, the effective lower heating value, net
    of slip, is set, and so are the TTW emissions of burning the fuel, split into the
    consumption and slip parts.

    Parameters
    ----------
    vessels
        All vessels in the simulation.
    fuels
        All fuels in the simulation.
    emissions
        All emissions in the simulation.
    """
    for vessel in vessels.values():
        for converter in vessel.power_system.get_converters():
            fuel_types = converter.get_fuel_types()

            for fuel in fuels.values():
                if fuel.fuel_type not in fuel_types:
                    continue

                _calculate_effective_lhv(vessel, converter, fuel)
                _calculate_ttw(vessel, converter, fuel, emissions)


def _calculate_effective_lhv(vessel: Vessel, converter: Converter, fuel: Fuel) -> None:
    """Set the fuel's heating value in the converter net of slip, in GJ/ton fuel-in."""
    slip = converter.slip_fraction[fuel.fuel_type].get()
    effective_lhv = (1.0 - slip) * fuel.lower_heating_value.get()

    vessel.expectation.set_effective_lhv(converter.name, fuel.name, effective_lhv)


def _calculate_ttw(
    vessel: Vessel, converter: Converter, fuel: Fuel, emissions: dict[str, Emission]
) -> None:
    """
    Set the fuel's TTW emissions in the converter, in ton emission/ton fuel-in.

    The consumption part holds the fuel-bound emissions of the burned fraction,
    1 - slip, and the converter's own emissions per ton fuel-in. The slip part is the
    slipped fraction itself, for the emission of the fuel's own type only.
    """
    expectation = vessel.expectation
    fuel_type = fuel.fuel_type
    slip = converter.slip_fraction[fuel_type].get()

    for emission_name, emission in emissions.items():
        fuel_ttw = fuel.ttw[emission_name].get()
        converter_ttw = converter.consumption_ttw[(fuel_type, emission_name)].get()

        ttw_consumption = (1.0 - slip) * fuel_ttw + converter_ttw
        ttw_slip = slip if emission.fuel_type == fuel_type else 0.0

        key = (converter.name, fuel.name, emission_name)
        expectation.set_ttw_consumption(*key, ttw_consumption)
        expectation.set_ttw_slip(*key, ttw_slip)
