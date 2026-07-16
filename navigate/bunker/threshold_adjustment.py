# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

from navigate.bunker.constraints.regulation_flexibility import update_flexibility_regulation_threshold_constraints
from navigate.bunker.constraints.regulation_helpers import get_regulation_vessel_threshold
from navigate.bunker.constraints.regulation_individual import update_individual_regulation_threshold_constraints
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
        m = alg.regulation_measure.get((r, v), 0.)

        offset_threshold, original_threshold = _get_offset_threshold_params(alg, regulation, v)
        adjusted_threshold = _compute_vessel_adjusted_threshold(
            measure, emissions, energy, m, offset_threshold, original_threshold)
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
            # compliant — store original shared threshold as adjusted.
            # For FLEXIBLE, all vessels share the same threshold value.
            original_threshold = get_regulation_vessel_threshold(alg, regulation,
                                                                 next(iter(alg.vessels)))
            alg.adjusted_shared_thresholds[r] = original_threshold
            for v in alg.vessels:
                if regulation.vessel_is_policed(v):
                    alg.adjusted_vessel_thresholds[(r, v)] = get_regulation_vessel_threshold(
                        alg, regulation, v)
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
                m = 0.
            elif measure in (RegulationMeasureID.TRANSPORT, RegulationMeasureID.TRANSPORT_NOMINAL):
                m = alg.regulation_measure[(r, v)]
                total_measure += m * multiplier
                energy = 0.
            else:
                energy = 0.
                m = 0.

            # store per-vessel adjusted threshold, reusing already-fetched values
            offset_threshold, original_threshold = _get_offset_threshold_params(alg, regulation, v)
            alg.adjusted_vessel_thresholds[(r, v)] = _compute_vessel_adjusted_threshold(
                measure, emissions, energy, m, offset_threshold, original_threshold)

        # compute fleet-level adjusted shared threshold (with tolerance)
        fleet_offset_threshold_attr = _get_effective_offset_threshold_attr(alg, regulation)
        fleet_offset_threshold = fleet_offset_threshold_attr.get() if fleet_offset_threshold_attr is not None else None
        fleet_original_threshold = get_regulation_vessel_threshold(alg, regulation, next(iter(alg.vessels)))
        alg.adjusted_shared_thresholds[r] = _compute_vessel_adjusted_threshold(
            measure, total_emissions, total_energy, total_measure,
            fleet_offset_threshold, fleet_original_threshold)

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


def _get_effective_offset_threshold_attr(alg, regulation):
    """Return the effective offset threshold attribute if offsetting applies, else None."""

    if not alg.offsetting_enabled or alg.offsetting_cost is None:
        return None

    if not regulation.allow_offsetting:
        return None

    remedial_cost = regulation.remedial_cost.get()
    if alg.offsetting_cost >= remedial_cost:
        return None

    return regulation.get_effective_offset_threshold()


def _get_offset_threshold_params(alg, regulation, vessel_name):
    """Return (offset_threshold_value, original_threshold_value) for a vessel.

    Returns (None, 0.) if offsetting does not apply.
    """

    offset_threshold_attr = _get_effective_offset_threshold_attr(alg, regulation)
    if offset_threshold_attr is None:
        return None, 0.

    return offset_threshold_attr.get(), get_regulation_vessel_threshold(alg, regulation, vessel_name)


def _compute_vessel_adjusted_threshold(measure, emissions, energy, transport_measure,
                                       offset_threshold=None, original_threshold=0.):
    """Compute the adjusted threshold for a vessel from its actual emissions.

    When an offset threshold is provided, the adjusted threshold is capped at the offset
    floor level instead of being set to the actual emissions.  This ensures that only the
    non-offsettable portion of non-compliance triggers threshold relaxation.

    A small relative tolerance is added so that the constraint remains
    non-binding after fair-share redistribution in the re-solve.
    """

    if measure == RegulationMeasureID.ABSOLUTE:
        actual = emissions
    elif measure == RegulationMeasureID.INTENSITY:
        actual = divide_nonzero(emissions, energy / TON_TO_KG)
    else:
        actual = divide_nonzero(emissions, transport_measure)

    if offset_threshold is not None and actual > offset_threshold:
        threshold = max(offset_threshold, original_threshold)
    else:
        threshold = actual

    return threshold * (1. + _THRESHOLD_TOLERANCE)


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
                    m = alg.regulation_measure[(r, v)]
                    new_rhs = adjusted_threshold * m

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
                    rhs_v = adjusted_threshold
                else:
                    m = alg.regulation_measure[(r, v)]
                    rhs_v = adjusted_threshold * m

                alg.regulation_rhs_flexibility[key] = rhs_v
                total_rhs += rhs_v * alg.multipliers[v]

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

        # FLEXIBLE schemes calibrate to the fleet-aggregate intensity so the re-solved
        # constraint dual carries cross-vessel cost differentiation (dirty vessels are
        # net payers, clean vessels net receivers). INDIVIDUAL schemes are calibrated
        # to each vessel's own threshold.
        flexible = regulation.scheme == RegulationSchemeID.FLEXIBLE
        shared_threshold = alg.adjusted_shared_thresholds.get(r) if flexible else None

        for v in alg.vessels:
            key = (r, v)

            if key not in alg.adjusted_vessel_thresholds:
                continue

            adjusted_threshold = shared_threshold if flexible else alg.adjusted_vessel_thresholds[key]

            # update the regulation spend coefficients with the adjusted threshold
            for c in alg.converters[v]:
                for f in alg.converter_fuels[v][c]:
                    coeff_key = (v, c, f, r)
                    ef = alg.regulation_emission_factor[coeff_key]
                    lhv = alg.effective_lhv[(v, c, f)]
                    alg.regulation_spend_coefficient[coeff_key] = ef - adjusted_threshold / TON_TO_KG * lhv

            # update shore power coefficients
            route = alg.vessels[v].route
            ports = route.ports
            for p, _port in enumerate(ports):
                if (v, p, r) in alg.shore_power_regulation_coeff:
                    sp_ef = alg.shore_power_regulation_ef.get((v, p, r), 0.)
                    alg.shore_power_regulation_coeff[(v, p, r)] = sp_ef - adjusted_threshold / TON_TO_KG * 1.0

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
