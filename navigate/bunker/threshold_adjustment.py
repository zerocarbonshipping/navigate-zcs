# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

from navigate.bunker.constraints.regulation_flexibility import update_flexibility_regulation_threshold_constraints
from navigate.bunker.constraints.regulation_individual import update_individual_regulation_threshold_constraints
from navigate.bunker.constraints.regulation_terms import get_regulation_vessel_threshold
from navigate.bunker.utils import get_converters
from navigate.core.enum_ import RegulationMeasureID, RegulationSchemeID
from navigate.core.unit import TON_TO_KG
from navigate.util import divide_nonzero

# Relative tolerance applied to adjusted thresholds to ensure non-binding constraints
# in the re-solve.  Without this margin, fair-share redistribution or solver numerics
# can push emissions fractionally above the exact-match threshold, reactivating the
# remedial factor.  1e-4 (0.01 %) is large enough to absorb these perturbations while
# being economically negligible.
_THRESHOLD_TOLERANCE = 1e-4


def adjust_regulation_thresholds(alg: BunkerAlgorithm) -> bool:
    """
    Perform threshold adjustment for regulations that have the AllowThresholdAdjustment flag enabled.

    After the initial solve, for any regulation with non-compliance (remedial factor > 0), compute
    the adjusted threshold that would make the regulation compliant at the current cost/supply levels.
    Updates the LP constraints with adjusted thresholds but does not re-solve — the caller is
    responsible for running the fair-share solve loop again if this returns True.

    Parameters
    ----------
    alg
        The algorithm instance.

    Returns
    -------
    bool
        True if thresholds were adjusted and the LP needs to be re-solved, False otherwise.
    """

    # check if any active regulation requires threshold adjustment
    adjustable_regulations = {r: reg for r, reg in alg.active_regulations.items()
                              if reg.allow_threshold_adjustment}

    if not adjustable_regulations:
        return False

    needs_resolve = False
    has_intensity = False

    # individual regulations
    for (r, v), remedial_factor in alg.remedial_factor_individual.items():

        if r not in adjustable_regulations:
            continue

        regulation = alg.regulations[r]
        if regulation.scheme != RegulationSchemeID.INDIVIDUAL:
            continue

        # compliant — store original threshold as adjusted
        if remedial_factor.X <= 0.:
            alg.adjusted_vessel_thresholds[(r, v)] = get_regulation_vessel_threshold(alg, regulation, v)
            continue

        measure = regulation.measure
        emissions = alg.regulation_emission_terms[(r, v)].getValue()
        energy = alg.regulation_energy_terms[(r, v)].getValue() if measure == RegulationMeasureID.INTENSITY else 0.
        vessel_measure = alg.regulation_measure.get((r, v), 0.)

        adjusted_threshold = _compute_vessel_adjusted_threshold(measure, emissions, energy, vessel_measure)
        if measure == RegulationMeasureID.INTENSITY:
            has_intensity = True

        alg.adjusted_vessel_thresholds[(r, v)] = adjusted_threshold
        needs_resolve = True

    # flexible regulations
    for r, remedial_factor in alg.remedial_factor_flexibility.items():

        if r not in adjustable_regulations:
            continue

        regulation = alg.regulations[r]
        if regulation.scheme != RegulationSchemeID.FLEXIBLE:
            continue

        if remedial_factor.X <= 0.:
            # compliant — nothing was adjusted: store the original per-vessel
            # thresholds and no fleet-level value, so downstream consumers fall
            # back to the per-vessel targets the initial build solved against
            alg.adjusted_vessel_thresholds.update(
                {(r, v): get_regulation_vessel_threshold(alg, regulation, v)
                 for v in alg.vessels if regulation.vessel_is_policed(v)})
            continue

        measure = regulation.measure

        # compute fleet-level adjusted shared threshold from total emissions/energy
        total_emissions = 0.
        total_energy = 0.
        total_measure = 0.
        for v in alg.vessels:
            if not regulation.vessel_is_policed(v):
                continue

            emissions = alg.regulation_emission_terms[(r, v)].getValue()
            multiplier = alg.multipliers[v]
            total_emissions += emissions * multiplier

            if measure == RegulationMeasureID.INTENSITY:
                energy = alg.regulation_energy_terms[(r, v)].getValue()
                total_energy += energy * multiplier
                has_intensity = True
                vessel_measure = 0.
            elif measure in (RegulationMeasureID.TRANSPORT, RegulationMeasureID.TRANSPORT_NOMINAL):
                vessel_measure = alg.regulation_measure[(r, v)]
                total_measure += vessel_measure * multiplier
                energy = 0.
            else:
                energy = 0.
                vessel_measure = 0.

            # store per-vessel adjusted threshold, reusing already-fetched values
            alg.adjusted_vessel_thresholds[(r, v)] = _compute_vessel_adjusted_threshold(
                measure, emissions, energy, vessel_measure)

        # compute fleet-level adjusted shared threshold (with tolerance)
        alg.adjusted_shared_thresholds[r] = _compute_vessel_adjusted_threshold(
            measure, total_emissions, total_energy, total_measure)

        needs_resolve = True

    if not needs_resolve:
        return False

    # update LP constraints with adjusted thresholds
    if has_intensity:
        # for INTENSITY regulations, the threshold is embedded in the constraint coefficients,
        # so we need to rebuild coefficients and constraints
        _rebuild_regulation_constraints_for_adjustment(alg, adjustable_regulations)
    else:
        # for non-INTENSITY regulations, we can simply update the constraint RHS
        _update_regulation_rhs_for_adjustment(alg, adjustable_regulations)

    return True


