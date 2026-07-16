# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Post-bunkering reclassification of compliance payments into physical emission offsets.

After the existing bunkering LP has solved, each active regulation or levy that allows
offsetting is revisited: when the global offsetting cost undercuts the policy's compliance
cost (a regulation's remedial cost or a levy's level), the LP has already charged the
truncated cost, so the matching remedial/levy units and expenses are reclassified as offsets
on both the policy profile and the per-vessel profiles. Entry point: calculate_offsetting,
invoked once per time step by the simulation manager.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from navigate.model_definition import ModelDefinition
    from navigate.policy.levy import Levy
    from navigate.policy.regulation import Regulation
    from navigate.vessel.fleet import Fleet
    from navigate.vessel import Vessel

from navigate.core.enum_ import LevySchemeID
from navigate.util import divide_nonzero


def calculate_offsetting(regulations: dict[str, Regulation],
                         levies: dict[str, Levy],
                         vessels: dict[str, Vessel],
                         fleets: dict[str, Fleet],
                         model_definition: ModelDefinition,
                         idx: int) -> None:
    """
    Post-bunkering offsetting calculation.

    After the existing bunkering LP has been solved, this function identifies which remedial
    or levy payments should be reclassified as physical emission offsets. If the global offsetting
    cost is cheaper than the policy's compliance cost, the LP will have already used the truncated
    cost — here we reclassify those units from remedial/levy payments to offset payments.

    Per-vessel remedial and levy units are tracked directly from the LP transfer, so offsets
    are reclassified on vessel profiles without needing to reconstruct the LP's per-vessel
    emission breakdown.

    Parameters
    ----------
    regulations
        All regulations in the simulation.
    levies
        All levies in the simulation.
    vessels
        All vessels in the simulation.
    fleets
        All fleets in the simulation.
    model_definition
        The model definition containing offsetting parameters.
    idx
        Current time-step index.
    """

    if not model_definition.get_enable_offsetting():
        return

    offsetting_cost = model_definition.get_offsetting_cost().get()
    multipliers = _build_multiplier_map(fleets, idx)

    _calculate_regulation_offsetting(regulations, offsetting_cost, vessels, multipliers, idx)
    _calculate_levy_offsetting(levies, offsetting_cost, vessels, multipliers, idx)


def _calculate_regulation_offsetting(regulations: dict[str, Regulation],
                                     offsetting_cost: float,
                                     vessels: dict[str, Vessel],
                                     multipliers: dict[str, float],
                                     idx: int) -> None:
    """
    Reclassify remedial units as offsets for regulations where offsetting is cheaper.

    Parameters
    ----------
    regulations
        All regulations in the simulation.
    offsetting_cost
        The global offsetting cost in USD/ton emission.
    vessels
        All vessels in the simulation.
    multipliers
        Mapping from vessel name to fleet multiplier.
    idx
        Current time-step index.
    """

    get_units = lambda profile, policy_name: profile.get_remedial_units(policy_name, idx)
    add_units = lambda profile, policy_name, delta: profile.add_remedial_units(policy_name, idx, delta)

    for regulation in regulations.values():

        if not regulation.is_active():
            continue

        if not regulation.allow_offsetting:
            continue

        original_remedial_cost = regulation.remedial_cost.get()

        if offsetting_cost >= original_remedial_cost:
            continue

        profile = regulation.profile

        # the remedial units from the LP represent offsets since
        # the remedial cost was truncated to the offsetting cost
        offsetting_units = profile.get_remedial_units(idx)

        if offsetting_units <= 0.:
            continue

        # cap aggregate offsets by the per-vessel offset threshold, when one applies
        aggregate_cap = _compute_aggregate_offset_cap(regulation, vessels, multipliers, idx)
        apply_offset_cap = aggregate_cap is not None
        if apply_offset_cap:
            offsetting_units = min(offsetting_units, aggregate_cap)

        offsetting_expenses = offsetting_units * offsetting_cost

        # store offsetting results on policy profile
        profile.set_offsetting_units(idx, offsetting_units)
        profile.set_offsetting_expenses(idx, offsetting_expenses)

        # reclassify remedial units and expenses as offsets
        profile.add_remedial_units(idx, -offsetting_units)
        profile.add_remedial_expenses(idx, -offsetting_expenses)

        # reclassify per-vessel remedial units as offsets
        _reclassify_vessel_policy_units(regulation, vessels, multipliers, idx,
                                        get_units, add_units,
                                        apply_offset_cap=apply_offset_cap)


