# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The remedial expenses of the vessels policed by individual regulations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import BunkerScopeID, RegulationSchemeID
from navigate.simulation.policy._policed import select_policed

if TYPE_CHECKING:
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel


def calculate_individual_remedial_expenses(
    regulations: dict[str, Regulation],
    vessels: dict[str, Vessel],
    multipliers: dict[str, float],
    scope: BunkerScopeID,
    idx: int,
) -> None:
    """
    Price the remedial units of each active INDIVIDUAL regulation from the LP results.

    Each policed vessel remediates its own non-compliance with the remedial units the
    bunkering LP chose for it, at the remedial cost of the regulation.

    Parameters
    ----------
    regulations
        All regulations in the simulation.
    vessels
        All vessels in the simulation.
    multipliers
        Multiplier of each vessel in the bunkering LP, in the LP's order, which the
        sums over the vessels follow.
    scope
        Scope of the bunkering LP: the existing expenses go to the results, the
        expected ones to the expectations.
    idx
        Time-step index of the bunkering LP.
    """
    for regulation in regulations.values():
        is_individual = regulation.scheme == RegulationSchemeID.INDIVIDUAL
        if not (regulation.active and is_individual):
            continue

        _calculate_regulation_remedial_expenses(
            regulation, vessels, multipliers, scope, idx
        )


def _calculate_regulation_remedial_expenses(
    regulation: Regulation,
    vessels: dict[str, Vessel],
    multipliers: dict[str, float],
    scope: BunkerScopeID,
    idx: int,
) -> None:
    """Price the remedial units of one regulation; see the public function."""
    expectation = regulation.expectation
    remedial_cost = expectation.get_remedial_cost(idx)

    for vessel_name, multiplier in select_policed(regulation, multipliers).items():
        vessel = vessels[vessel_name]

        remedial_units = expectation.get_vessel_remedial_units(vessel_name, idx)
        remedial_expenses = remedial_units * remedial_cost

        if scope == BunkerScopeID.EXISTING:
            # the regulation totals cover all the vessels the LP vessel represents
            total_remedial_units = remedial_units * multiplier
            total_remedial_expenses = total_remedial_units * remedial_cost

            regulation.results.remedial_units[idx] += total_remedial_units
            regulation.results.remedial_expenses[idx] += total_remedial_expenses
            vessel.results.remedial_units[regulation.name][idx] += remedial_units
            vessel.results.remedial_expenses[idx] += remedial_expenses

        else:
            vessel.expectation.add_remedial_expenses(idx, remedial_expenses)
