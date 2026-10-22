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
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray

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
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    liquid_fuels = {f: fuel for f, fuel in fuels.items() if fuel.liquid_market}
    production_fuels = {f: fuel for f, fuel in fuels.items() if not fuel.liquid_market}

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
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    forward = np.s_[idx:]
    zeros = np.zeros_like(timeline[forward])
    zero_wtts = dict.fromkeys(emissions, zeros)

    for port in ports.values():
        for f in fuels:
            allowed = port.is_bunkering_allowed(f)
            limit = np.asarray(port.expectation.get_bunkering_limit(f, forward))

            bunker_price = _calculate_bunker_price(port, f, zeros, forward)
            bunker_wtts = _calculate_bunker_wtts(port, f, zero_wtts, forward)
            bunker_supply = limit if allowed else zeros

            port.expectation.set_bunker_price(idx, f, bunker_price)
            port.expectation.set_bunker_supply(idx, f, bunker_supply)

            for key, value in bunker_wtts.items():
                port.expectation.set_bunker_wtt(idx, f, key, value)

            if allowed:
                port.results.bunker_price[f][idx] = bunker_price[0]

                for key, value in bunker_wtts.items():
                    port.results.bunker_wtt[f, key][idx] = value[0]

            if allowed and np.isfinite(bunker_supply[0]):
                port.results.bunker_supply_mass[f][idx] = bunker_supply[0]


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
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    forward = np.s_[idx:]

    supplies, costs, wtts = _calculate_import_totals(
        ports, producers, emissions, fuels, timeline, idx
    )

    # price and WTT are averaged before the supply is aligned with the bunkering
    # limits; the alignment reroutes supply equally from each plant, so keeps them
    for f in fuels:
        for p, port in ports.items():
            supply = supplies[f][p]
            supplied = supply[0] > 0.0

            average_cost = divide_nonzero(costs[f][p], supply)
            average_wtts = {e: divide_nonzero(wtts[f, e][p], supply) for e in emissions}

            bunker_price = _calculate_bunker_price(port, f, average_cost, forward)
            bunker_wtts = _calculate_bunker_wtts(port, f, average_wtts, forward)

            port.expectation.set_bunker_price(idx, f, bunker_price)

            for key, value in bunker_wtts.items():
                port.expectation.set_bunker_wtt(idx, f, key, value)

            if supplied:
                port.results.bunker_price[f][idx] = bunker_price[0]

                for key, value in bunker_wtts.items():
                    port.results.bunker_wtt[f, key][idx] = value[0]

    for f in fuels:
        supplies[f] = _align_with_bunkering_limits(supplies[f], ports, f, forward)

    # a port without a bunker price supplies nothing, so the optimizer cannot use the
    # fuel at zero cost
    for f in fuels:
        for p, port in ports.items():
            bunker_price = port.expectation.get_bunker_price(f, forward)
            bunker_supply = np.where(bunker_price > TOLERANCE, supplies[f][p], 0.0)

            port.expectation.set_bunker_supply(idx, f, bunker_supply)
            port.results.bunker_supply_mass[f][idx] = bunker_supply[0]


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
        Simulation timeline, days.
    idx
        Current time-step index.

    Returns
    -------
    _ImportTotals
        The supply of each fuel at each port, with its supply-weighted cost and WTT.
    """
    forward = np.s_[idx:]
    times = timeline[forward]

    shares = _allowed_port_shares(ports)

    supplies = {}
    costs = {}
    wtts = {}

    for f in fuels:
        supplies[f] = {p: np.zeros_like(times) for p in ports}
        costs[f] = {p: np.zeros_like(times) for p in ports}

        for e in emissions:
            wtts[f, e] = {p: np.zeros_like(times) for p in ports}

    for producer in producers.values():
        exports = producer.expectation.get_export_distribution(idx=forward)

        for plant in producer.plants:
            f = plant.fuel.name

            if shares[f] == 0.0:
                logger.debug(
                    'Fuel("%s") is not allowed for bunkering in any port. Any existing '
                    "production from %s is inaccessible during bunkering.",
                    f,
                    plant,
                )

                continue

            expectation = plant.expectation
            production = producer.expectation.get_expected_production(
                plant.name, forward
            )
            production_cost = expectation.get_expected_production_cost(forward)

            production_wtts = {}
            for e in emissions:
                production_wtts[e] = expectation.get_expected_production_wtt(e, forward)

            for p, export in exports.items():
                if not ports[p].is_bunkering_allowed(f):
                    continue

                rerouted = export / shares[f]
                supply = production * rerouted
                delivery_cost = expectation.get_levelized_delivery_cost(p, forward)

                supplies[f][p] += supply
                costs[f][p] += supply * (production_cost + delivery_cost)

                for e in emissions:
                    delivery_wtt = expectation.get_delivery_wtt(p, e, forward)
                    wtts[f, e][p] += supply * (production_wtts[e] + delivery_wtt)

    return _ImportTotals(supplies, costs, wtts)


def _calculate_bunker_price(
    port: Port, fuel_name: str, fallback: FloatArray, idx: slice
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
    idx
        Slice of the timeline from the current time step onwards.

    Returns
    -------
    FloatArray
        Bunker price, in USD/t.
    """
    overwrite = port.expectation.get_bunker_price_overwrite(fuel_name, idx)
    overwritten = port.bunker_price_overwrite[fuel_name] is not None
    price = np.asarray(overwrite) if overwritten else fallback

    # the overwrite getter returns a view into stored state, so the handling cost is
    # added out of place rather than onto it
    return price + port.expectation.get_handling_cost(fuel_name, idx)


