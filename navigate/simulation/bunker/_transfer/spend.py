# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer the fuel spend at sea and in port to the vessel expectations and results."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from navigate.core.enum_ import BunkerScopeID

if TYPE_CHECKING:
    from collections.abc import Iterator

    from navigate.core.enum_ import FuelTypeID
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def transfer_spend(alg: BunkerAlgorithm) -> None:
    """
    Transfer the fuel spend at sea and in port to the vessel expectations and results.

    The energy each converter spent goes to the vessel expectations, the TTW
    emissions of each fuel to the vessel results.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    if alg.scope != BunkerScopeID.EXISTING:
        return

    # every fleet vessel restarts its spent energy from zero, also one out of the LP
    for fleet in alg.fleets.values():
        for vessel in fleet.vessels:
            vessel.expectation.reset_spend_energy()

    mass: defaultdict[tuple[str, str], float] = defaultdict(float)
    ttw: defaultdict[tuple[str, str, str], float] = defaultdict(float)

    for v, c, f, spend in _iterate_spend(alg):
        expectation = alg.vessels[v].expectation

        # the effective LHV accounts for slip
        expectation.spend_energy[c] += spend * expectation.effective_lhv[c, f]

        # the recorded emissions always count the slip, whatever a policy counts
        mass[v, f] += spend
        for emission_name in alg.emissions:
            ttw_consumption = expectation.ttw_consumption[c, f, emission_name]
            ttw_slip = expectation.ttw_slip[c, f, emission_name]
            ttw[v, f, emission_name] += (ttw_consumption + ttw_slip) * spend

    _transfer_ttw(alg, mass, ttw)


def _iterate_spend(alg: BunkerAlgorithm) -> Iterator[tuple[str, str, str, float]]:
    """
    Walk the fuel masses the solution spends, at sea, then in port.

    A spend below the solution tolerance is left out.

    Parameters
    ----------
    alg
        The algorithm instance.

    Yields
    ------
    tuple[str, str, str, float]
        Vessel, converter and fuel name, and the mass spent, in tons/year.
    """
    tolerance = alg.options.solution_tolerance

    for (v, c, f, _, _), spend_sea in alg.spend_sea.items():
        spend = alg.model.value(spend_sea)
        if spend >= tolerance:
            yield v, c, f, spend

    for (v, c, f, _), spend_port in alg.spend_port.items():
        spend = alg.model.value(spend_port)
        if spend >= tolerance:
            yield v, c, f, spend


def _transfer_ttw(
    alg: BunkerAlgorithm,
    mass: defaultdict[tuple[str, str], float],
    ttw: defaultdict[tuple[str, str, str], float],
) -> None:
    r"""
    Write the TTW emissions per fuel, those of one substance shared by mass spent.

    A converter burns a ton of one fuel of a substance (see ``_group_substances``)
    exactly as a ton of another: which of them the solution has each converter burn
    changes neither the energy delivered nor the vessel's emissions, and is
    arbitrary unless a regulation counts them differently: one that polices only
    some of them, or is given TTW emissions of its own for some. Where the
    converters differ in slip or consumption emissions, the emissions of each of
    the fuels would follow that choice. Every converter is therefore taken to burn
    them in the proportions the vessel spends them, as from one tank. For fuel f of
    substance S and each emission (vessel index omitted):

        t_f = (m_f / \sum_{g in S} m_g) \sum_{g in S} s_g

    where m is the mass the vessel spends of a fuel, s the emissions of a fuel as
    the solution burns it and t those recorded, all in tons/year. The emissions of
    the substance, and with them the vessel's total of each emission, are the
    solution's by construction, and so are the emissions of a fuel that is a
    substance of its own.

    Fuels of one fuel type that are not one substance, such as two of different
    heating value, keep the solution's emissions, per fuel and in total. Where
    their converters differ in slip and no regulation counts the difference, those
    follow a choice of converter that is as arbitrary.

    Parameters
    ----------
    alg
        The algorithm instance.
    mass
        Fuel mass spent per vessel and fuel name, in tons/year.
    ttw
        Emissions of the fuel as the solution burns it, per vessel, fuel and
        emission name, in tons/year.
    """
    substances = _group_substances(alg)

    for v, vessel in alg.vessels.items():
        results = vessel.results

        for fuels in substances:
            mass_total = sum(mass[v, f] for f in fuels)

            # a vessel that spent none of the substance emitted nothing from it
            if mass_total == 0.0:
                continue

            shares = {f: mass[v, f] / mass_total for f in fuels}

            for emission_name in alg.emissions:
                ttw_total = sum(ttw[v, f, emission_name] for f in fuels)

                for f, share in shares.items():
                    results.ttw[f, emission_name][alg.idx] = share * ttw_total


def _group_substances(alg: BunkerAlgorithm) -> list[list[str]]:
    """
    Group the fuels that are one substance to a converter.

    Fuels are one substance where they share the fuel type, the lower heating
    value and the TTW emission factor of every emission. The values are compared as
    evaluated: two that differ in the last digit are two substances, which only
    leaves their fuels the solution's emissions.

    Parameters
    ----------
    alg
        The algorithm instance.

    Returns
    -------
    list[list[str]]
        Names of the fuels of each substance, every fuel in one.
    """
    groups: defaultdict[tuple[FuelTypeID | float, ...], list[str]] = defaultdict(list)

    for f, fuel in alg.fuels.items():
        lhv = fuel.lower_heating_value.get()
        ttw = [fuel.ttw[emission_name].get() for emission_name in alg.emissions]
        groups[fuel.fuel_type, lhv, *ttw].append(f)

    return list(groups.values())
