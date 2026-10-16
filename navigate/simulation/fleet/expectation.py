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
    vessels: dict[str, Vessel], emissions: dict[str, Emission]
) -> None:
    """
    Calculate the vessel expectations set once at the start of the step.

    For every vessel and usable fuel, each converter able to burn the fuel gets the
    fuel's effective lower heating value, net of slip, and the TTW emissions of
    burning it, split into the consumption and slip parts. The vessel gets the means
    of these over those converters, weighted by the fuel power each draws.

    Parameters
    ----------
    vessels
        All vessels in the simulation.
    emissions
        All emissions in the simulation.
    """
    for vessel in vessels.values():
        for fuel in vessel.usable_fuels.values():
            weights = _converter_weights(vessel, fuel)

            for converter, _ in weights:
                _calculate_effective_lhv(vessel, converter, fuel)
                _calculate_ttw(vessel, converter, fuel, emissions)

            _calculate_mean_effective_lhv(vessel, weights, fuel)
            _calculate_mean_ttw(vessel, weights, fuel, emissions)


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


def _converter_weights(vessel: Vessel, fuel: Fuel) -> list[tuple[Converter, float]]:
    """
    Weigh the vessel's converters that can burn a fuel by power over efficiency.

    The weight is the fuel power a converter draws at full load, and so estimates its
    share of the vessel's burn of the fuel. Converters that cannot burn the fuel are
    left out, so they carry no weight in a mean over the weights. A converter with zero
    efficiency delivers no energy and so burns no fuel; it weighs zero.

    Parameters
    ----------
    vessel
        Vessel whose converters are weighed.
    fuel
        Fuel being burned.

    Returns
    -------
    list[tuple[Converter, float]]
        Each converter able to burn the fuel with its weight, in MW.
    """
    converter_names = vessel.converters_per_fuel[fuel.name]

    weights: list[tuple[Converter, float]] = []
    for converter in vessel.power_system.get_converters():
        if converter.name not in converter_names:
            continue

        power = converter.power_capacity.get()
        efficiency = converter.efficiency.get()
        weight = power / efficiency if efficiency > 0.0 else 0.0

        weights.append((converter, weight))

    return weights


def _calculate_mean_effective_lhv(
    vessel: Vessel, weights: list[tuple[Converter, float]], fuel: Fuel
) -> None:
    """
    Set the vessel's mean effective LHV of the fuel, in GJ/ton fuel-in.

    A vessel without weight on any converter able to burn the fuel has no slip to net
    off, so it takes the fuel's LHV.
    """
    expectation = vessel.expectation
    lhv_sum = 0.0
    weight_total = 0.0

    for converter, weight in weights:
        effective_lhv = expectation.get_effective_lhv(converter.name, fuel.name)
        lhv_sum += weight * effective_lhv
        weight_total += weight

    lhv = fuel.lower_heating_value.get()
    mean_lhv = lhv_sum / weight_total if weight_total > 0.0 else lhv

    expectation.set_mean_effective_lhv(fuel.name, mean_lhv)


def _calculate_mean_ttw(
    vessel: Vessel,
    weights: list[tuple[Converter, float]],
    fuel: Fuel,
    emissions: dict[str, Emission],
) -> None:
    """
    Set the vessel's mean TTW emissions of the fuel, in ton emission/ton fuel-in.

    A vessel without weight on any converter able to burn the fuel emits nothing
    from it.
    """
    expectation = vessel.expectation

    for emission_name in emissions:
        key = (fuel.name, emission_name)
        consumption_sum = 0.0
        slip_sum = 0.0
        weight_total = 0.0

        for converter, weight in weights:
            consumption = expectation.get_ttw_consumption(converter.name, *key)
            slip = expectation.get_ttw_slip(converter.name, *key)

            consumption_sum += weight * consumption
            slip_sum += weight * slip
            weight_total += weight

        mean_consumption = consumption_sum / weight_total if weight_total > 0.0 else 0.0
        mean_slip = slip_sum / weight_total if weight_total > 0.0 else 0.0

        expectation.set_mean_ttw_consumption(*key, mean_consumption)
        expectation.set_mean_ttw_slip(*key, mean_slip)