def _calculate_bunker_wtts(
    port: Port, fuel_name: str, fallbacks: dict[str, FloatArray], idx: slice
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
    idx
        Slice of the timeline from the current time step onwards.

    Returns
    -------
    dict[str, FloatArray]
        Bunker WTT per emission, in t/t.
    """
    wtts = {}

    for e, fallback in fallbacks.items():
        overwrite = port.expectation.get_bunker_wtt_overwrite(fuel_name, e, idx)
        overwritten = port.bunker_wtt_overwrite[(fuel_name, e)] is not None
        wtts[e] = np.asarray(overwrite) if overwritten else fallback

    return wtts


def _allowed_port_shares(ports: dict[str, Port]) -> dict[str, float]:
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

    return {f: count / len(ports) for f, count in counts.items()}


def _align_with_bunkering_limits(
    imports: dict[str, FloatArray], ports: dict[str, Port], fuel_name: str, idx: slice
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
        Import of the fuel to each port, in t/year.
    ports
        All ports in the simulation.
    fuel_name
        Name of the fuel.
    idx
        Slice of the timeline from the current time step onwards.

    Returns
    -------
    dict[str, FloatArray]
        Import of the fuel to each port within its bunkering limit, in t/year.
    """
    surplus = {}
    deficit = {}
    unlimited = {}

    for p, port in ports.items():
        imported = imports[p]
        limit = port.expectation.get_bunkering_limit(fuel_name, idx)

        has_limit = np.isfinite(limit)
        has_import = imported > 0.0
        gap = imported - limit

        surplus[p] = np.where(has_limit & (gap > 0.0), gap, 0.0)
        deficit[p] = np.where(has_limit & (gap <= 0.0) & has_import, -gap, 0.0)
        unlimited[p] = ~has_limit & has_import

    total_surplus = np.sum(list(surplus.values()), axis=0)
    total_deficit = np.sum(list(deficit.values()), axis=0)
    unlimited_count = np.sum(list(unlimited.values()), axis=0)

    absorbed = np.minimum(total_surplus, total_deficit)
    remaining = total_surplus - absorbed
    unlimited_share = divide_nonzero(remaining, unlimited_count)

    aligned = {}

    for p, imported in imports.items():
        received = divide_nonzero(deficit[p], total_deficit) * absorbed
        spread = np.where(unlimited[p], unlimited_share, 0.0)
        aligned[p] = imported - surplus[p] + received + spread

    return aligned
