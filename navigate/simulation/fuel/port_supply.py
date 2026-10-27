# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Bunker price, supply and WTT of each fuel at each port."""

from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING, NamedTuple

import numpy as np

from navigate.util import TOLERANCE, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray, FloatLike

logger = logging.getLogger(__name__)


class _ImportTotals(NamedTuple):
    """Supply of each fuel at each port and its supply-weighted cost and WTT."""

    supplies: dict[str, dict[str, FloatArray]]
    costs: dict[str, dict[str, FloatArray]]
    wtts: dict[tuple[str, str], dict[str, FloatArray]]


def calculate_fuel_import_to_ports(
    ports: dict[str, Port],
    producers: dict[str, Producer],
    emissions: dict[str, Emission],
    fuels: dict[str, Fuel],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Set bunker price, supply and WTT per port from liquid-market and producer imports.

    Parameters
    ----------
    ports
        All ports in the simulation.
    producers
        All producers in the simulation.
    emissions
        All emissions in the simulation.
    fuels
        All fuels in the simulation.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    liquid_fuels: dict[str, Fuel] = {}
    production_fuels: dict[str, Fuel] = {}

    for fuel_name, fuel in fuels.items():
        if fuel.liquid_market:
            liquid_fuels[fuel_name] = fuel
        else:
            production_fuels[fuel_name] = fuel

    _calculate_import_from_liquid_market(ports, emissions, liquid_fuels, timeline, idx)
    _calculate_import_from_producers(
        ports, producers, emissions, production_fuels, timeline, idx
    )


def _calculate_import_from_liquid_market(
    ports: dict[str, Port],
    emissions: dict[str, Emission],
    fuels: dict[str, Fuel],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Set bunker price, supply and WTT at each port for fuels drawn from a liquid market.

    A liquid-market fuel is never short of supply, so a port offers as much as it may
    bunker: its bunkering limit, unlimited where none is declared, and only a finite
    limit turns on the fair-share constraint.

    Parameters
    ----------
    ports
        All ports in the simulation.
    emissions
        All emissions in the simulation.
    fuels
        All fuels in the simulation which belong to a liquid market.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    forward = np.s_[idx:]
    zeros = np.zeros_like(timeline[forward])
    zero_wtts = dict.fromkeys(emissions, zeros)

    for port in ports.values():
        expectation = port.expectation

        for fuel_name in fuels:
            allowed = port.bunkering_allowed[fuel_name]
            limit = expectation.get_bunkering_limit(fuel_name, forward)

            bunker_price = _calculate_bunker_price(port, fuel_name, zeros, forward)
            bunker_wtts = _calculate_bunker_wtts(port, fuel_name, zero_wtts, forward)
            bunker_supply = limit if allowed else zeros

            _set_bunker_terms(port, fuel_name, bunker_price, bunker_wtts, idx)
            expectation.set_bunker_supply(idx, fuel_name, bunker_supply)

            if allowed:
                _record_bunker_terms(port, fuel_name, bunker_price, bunker_wtts, idx)

            if allowed and np.isfinite(bunker_supply[0]):
                port.results.bunker_supply_mass[fuel_name][idx] = bunker_supply[0]


def _calculate_import_from_producers(
    ports: dict[str, Port],
    producers: dict[str, Producer],
    emissions: dict[str, Emission],
    fuels: dict[str, Fuel],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Set supply-weighted bunker price, supply and WTT at each port for producer fuels.

    Parameters
    ----------
    ports
        All ports in the simulation.
    producers
        All producers in the simulation.
    emissions
        All emissions in the simulation.
    fuels
        All fuels in the simulation which do not belong to a liquid market.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    forward = np.s_[idx:]

    supplies, costs, wtt_totals = _calculate_import_totals(
        ports, producers, emissions, fuels, timeline, idx
    )

    # price and WTT are averaged before the supply is aligned with the bunkering
    # limits; the alignment reroutes supply equally from each plant, so keeps them
    for fuel_name in fuels:
        for port_name, port in ports.items():
            supply = supplies[fuel_name][port_name]
            supplied = supply[0] > 0.0

            cost = divide_nonzero(costs[fuel_name][port_name], supply)
            wtts: dict[str, FloatArray] = {}

            for emission_name in emissions:
                total = wtt_totals[fuel_name, emission_name][port_name]
                wtts[emission_name] = divide_nonzero(total, supply)

            bunker_price = _calculate_bunker_price(port, fuel_name, cost, forward)
            bunker_wtts = _calculate_bunker_wtts(port, fuel_name, wtts, forward)

            _set_bunker_terms(port, fuel_name, bunker_price, bunker_wtts, idx)

            if supplied:
                _record_bunker_terms(port, fuel_name, bunker_price, bunker_wtts, idx)

    for fuel_name in fuels:
        imports = supplies[fuel_name]
        aligned = _align_with_bunkering_limits(imports, ports, fuel_name, forward)

        # a port without a bunker price supplies nothing, so the optimizer cannot use
        # the fuel at zero cost
        for port_name, port in ports.items():
            bunker_price = port.expectation.get_bunker_price(fuel_name, forward)
            bunker_supply = np.where(bunker_price > TOLERANCE, aligned[port_name], 0.0)

            port.expectation.set_bunker_supply(idx, fuel_name, bunker_supply)
            port.results.bunker_supply_mass[fuel_name][idx] = bunker_supply[0]


def _calculate_import_totals(
    ports: dict[str, Port],
    producers: dict[str, Producer],
    emissions: dict[str, Emission],
    fuels: dict[str, Fuel],
    timeline: FloatArray,
    idx: int,
) -> _ImportTotals:
    """
    Sum the supply each port imports from every plant, and its weighted cost and WTT.

    A fuel disallowed in some ports has its export rerouted to the others by equal
    fractions.

    Parameters
    ----------
    ports
        All ports in the simulation.
    producers
        All producers in the simulation.
    emissions
        All emissions in the simulation.
    fuels
        All fuels in the simulation which do not belong to a liquid market.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.

    Returns
    -------
    _ImportTotals
        The supply of each fuel at each port, with its supply-weighted cost and WTT.
    """
    forward = np.s_[idx:]
    times = timeline[forward]

    shares = _calculate_allowed_port_shares(ports)

    supplies = {}
    costs = {}
    wtts = {}

    for fuel_name in fuels:
        supplies[fuel_name] = _allocate_per_port(ports, times)
        costs[fuel_name] = _allocate_per_port(ports, times)

        for emission_name in emissions:
            wtts[fuel_name, emission_name] = _allocate_per_port(ports, times)

    for producer in producers.values():
        exports = producer.expectation.get_export_distribution(forward)

        for plant in producer.plants:
            fuel_name = plant.fuel.name

            if shares[fuel_name] == 0.0:
                logger.debug(
                    'Fuel("%s") is not allowed for bunkering in any port. Any existing '
                    "production from %s is inaccessible during bunkering.",
                    fuel_name,
                    plant,
                )

                continue

            production = producer.expectation.get_expected_production(
                plant.name, forward
            )

            for port_name, export in exports.items():
                if not ports[port_name].bunkering_allowed[fuel_name]:
                    continue

                rerouted = export / shares[fuel_name]
                supply = production * rerouted
                delivered_cost = _calculate_delivered_cost(plant, port_name, forward)
                delivered_wtts = _calculate_delivered_wtts(plant, port_name, forward)

                supplies[fuel_name][port_name] += supply
                costs[fuel_name][port_name] += supply * delivered_cost

                for emission_name, delivered_wtt in delivered_wtts.items():
                    wtts[fuel_name, emission_name][port_name] += supply * delivered_wtt

    return _ImportTotals(supplies, costs, wtts)


def _allocate_per_port(
    ports: dict[str, Port], times: FloatArray
) -> dict[str, FloatArray]:
    """Allocate a zero value at each of the times for each port."""
    return {port_name: np.zeros_like(times) for port_name in ports}


def _calculate_delivered_cost(
    plant: Plant, port_name: str, forward: slice
) -> FloatLike:
    """
    Calculate the expected cost of a plant's fuel delivered to a port.

    Parameters
    ----------
    plant
        The plant.
    port_name
        Name of the port.
    forward
        Slice of the timeline from the current time step onwards.

    Returns
    -------
    FloatLike
        Production plus delivery cost, in USD/t.
    """
    expectation = plant.expectation
    production_cost = expectation.get_expected_production_cost(forward)
    delivery_cost = expectation.get_levelized_delivery_cost(port_name, forward)
    return production_cost + delivery_cost


def _calculate_delivered_wtts(
    plant: Plant, port_name: str, forward: slice
) -> dict[str, FloatLike]:
    """
    Calculate the expected WTT per emission of a plant's fuel delivered to a port.

    Parameters
    ----------
    plant
        The plant.
    port_name
        Name of the port.
    forward
        Slice of the timeline from the current time step onwards.

    Returns
    -------
    dict[str, FloatLike]
        Production plus delivery WTT per emission in the simulation, in t/t.
    """
    expectation = plant.expectation
    wtts: dict[str, FloatLike] = {}

    for emission_name in expectation.get_emissions():
        production_wtt = expectation.get_expected_production_wtt(emission_name, forward)
        delivery_wtt = expectation.get_delivery_wtt(port_name, emission_name, forward)
        wtts[emission_name] = production_wtt + delivery_wtt

    return wtts


def _set_bunker_terms(
    port: Port,
    fuel_name: str,
    bunker_price: FloatArray,
    bunker_wtts: dict[str, FloatArray],
    idx: int,
) -> None:
    """
    Set the port's expected bunker price and WTT of a fuel from the time step on.

    Parameters
    ----------
    port
        The port.
    fuel_name
        Name of the fuel.
    bunker_price
        Bunker price, in USD/t.
    bunker_wtts
        Bunker WTT per emission, in t/t.
    idx
        Current time-step index.
    """
    expectation = port.expectation
    expectation.set_bunker_price(idx, fuel_name, bunker_price)

    for key, value in bunker_wtts.items():
        expectation.set_bunker_wtt(idx, fuel_name, key, value)


def _record_bunker_terms(
    port: Port,
    fuel_name: str,
    bunker_price: FloatArray,
    bunker_wtts: dict[str, FloatArray],
    idx: int,
) -> None:
    """
    Write the bunker price and WTT of a fuel at the time step to the port's results.

    Parameters
    ----------
    port
        The port.
    fuel_name
        Name of the fuel.
    bunker_price
        Bunker price from the time step on, in USD/t.
    bunker_wtts
        Bunker WTT per emission from the time step on, in t/t.
    idx
        Current time-step index.
    """
    results = port.results
    results.bunker_price[fuel_name][idx] = bunker_price[0]

    for key, value in bunker_wtts.items():
        results.bunker_wtt[fuel_name, key][idx] = value[0]


def _calculate_bunker_price(
    port: Port, fuel_name: str, fallback: FloatArray, forward: slice
) -> FloatArray:
    """
    Calculate the bunker price, the port's overwrite where set, plus handling cost.

    Parameters
    ----------
    port
        The port.
    fuel_name
        Name of the fuel.
    fallback
        Price where the port sets no overwrite, in USD/t.
    forward
        Slice of the timeline from the current time step onwards.

    Returns
    -------
    FloatArray
        Bunker price, in USD/t.
    """
    overwrite = port.expectation.get_bunker_price_overwrite(fuel_name, forward)
    overwritten = port.bunker_price_overwrites[fuel_name] is not None
    price = overwrite if overwritten else fallback

    # the overwrite getter returns a view into stored state, so the handling cost is
    # added out of place rather than onto it
    return price + port.expectation.get_handling_cost(fuel_name, forward)


def _calculate_bunker_wtts(
    port: Port, fuel_name: str, fallbacks: dict[str, FloatArray], forward: slice
) -> dict[str, FloatArray]:
    """
    Calculate the bunker WTT per emission, the port's overwrite where set.

    Parameters
    ----------
    port
        The port.
    fuel_name
        Name of the fuel.
    fallbacks
        WTT per emission where the port sets no overwrite, in t/t.
    forward
        Slice of the timeline from the current time step onwards.

    Returns
    -------
    dict[str, FloatArray]
        Bunker WTT per emission, in t/t.
    """
    wtts = {}

    for emission_name, fallback in fallbacks.items():
        key = (fuel_name, emission_name)
        overwrite = port.expectation.get_bunker_wtt_overwrite(*key, forward)
        overwritten = port.bunker_wtt_overwrites[key] is not None
        wtts[emission_name] = overwrite if overwritten else fallback

    return wtts


def _calculate_allowed_port_shares(ports: dict[str, Port]) -> dict[str, float]:
    """
    Calculate the share of ports allowing each fuel to be bunkered.

    Parameters
    ----------
    ports
        All ports in the simulation.

    Returns
    -------
    dict[str, float]
        Share of ports allowing each fuel.
    """
    counts: Counter[str] = Counter()

    for port in ports.values():
        for fuel_name, allowed in port.bunkering_allowed.items():
            counts[fuel_name] += allowed

    return {fuel_name: count / len(ports) for fuel_name, count in counts.items()}


def _align_with_bunkering_limits(
    imports: dict[str, FloatArray],
    ports: dict[str, Port],
    fuel_name: str,
    forward: slice,
) -> dict[str, FloatArray]:
    """
    Align one fuel's import to each port with the port's bunkering limit.

    A port over its limit is trimmed to it, and the freed surplus fills the deficit of
    the ports under their limit, in proportion to it. What surplus the deficits
    cannot absorb is split equally across the ports without a limit, and dropped
    where there are none. A port without import neither gives up nor receives fuel,
    so the aligned imports break with the fractions of the export distribution.

    A port keeps the price and WTT of its import, on the assumption that the
    adjustment is rerouted equally from each of its supplying plants; a port without
    import receives none, as no delivery prices it.

    Parameters
    ----------
    imports
        Import of the fuel to each port, in tons/year.
    ports
        All ports in the simulation.
    fuel_name
        Name of the fuel.
    forward
        Slice of the timeline from the current time step onwards.

    Returns
    -------
    dict[str, FloatArray]
        Import of the fuel to each port within its bunkering limit, in tons/year.
    """
    surplus = {}
    deficit = {}
    unlimited = {}

    for port_name, port in ports.items():
        imported = imports[port_name]
        limit = port.expectation.get_bunkering_limit(fuel_name, forward)

        has_limit = np.isfinite(limit)
        has_import = imported > 0.0
        gap = imported - limit

        surplus[port_name] = np.where(has_limit & (gap > 0.0), gap, 0.0)
        deficit[port_name] = np.where(has_limit & (gap <= 0.0) & has_import, -gap, 0.0)
        unlimited[port_name] = ~has_limit & has_import

    total_surplus = np.sum(list(surplus.values()), axis=0)
    total_deficit = np.sum(list(deficit.values()), axis=0)
    unlimited_count = np.sum(list(unlimited.values()), axis=0)

    absorbed = np.minimum(total_surplus, total_deficit)
    remaining = total_surplus - absorbed
    unlimited_share = divide_nonzero(remaining, unlimited_count)

    aligned = {}

    for port_name, imported in imports.items():
        received = divide_nonzero(deficit[port_name], total_deficit) * absorbed
        spread = np.where(unlimited[port_name], unlimited_share, 0.0)
        aligned[port_name] = imported - surplus[port_name] + received + spread

    return aligned