def _compute_vessel_adjusted_threshold(measure, emissions, energy, measure_value):
    """Compute the adjusted threshold for a vessel from its actual emissions.

    A small relative tolerance is added so that the constraint remains
    non-binding after fair-share redistribution in the re-solve.
    """

    if measure == RegulationMeasureID.ABSOLUTE:
        actual = emissions
    elif measure == RegulationMeasureID.INTENSITY:
        actual = divide_nonzero(emissions, energy / TON_TO_KG)
    else:
        actual = divide_nonzero(emissions, measure_value)

    return actual * (1. + _THRESHOLD_TOLERANCE)


def _update_regulation_rhs_for_adjustment(alg: BunkerAlgorithm, adjustable_regulations: dict) -> None:
    """
    Update constraint RHS values for non-INTENSITY regulation threshold adjustments.

    Parameters
    ----------
    alg
        The algorithm instance.
    adjustable_regulations
        Dictionary of regulations that have threshold adjustment enabled.
    """

    for r, regulation in adjustable_regulations.items():

        measure = regulation.measure
        if measure == RegulationMeasureID.INTENSITY:
            continue

        if regulation.scheme == RegulationSchemeID.INDIVIDUAL:

            for v in alg.vessels:
                key = (r, v)
                if key not in alg.regulation_threshold_individual:
                    continue
                if key not in alg.adjusted_vessel_thresholds:
                    continue

                adjusted_threshold = alg.adjusted_vessel_thresholds[key]

                if measure == RegulationMeasureID.ABSOLUTE:
                    new_rhs = adjusted_threshold
                else:
                    vessel_measure = alg.regulation_measure[(r, v)]
                    new_rhs = adjusted_threshold * vessel_measure

                alg.regulation_rhs_individual[key] = new_rhs
                alg.regulation_threshold_individual[key].RHS = new_rhs

        elif regulation.scheme == RegulationSchemeID.FLEXIBLE:

            if r not in alg.regulation_threshold_flexibility:
                continue

            total_rhs = 0.
            for v in alg.vessels:
                key = (r, v)

                if not regulation.vessel_is_policed(v):
                    continue

                if key not in alg.adjusted_vessel_thresholds:
                    continue

                adjusted_threshold = alg.adjusted_vessel_thresholds[key]

                if measure == RegulationMeasureID.ABSOLUTE:
                    vessel_rhs = adjusted_threshold
                else:
                    vessel_measure = alg.regulation_measure[(r, v)]
                    vessel_rhs = adjusted_threshold * vessel_measure

                alg.regulation_rhs_flexibility[key] = vessel_rhs
                total_rhs += vessel_rhs * alg.multipliers[v]

            alg.regulation_total_rhs_flexibility[r] = total_rhs
            alg.regulation_threshold_flexibility[r].RHS = total_rhs


