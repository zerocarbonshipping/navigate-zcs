# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
State the rules that select among equally cheap solutions of the bunkering LP.

A solve applies three rules, each among the solutions the ones before it left
(_selection.py):

1. the vessel types of the one pool that binds each take the same share of their
   own room;
2. the regulated emissions are the least;
3. the bunker peaks are the least.

Six choices are left to the solver, as no rule decides them:

- the stops of a route of three or more stops that sell a fuel at one price, where
  another stop sets the peak of the fuel, such as a cheaper one capped by its fair
  share: the split of the fuel among the stops below the peak;
- two fuels a vessel burns in the same converters, where the regulated emissions
  are the same whichever of them it burns where: the split of each fuel among the
  legs, ports and converters. The emission results are summed over the fuels, so
  where the two have the same heating value and emission factors they do not
  depend on it;
- two fuels that cost a vessel the same at the same stops, have the same
  regulated emissions and the same heating value: the amount of each the vessel
  bunkers and burns. The bunker peaks add up to the same mass whatever the split:
  100 t at two stops of one price is 50 t of one fuel at each, or 25 t of each
  fuel at each, and the peaks sum to 50 t either way;
- the vessel types of a pool that can trade their terms at no cost while two or
  more pools bind: the split among the types, as far as the second rule leaves it;
- the same types where the shares of the first rule cannot be met together with
  another constraint, such as the threshold of a second pool that does not bind:
  the rule is then left out;
- two priced constraints that bind only together and, relaxed in proportion to
  their sizes, would allow the same amount: which of the two carries the price,
  and with it which of two such pools binds (_selection.py, Duals).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.simulation.bunker._solver import MinimizingRule, Pool

if TYPE_CHECKING:
    from navigate.simulation.bunker._solver import Terms, Variable
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def update_selection_rules(alg: BunkerAlgorithm) -> None:
    """
    Update the rules by which a solve selects among equally cheap solutions.

    The regulated emissions come before the bunker peaks, so between two fuels that
    cost a vessel the same, the mass of the peaks decides only where their regulated
    emissions are the same too.

    The two minimizing rules count a vessel type as one vessel, whatever its
    count. A rule so weighs every type alike, and its coefficients keep the scale
    of one vessel, large against the tolerance of the model (MinimizingRule),
    where a count can be small. The share of room weighs a type by its count, as
    the constraint of its pool does, and comes first: a rule that counts each type
    as one vessel would take a trade between two types of a pool as far as it
    goes, to the lower emissions for the type with fewer vessels.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    pools = _calculate_pools(alg)
    minimizing_rules = [
        MinimizingRule("regulated emissions", _calculate_regulated_emission_terms(alg)),
        MinimizingRule("bunker peaks", _calculate_bunker_peak_terms(alg)),
    ]

    alg.model.set_selection_rules(pools, minimizing_rules)


def _calculate_pools(alg: BunkerAlgorithm) -> list[Pool]:
    r"""
    Calculate the pools of the share of room: one per FLEXIBLE regulation.

    The pool of regulation r is its threshold constraint
    (regulation_threshold_flexibility), with the terms T_{r,v} of the vessel types
    it polices as members, weighted by their counts n_v, and its remedial units
    w_r as the excess. Where the threshold binds and several types can each cut
    their term at the cost another saves by raising its own, every split of the
    cut among them costs the same. Each type then takes the same share of its own
    room, the range between the least and the largest term it can have at that
    cost, whatever the other types do (_selection.py, Share of room). Two
    identical types so end at the same term, and a type with twice the room cuts
    twice as much.

    Where a remedial unit costs what a cut costs, the pool cuts before it pays: it
    buys remedial units only for what its types cannot cut.

    Parameters
    ----------
    alg
        The algorithm instance.

    Returns
    -------
    list[Pool]
        Per FLEXIBLE regulation in the LP, its threshold constraint, its remedial
        factor and the term of each vessel it polices.
    """
    members: dict[str, list[Variable]] = {}

    for r in alg.regulation_threshold_flexibility:
        members[r] = []

    for (r, _), pooled_term in alg.pooled_term.items():
        members[r].append(pooled_term)

    pools = []

    for r, constraint in alg.regulation_threshold_flexibility.items():
        remedial_factor = alg.remedial_factor_flexibility[r]
        pools.append(Pool(constraint, remedial_factor, members[r]))

    return pools


def _calculate_regulated_emission_terms(alg: BunkerAlgorithm) -> Terms:
    r"""
    Calculate the terms of the regulated-emissions rule: the sum of those emissions.

        \sum_{r} \sum_{v policed} M_{r,v}

    where M is the emissions of calculate_regulation_terms, of vessel v under
    regulation r. Where the threshold of a regulation does not bind, a vessel so
    burns its fuels on the legs and in the ports that make its regulated emissions
    the least its fuels allow. Where the threshold of a pool binds, the rule decides
    among the solutions at which each type holds its share of room.

    Parameters
    ----------
    alg
        The algorithm instance.

    Returns
    -------
    Terms
        The emission terms of every regulation and policed vessel, one after another.
    """
    terms: Terms = []

    for emission_terms in alg.regulation_emission_terms.values():
        terms.extend(emission_terms)

    return terms


def _calculate_bunker_peak_terms(alg: BunkerAlgorithm) -> Terms:
    r"""
    Calculate the terms of the bunker-peaks rule: the sum of the bunker peaks.

        \sum_{v} \sum_{f} \hat{b}_{v,f}

    where \hat{b} is the peak of fuel f on vessel v, at its least the largest mass
    of the fuel the vessel bunkers at one stop (bunker_below_peak); two calls at
    one port are two stops. Where the fuel costs the same at several stops and
    nothing else limits them, the vessel so bunkers the same mass at each. Where
    another stop sets the peak, such as a cheaper one capped by its fair share, the
    rule leaves the split among the stops below it open: with two stops the other
    one takes the rest, and with more the solver splits it.

    The peaks add up in mass, so where the rule is left the choice between two
    fuels, it takes the one the vessel needs less mass of.

    Parameters
    ----------
    alg
        The algorithm instance.

    Returns
    -------
    Terms
        Each bunker peak with the coefficient one.
    """
    return [(peak, 1.0) for peak in alg.bunker_peak.values()]
