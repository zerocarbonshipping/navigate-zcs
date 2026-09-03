# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

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

logger = logging.getLogger(__name__)


def calculate_fuel_import_to_ports(ports: dict[str, Port],
                                   producers: dict[str, Producer],
                                   emissions: dict[str, Emission],
                                   fuels: dict[str, Fuel],
                                   timeline: np.ndarray,
                                   idx: int
                                   ) -> None:
    """
    Set bunker price, supply and WTT at each port from both liquid-market and producer imports.

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
        The simulation timeline.
    idx
        Current time-step index.
    """

    # split fuels: those drawn from a liquid market
    # versus those produced specifically for shipping
    liquid_fuels = {f: fuel for f, fuel in fuels.items() if fuel.liquid_market}
    production_fuels = {f: fuel for f, fuel in fuels.items() if not fuel.liquid_market}

    _calculate_import_from_liquid_market(ports, liquid_fuels, emissions, idx)
    _calculate_import_from_producers(ports,
                                     producers,
                                     emissions,
                                     production_fuels,
                                     timeline,
                                     idx)


def _calculate_import_from_liquid_market(ports: dict[str, Port],
                                         fuels: dict[str, Fuel],
                                         emissions: dict[str, Emission],
                                         idx: int
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
                price = port.expectation.get_bunker_price_overwrite(f, idx_)
            else:
                price = np.zeros(port.expectation.get_shape(idx))

            # add the handling cost of the
            # bunkering service itself to
            # the price of the fuel
            price += port.expectation.get_handling_cost(f, idx_)

            # transfer the bunker price
            # to expectation and profile
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
                supply = port.expectation.get_bunkering_limit(f, idx_)
            else:
                supply = np.zeros(port.expectation.get_shape(idx))

            port.expectation.set_bunker_supply(idx, f, supply)

            if allowed and np.isfinite(supply[0]):
                port.profile.set_bunker_supply_mass(idx, f, supply[0])

            for e in emissions:

                # check if the bunker WTT is overwritten on the port
                if port.bunker_wtt_overwrite[(f, e)] is not None:
                    wtt = port.expectation.get_bunker_wtt_overwrite(f, e, idx_)
                else:
                    wtt = np.zeros(port.expectation.get_shape(idx))

                # transfer the bunker WTT to
                # expectation and profile
                port.expectation.set_bunker_wtt(idx, f, e, wtt)

                if allowed:
                    port.profile.set_bunker_wtt(idx, f, e, wtt[0])


def _calculate_import_from_producers(ports: dict[str, Port],
                                     producers: dict[str, Producer],
                                     emissions: dict[str, Emission],
                                     fuels: dict[str, Fuel],
                                     timeline: np.ndarray,
                                     idx: int
                                     ) -> None:
    """
    Set supply-weighted bunker price, supply and WTT at each port for producer-supplied fuels.

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
        Simulation timeline
    idx
        Current time-step index.
    """

    idx_ = np.s_[idx:]
    times = timeline[idx_]

    # pre-allocate containers for weighted averages
    supplies = {p: {f: np.zeros_like(times) for f in fuels} for p in ports}
    prices = {p: {f: np.zeros_like(times) for f in fuels} for p in ports}
    wtts = {p: {(f, e): np.zeros_like(times) for f in fuels for e in emissions} for p in ports}

    # if the bunkering of a fuel is disallowed
    # in certain ports the export of fuel is
    # rerouted elsewhere by equal fractions
    export_normalization = _calculate_export_normalization_factors(ports)

    # loop over all producers and plants
    # and sum of the total supply of specific
    # fuels exported to the various ports
    for producer in producers.values():

        export_distribution = producer.expectation.get_export_distribution(idx=idx_)

        for plant in producer.plants:

            plant_name = plant.name

            # extract the fuel the plant produces
            fuel = plant.fuel
            f = fuel.name

            # if the fuel is not allowed for bunkering
            # in any port then no export can occur and
            # the available production is inaccessible
            if export_normalization[f] == 0.:

                logger.debug("Fuel(\"{}\") is not allowed for bunkering in any port. Any existing"
                             " production from {} is inaccessible during bunkering."
                             .format(f, plant))

                continue

            expectation = plant.expectation

            # extract the expected production
            production = producer.expectation.get_expected_production(plant_name, idx_)

            # export the production to individual ports
            for p, export in export_distribution.items():

                # if bunkering of the produced fuel
                # is disallowed in the port then skip
                if not ports[p].is_bunkering_allowed(f):
                    continue

                normalized_export = export / export_normalization[f]

                # weight each plant's production by its normalized export
                # fraction. an unconstrained producer reports infinite
                # production here; the resulting infinite supply is capped
                # per port later in _align_export_with_bunkering_limits.
                supply = production * normalized_export
                supplies[p][f] += supply

                # calculate the supply weighted price
                prices[p][f] += supply * expectation.get_expected_delivered_cost(p, idx_)

                # calculate the supply weighted WTT emissions
                for e in emissions:
                    wtts[p][(f, e)] += supply * expectation.get_expected_delivered_wtt(p, e, idx_)

    # transfer the supply-weighted average price
    # and WTT to the ports before adjusting the
    # supply to account for local supply limits
    for p, port in ports.items():

        for f in fuels:

            # check if the bunker price is overwritten on the port
            if port.bunker_price_overwrite[f] is not None:
                price = port.expectation.get_bunker_price_overwrite(f, idx_)
            else:
                # normalize the weighted average
                price = divide_nonzero(prices[p][f], supplies[p][f])

            # add handling costs
            handling_cost = port.expectation.get_handling_cost(f, idx_)
            price += handling_cost

            port.expectation.set_bunker_price(idx, f, price)

            if supplies[p][f][0] > 0.:
                port.profile.set_bunker_price(idx, f, price[0])

            for e in emissions:

                # check if the bunker WTT is overwritten on the port
                if port.bunker_wtt_overwrite[(f, e)] is not None:
                    wtt = port.expectation.get_bunker_wtt_overwrite(f, e, idx_)
                else:
                    # normalize the weighted average
                    wtt = divide_nonzero(wtts[p][(f, e)], supplies[p][f])

                # transfer the average bunker WTT
                # to expectation and profile
                port.expectation.set_bunker_wtt(idx, f, e, wtt)

                if supplies[p][f][0] > 0.:
                    port.profile.set_bunker_wtt(idx, f, e, wtt[0])

    # the import of fuel to ports is adjusted to
    # account for local bunkering limitations.
    # Notice the rerouting of fuel to ports has
    # no impact on the weighted averages of price
    # and emissions as it is assumed that the fuel
    # is rerouted equally from each plant and thus
    # the maintains their relative share
    _align_export_with_bunkering_limits(supplies, fuels, ports, idx_)

    for p, port in ports.items():
        for f in fuels:

            # zero out supply at positions where bunker price
            # could not be determined to prevent the optimizer
            # from using fuel at zero cost
            price = port.expectation.get_bunker_price(f, idx_)
            supplies[p][f] = np.where(price > TOLERANCE, supplies[p][f], 0.)

            # transfer the adjusted supply to the ports
            port.expectation.set_bunker_supply(idx, f, supplies[p][f])
            port.profile.set_bunker_supply_mass(idx, f, supplies[p][f][0])


def _calculate_export_normalization_factors(ports: dict[str, Port]) -> dict[str, float]:
    """
    Calculate export-normalization factors for each fuel to ensure all fuels are fully exported independent of whether
    it is allowed to bunker in certain ports.

    Parameters
    ----------
    ports
        All ports in the simulation.

    Returns
    -------
    dict[float]
        Dict of all fuels and their normalization factors during export from producer to port.
    """

    normalization = {}
    n_ports = len(ports)

    for port in ports.values():

        for fuel_name, allowed in port.bunkering_allowed.items():

            normalization.setdefault(fuel_name, 0.)

            if allowed:
                normalization[fuel_name] += 1.

    for fuel_name in normalization:

        normalization[fuel_name] /= n_ports

    return normalization


def _align_export_with_bunkering_limits(supplies: dict[str, dict[str, float | np.ndarray]],
                                        fuels: dict[str, Fuel],
                                        ports: dict[str, Port],
                                        idx: int | slice
                                        ) -> None:
    """
    The bunkering of a certain fuel in given port may be limited by the port. In that case no more fuel than can be
    bunkered should be exported to that port and the surplus distributed to the other ports.

    TODO: This method surely must break with the export distribution assigned on the producer. May be acceptable.

    Parameters
    ----------
    supplies
        Imported supply not accounting for bunker limits.
    fuels
        All fuels assigned to a plant and which can be bunkered in at least one port.
    ports
        All ports in the simulation.
    idx
        Current time-step index.
    """

    for fuel_name, fuel in fuels.items():

        # calculate the total import across all ports
        total_import = sum(supplies[port_name][fuel_name] for port_name in ports)

        # if the import to any port is infinite it
        # means there is an infinite production
        # potential and thus each port will be
        # assigned its limit
        infinite_mask = np.isinf(total_import)

        if np.any(infinite_mask):

            for port_name, port in ports.items():

                if not port.is_bunkering_allowed(fuel_name):
                    continue

                # if a port has zero import it must be
                # because the export distribution to that
                # port was set to zero for all producers.
                # This limitation is honored.
                active_mask = infinite_mask & (supplies[port_name][fuel_name] > 0.)

                # extract the limit and assign it
                limit = port.expectation.get_bunkering_limit(fuel_name, idx)
                supplies[port_name][fuel_name][active_mask] = limit[active_mask]

        # if the import is finite across all ports then a two-stage approach
        # is used in the redistribution of fuel between ports. First all
        # limit-constrained ports have a fair-redistribution after which the
        # remainder is distributed equally to unlimited ports
        finite_mask = ~np.isinf(total_import)

        if np.any(finite_mask):
            _align_finite_export_with_bunkering_limits(supplies,
                                                       fuel,
                                                       ports,
                                                       idx,
                                                       finite_mask)


def _align_finite_export_with_bunkering_limits(supplies: dict[str, dict[str, float | np.ndarray]],
                                               fuel: Fuel,
                                               ports: dict[str, Port],
                                               idx: int | slice,
                                               mask: np.ndarray
                                               ) -> None:
    """
    Redistribute the finite-import case: trim each over-limit port to its bunkering limit and spread the freed
    surplus across the under-limit ports in proportion to their deficit.

    Notice that this method breaks with the fractions assigned in the export distribution.

    TODO: make two-stage algorithm?

    Parameters
    ----------
    supplies
        Imported supply not accounting for bunker limits.
    fuel
        Fuels assigned to a plant and which can be bunkered in at least one port.
    ports
        All ports in the simulation.
    idx
        Current time-step index.
    mask
        Array index.
    """

    fuel_name = fuel.name

    surplus = {}
    deficit = {}

    for port_name, port in ports.items():

        # extract the imported amount and the bunkering limit
        imported = supplies[port_name][fuel_name][mask]
        limit = port.expectation.get_bunkering_limit(fuel_name, idx)[mask]

        # set default arrays
        surplus.setdefault(port_name, np.zeros_like(limit))
        deficit.setdefault(port_name, np.zeros_like(limit))

        # if bunkering of the produced fuel
        # is disallowed in the port then skip.
        # Must be called after defaulting of
        # surplus and deficit
        if not port.is_bunkering_allowed(fuel_name):
            continue

        # calculate the gap between imported and bunkering limit
        # positive is a surplus and negative is a deficit
        gap = imported - limit

        surplus[port_name] = np.where(gap > 0., gap, 0.)
        deficit[port_name] = np.where(gap <= 0., -gap, 0.)

    # calculate the total surplus and deficit
    total_surplus = np.sum(list(surplus.values()), axis=0)
    total_deficit = np.sum(list(deficit.values()), axis=0)

    # if there is no surplus it cannot be rerouted
    if np.all(total_surplus == 0.):
        return

    # calculate the maximum fraction that
    # can be redistributed if the surplus
    # is larger than the deficit
    scaling = np.minimum(divide_nonzero(total_deficit, total_surplus), 1.)

    # calculate the adjusted import
    for port_name in ports:

        if port_name in surplus:

            # reduce the imported supply to the bunkering limit
            supplies[port_name][fuel_name][mask] -= surplus[port_name]

        else:

            # increase the imported supply proportional
            # to the ports relative deficit
            supplies[port_name][fuel_name][mask] += (deficit[port_name] / total_deficit) * scaling * total_surplus