def _rebuild_regulation_constraints_for_adjustment(alg: BunkerAlgorithm, adjustable_regulations: dict) -> None:
    """
    Rebuild regulation constraints when INTENSITY regulations need threshold adjustment.

    Parameters
    ----------
    alg
        The algorithm instance.
    adjustable_regulations
        Dictionary of regulations that have threshold adjustment enabled.
    """

    # update non-INTENSITY constraints via RHS
    _update_regulation_rhs_for_adjustment(alg, adjustable_regulations)

    # for INTENSITY regulations, rebuild the regulation spend coefficients
    # by temporarily storing adjusted thresholds and recomputing coefficients
    for r, regulation in adjustable_regulations.items():

        if regulation.measure != RegulationMeasureID.INTENSITY:
            continue

        # Adjusted FLEXIBLE schemes calibrate to the fleet-aggregate intensity so the
        # re-solved constraint dual carries cross-vessel cost differentiation (dirty
        # vessels are net payers, clean vessels net receivers). INDIVIDUAL schemes and
        # compliant FLEXIBLE schemes (no fleet-level adjusted value stored) are
        # calibrated to each vessel's own threshold.
        shared_threshold = (alg.adjusted_shared_thresholds.get(r)
                            if regulation.scheme == RegulationSchemeID.FLEXIBLE else None)

        for v, vessel in alg.vessels.items():
            key = (r, v)

            if key not in alg.adjusted_vessel_thresholds:
                continue

            adjusted_threshold = shared_threshold if shared_threshold is not None \
                else alg.adjusted_vessel_thresholds[key]

            # update the regulation spend coefficients with the adjusted threshold
            for c in get_converters(vessel):
                for f in alg.fuels_per_converter[v, c]:
                    coefficient_key = (v, c, f, r)
                    emission_factor = alg.regulation_emission_factor[coefficient_key]
                    effective_lhv = alg.effective_lhv[(v, c, f)]
                    alg.regulation_spend_coefficient[coefficient_key] = (
                        emission_factor - adjusted_threshold / TON_TO_KG * effective_lhv)

            # update shore power coefficients
            ports = vessel.route.ports
            for p, _port in enumerate(ports):
                if (v, p, r) in alg.shore_power_regulation_coefficient:
                    shore_power_emission_factor = alg.shore_power_regulation_emission_factor.get((v, p, r), 0.)
                    alg.shore_power_regulation_coefficient[(v, p, r)] = (
                        shore_power_emission_factor - adjusted_threshold / TON_TO_KG * 1.0)

    # rebuild the regulation threshold constraints (which remove and re-add).
    # Each function rebuilds all constraints of that scheme type, so call at most once per scheme.
    rebuild_individual = False
    rebuild_flexibility = False
    for _r, regulation in adjustable_regulations.items():
        if regulation.measure != RegulationMeasureID.INTENSITY:
            continue
        if regulation.scheme == RegulationSchemeID.INDIVIDUAL:
            rebuild_individual = True
        elif regulation.scheme == RegulationSchemeID.FLEXIBLE:
            rebuild_flexibility = True

    if rebuild_individual:
        update_individual_regulation_threshold_constraints(alg)
    if rebuild_flexibility:
        update_flexibility_regulation_threshold_constraints(alg)
