# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Bunker price, supply and WTT of each fuel at each port."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.util import TOLERANCE, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)


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
        The simulation timeline, days.
    idx
        Current time-step index.
    """
    liquid_fuels = {f: fuel for f, fuel in fuels.items() if fuel.liquid_market}
    production_fuels = {f: fuel for f, fuel in fuels.items() if not fuel.liquid_market}

    _calculate_import_from_liquid_market(ports, liquid_fuels, emissions, idx)
    _calculate_import_from_producers(
        ports, producers, emissions, production_fuels, timeline, idx
    )


def _calculate_import_from_liquid_market(
    ports: dict[str, Port],
    fuels: dict[str, Fuel],
    emissions: dict[str, Emission],
    idx: int,
) -> None:
    """
    Set bunker price, supply and WTT at each port for fuels drawn from a liquid market.

    Parameters
    ----------
    ports
        All ports in the simulation.
    emissions
        All emissions in the simulation.
    fuels
        All fuels in the simulation which belong to a liquid market.
    idx
        Current time-step index.
    """
    idx_ = np.s_[idx:]

    for port in ports.values():
        for f in fuels:
            allowed = port.is_bunkering_allowed(f)

            if port.bunker_price_overwrite[f] is not None:
                base_price = np.asarray(
                    port.expectation.get_bunker_price_overwrite(f, idx_)
                )
            else:
                base_price = np.zeros(port.expectation.get_shape(idx))

            # the overwrite getter returns a view into stored state, so the
            # handling cost is added out of place rather than onto it
            price = base_price + port.expectation.get_handling_cost(f, idx_)
            port.expectation.set_bunker_price(idx, f, price)

            if allowed:
                port.profile.set_bunker_price(idx, f, price[0])

            # propagate the declared bunkering limit as the liquid-market supply.
            # _bunkering_limit defaults to np.inf, so ports that do not call
            # set_bunkering_limit keep supply effectively unconstrained and the
            # fair_share_fuel LP constraint stays inactive (skipped on non-finite
            # supply). A finite cap flows through to fair-share allocation and
            # makes the per-port bunkering limit bind on the LP.
            if allowed:
                supply = np.asarray(port.expectation.get_bunkering_limit(f, idx_))
            else:
                supply = np.zeros(port.expectation.get_shape(idx))

            port.expectation.set_bunker_supply(idx, f, supply)

            if allowed and np.isfinite(supply[0]):
                port.profile.set_bunker_supply_mass(idx, f, supply[0])

            for e in emissions:
                if port.bunker_wtt_overwrite[(f, e)] is not None:
                    wtt = np.asarray(
                        port.expectation.get_bunker_wtt_overwrite(f, e, idx_)
                    )
                else:
                    wtt = np.zeros(port.expectation.get_shape(idx))

                port.expectation.set_bunker_wtt(idx, f, e, wtt)

                if allowed:
                    port.profile.set_bunker_wtt(idx, f, e, wtt[0])


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
    idx_ = np.s_[idx:]
    times = timeline[idx_]

    supplies = {p: {f: np.zeros_like(times) for f in fuels} for p in ports}
    prices = {p: {f: np.zeros_like(times) for f in fuels} for p in ports}
    wtts = {
        p: {(f, e): np.zeros_like(times) for f in fuels for e in emissions}
        for p in ports
    }

    # a fuel disallowed in some ports has its export rerouted to the others by
    # equal fractions
    export_normalization = _calculate_export_normalization_factors(ports)

    for producer in producers.values():
        export_distribution = producer.expectation.get_export_distribution(idx=idx_)

        for plant in producer.plants:
            plant_name = plant.name
            f = plant.fuel.name

            if export_normalization[f] == 0.0:
                logger.debug(
                    'Fuel("%s") is not allowed for bunkering in any port. Any existing '
                    "production from %s is inaccessible during bunkering.",
                    f,
                    plant,
                )

                continue

            expectation = plant.expectation
            production = producer.expectation.get_expected_production(plant_name, idx_)

            for p, export in export_distribution.items():
                if not ports[p].is_bunkering_allowed(f):
                    continue

                normalized_export = export / export_normalization[f]

                supply = production * normalized_export
                supplies[p][f] += supply
                prices[p][f] += supply * expectation.get_expected_delivered_cost(
                    p, idx_
                )

                for e in emissions:
                    wtts[p][(f, e)] += supply * expectation.get_expected_delivered_wtt(
                        p, e, idx_
                    )

    # the supply-weighted average price and WTT are transferred before the supply
    # is adjusted to the local bunkering limits
    for p, port in ports.items():
        for f in fuels:
            if port.bunker_price_overwrite[f] is not None:
                base_price = np.asarray(
                    port.expectation.get_bunker_price_overwrite(f, idx_)
                )
            else:
                base_price = divide_nonzero(prices[p][f], supplies[p][f])

            # the overwrite getter returns a view into stored state, so the
            # handling cost is added out of place rather than onto it
            price = base_price + port.expectation.get_handling_cost(f, idx_)
            port.expectation.set_bunker_price(idx, f, price)

            if supplies[p][f][0] > 0.0:
                port.profile.set_bunker_price(idx, f, price[0])

            for e in emissions:
                if port.bunker_wtt_overwrite[(f, e)] is not None:
                    wtt = np.asarray(
                        port.expectation.get_bunker_wtt_overwrite(f, e, idx_)
                    )
                else:
                    wtt = divide_nonzero(wtts[p][(f, e)], supplies[p][f])

                port.expectation.set_bunker_wtt(idx, f, e, wtt)

                if supplies[p][f][0] > 0.0:
                    port.profile.set_bunker_wtt(idx, f, e, wtt[0])

    # the import of fuel to ports is adjusted to account for local bunkering
    # limits. A port that already imports the fuel keeps the price and WTT
    # just written, on the assumption that the adjustment is rerouted equally
    # from each of the port's supplying plants and so preserves their relative
    # share; a port with no import receives none of the redistribution and its
    # price and WTT stay at zero
    for fuel in fuels.values():
        _align_export_with_bunkering_limits(supplies, fuel, ports, idx_)

    for p, port in ports.items():
        for f in fuels:
            # zero out supply where the bunker price could not be determined, so
            # the optimizer cannot use the fuel at zero cost
            bunker_price = port.expectation.get_bunker_price(f, idx_)
            supplies[p][f] = np.where(bunker_price > TOLERANCE, supplies[p][f], 0.0)

            port.expectation.set_bunker_supply(idx, f, supplies[p][f])
            port.profile.set_bunker_supply_mass(idx, f, supplies[p][f][0])


def _calculate_export_normalization_factors(ports: dict[str, Port]) -> dict[str, float]:
    """
    Calculate each fuel's export-normalization factor.

    Ensures all fuels are fully exported independent of whether it is allowed to
    bunker in certain ports.

    Parameters
    ----------
    ports
        All ports in the simulation.

    Returns
    -------
    dict[str, float]
        Dict of all fuels and their normalization factors during export from producer to
        port.
    """
    normalization: dict[str, float] = {}
    n_ports = len(ports)

    for port in ports.values():
        for fuel_name, allowed in port.bunkering_allowed.items():
            normalization.setdefault(fuel_name, 0.0)

            if allowed:
                normalization[fuel_name] += 1.0

    for fuel_name in normalization:
        normalization[fuel_name] /= n_ports

    return normalization


def _align_export_with_bunkering_limits(
    supplies: dict[str, dict[str, FloatArray]],
    fuel: Fuel,
    ports: dict[str, Port],
    idx: slice,
) -> None:
    """
    Align the exports of one fuel with the port bunkering limits.

    The bunkering of a fuel in a given port may be limited by the port; in that case
    no more fuel than can be bunkered should be exported to that port. Each
    over-limit port is trimmed to its bunkering limit and the freed surplus is spread
    across the under-limit ports in proportion to their deficit. A port with no
    bunkering limit set never has a deficit of its own - a shortfall against an
    infinite limit is meaningless - so whatever surplus the limited ports cannot
    absorb is split equally across the unlimited, allowed ports instead. Where
    neither can take it, the surplus is dropped and the total bunkered import
    shrinks. A port the producers' export distribution sends no fuel to receives
    none of the redistributed surplus either.

    Notice that this method breaks with the fractions assigned in the export
    distribution.

    Parameters
    ----------
    supplies
        Imported supply not accounting for bunker limits, adjusted in place.
    fuel
        Fuel assigned to a plant and which can be bunkered in at least one port.
    ports
        All ports in the simulation.
    idx
        Slice of the timeline from the current time step onwards.
    """
    fuel_name = fuel.name

    surplus = {}
    deficit = {}
    unlimited = {}

    for port_name, port in ports.items():
        imported = supplies[port_name][fuel_name]
        limit = port.expectation.get_bunkering_limit(fuel_name, idx)

        # a disallowed port neither contributes to nor receives a share of the
        # redistribution
        surplus[port_name] = np.zeros_like(limit)
        deficit[port_name] = np.zeros_like(limit)
        unlimited[port_name] = np.zeros_like(limit, dtype=bool)

        if not port.is_bunkering_allowed(fuel_name):
            continue

        # a port without a finite limit can never be over it, and a deficit
        # against an infinite limit does not exist; it is handled below instead
        has_limit = np.isfinite(limit)

        # a port the export distribution sends nothing to has no fuel to give up
        # and registers no deficit either: its weighted price and WTT are left at
        # zero upstream, so any share handed to it here could not be attributed
        # to a real delivery
        has_import = imported > 0.0
        unlimited[port_name] = ~has_limit & has_import

        gap = imported - limit

        surplus[port_name] = np.where(has_limit & (gap > 0.0), gap, 0.0)
        deficit[port_name] = np.where(has_limit & (gap <= 0.0) & has_import, -gap, 0.0)

    total_surplus = np.sum(list(surplus.values()), axis=0)
    total_deficit = np.sum(list(deficit.values()), axis=0)

    if np.all(total_surplus == 0.0):
        return

    # the surplus fills at most the whole deficit
    scaling = np.minimum(divide_nonzero(total_deficit, total_surplus), 1.0)

    # trim every over-limit port to its bunkering limit, and fill every
    # under-limit port's deficit in proportion to its share of the total deficit
    for port_name in ports:
        supplies[port_name][fuel_name] += -surplus[port_name] + (
            divide_nonzero(deficit[port_name], total_deficit) * scaling * total_surplus
        )

    # spread whatever surplus the limited ports could not absorb equally across
    # the unlimited, allowed ports; it is dropped where none of those exist
    remaining_surplus = np.maximum(total_surplus - total_deficit, 0.0)
    n_unlimited = np.sum(list(unlimited.values()), axis=0)
    share = divide_nonzero(remaining_surplus, n_unlimited)

    for port_name in ports:
        supplies[port_name][fuel_name] += np.where(unlimited[port_name], share, 0.0)