def _calculate_levy_offsetting(levies: dict[str, Levy],
                               offsetting_cost: float,
                               vessels: dict[str, Vessel],
                               multipliers: dict[str, float],
                               idx: int) -> None:
    """
    Reclassify levy payments as offsets for levies where offsetting is cheaper.

    Parameters
    ----------
    levies
        All levies in the simulation.
    offsetting_cost
        The global offsetting cost in USD/ton emission.
    vessels
        All vessels in the simulation.
    multipliers
        Mapping from vessel name to fleet multiplier.
    idx
        Current time-step index.
    """

    get_units = lambda profile, policy_name: profile.get_levy_units(policy_name, idx)
    add_units = lambda profile, policy_name, delta: profile.add_levy_units(policy_name, idx, delta)

    for levy in levies.values():

        if not levy.is_active():
            continue

        if not levy.allow_offsetting:
            continue

        # offsetting only applies to penalty and both schemes
        if levy.scheme not in (LevySchemeID.PENALTY, LevySchemeID.BOTH):
            continue

        original_level = levy.level.get()

        if offsetting_cost >= original_level:
            continue

        profile = levy.profile

        # the LP was solved with the truncated level (= offsetting_cost)
        # so the collected amount represents offsetting expenses
        collected = profile.get_collected(idx)

        if collected <= 0.:
            continue

        offsetting_units = divide_nonzero(collected, offsetting_cost)

        # store offsetting results on policy profile
        profile.set_offsetting_units(idx, offsetting_units)
        profile.set_offsetting_expenses(idx, collected)

        # reclassify collected levy as offset payment
        profile.set_collected(idx, 0.)

        # reclassify per-vessel levy units as offsets
        _reclassify_vessel_policy_units(levy, vessels, multipliers, idx,
                                        get_units, add_units)


def _compute_aggregate_offset_cap(regulation: Regulation, vessels: dict[str, Vessel],
                                  multipliers: dict[str, float], idx: int) -> float | None:
    """
    Compute the fleet-level aggregate offset cap from per-vessel max_offset_rhs.

    Returns None if the regulation has no offset threshold (no cap applies).

    Parameters
    ----------
    regulation
        The regulation whose per-vessel offset caps are aggregated.
    vessels
        All vessels in the simulation.
    multipliers
        Mapping from vessel name to fleet multiplier.
    idx
        Current time-step index.
    """

    if regulation.get_effective_offset_threshold() is None:
        return None

    profile = regulation.profile

    total = 0.
    for vessel_name, _ in _policed_vessels(regulation, vessels, multipliers):
        total += profile.get_max_offset_rhs(vessel_name, idx) * multipliers[vessel_name]

    return total


def _reclassify_vessel_policy_units(policy: Regulation | Levy,
                                    vessels: dict[str, Vessel],
                                    multipliers: dict[str, float], idx: int,
                                    get_units: Callable,
                                    add_units: Callable,
                                    apply_offset_cap: bool = False) -> None:
    """
    Reclassify per-vessel policy units as offsets on vessel profiles.

    Per-vessel units were tracked during LP transfer. When a policy's
    compliance costs are reclassified as offsets at the policy level, the
    corresponding per-vessel units become per-vessel offsets.

    For regulations with an OffsetThreshold, the per-vessel offset amount
    is capped by the max_offset_rhs stored on the regulation profile.

    Parameters
    ----------
    policy
        The regulation or levy whose units are being reclassified.
    vessels
        All vessels in the simulation.
    multipliers
        Mapping from vessel name to fleet multiplier.
    idx
        Current time-step index.
    get_units
        Callable(profile, policy_name) returning the per-vessel units at the current step.
    add_units
        Callable(profile, policy_name, delta) to adjust the per-vessel units at the current step.
    apply_offset_cap
        When True, cap each vessel's offset by the per-vessel max_offset_rhs read from
        the policy profile. Only regulations with an offset threshold set this.
    """

    policy_name = policy.get_name()

    for vessel_name, vessel in _policed_vessels(policy, vessels, multipliers):
        profile = vessel.profile
        units = get_units(profile, policy_name)

        if units <= 0.:
            continue

        # apply per-vessel offset cap from offset threshold
        if apply_offset_cap:
            max_offset = policy.profile.get_max_offset_rhs(vessel_name, idx)
            units = min(units, max_offset)

            if units <= 0.:
                continue

        profile.add_offset(units, idx)
        add_units(profile, policy_name, -units)


def _build_multiplier_map(fleets: dict[str, Fleet], idx: int) -> dict[str, float]:
    """
    Build a mapping from vessel name to its fleet multiplier at the current time step.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    idx
        Current time-step index.

    Returns
    -------
    dict[str, float]
        Mapping from vessel name to fleet multiplier.
    """
    multipliers = {}
    for fleet in fleets.values():
        expectation = fleet.expectation

        for vessel in fleet.get_vessels():
            vessel_name = vessel.get_name()
            multiplier = expectation.get_existing_multipliers(vessel_name, idx)

            if multiplier <= 0.:
                continue

            multipliers[vessel_name] = multiplier

    return multipliers


def _policed_vessels(policy: Regulation | Levy,
                     vessels: dict[str, Vessel],
                     multipliers: dict[str, float]) -> Iterator[tuple[str, Vessel]]:
    """
    Yield (vessel_name, vessel) for vessels this policy polices that have a fleet multiplier.

    Parameters
    ----------
    policy
        The regulation or levy doing the policing.
    vessels
        All vessels in the simulation.
    multipliers
        Mapping from vessel name to fleet multiplier.
    """

    for vessel_name, vessel in vessels.items():

        if not policy.vessel_is_policed(vessel_name):
            continue

        if vessel_name not in multipliers:
            continue

        yield vessel_name, vessel
