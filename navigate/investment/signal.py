# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.enum_ import RegulationSchemeID
from navigate.core.misc import YEAR


def update_vessel_scarcity_beliefs(fleets: dict, timeline: np.ndarray, idx: int) -> None:
    """
    Update per-leg shadow-price beliefs for every vessel.

    Each (energy-demand-type, leg) array of LP duals is smoothed independently
    via exponential moving average, in place on the expectation's per-leg
    belief arrays. Two parallel belief sets are maintained: a slower one for
    technology decisions (amortised over `technology_horizon`) and a faster
    one for operational speed management (`speed_horizon`).

    Per-leg smoothing preserves the LP's directional structure across legs
    (where shadow prices may differ in sign and magnitude) while damping
    year-to-year volatility at each leg individually.

    Parameters
    ----------
    fleets
        Mapping of fleet id to fleet object.
    timeline
        Simulation timeline in days.
    idx
        Current outer time-step index.
    """

    for fleet in fleets.values():

        tech_horizon = fleet.technology_horizon.get()
        speed_horizon = fleet.speed_horizon.get()

        alpha_tech = _derive_smoothing_alpha(idx, tech_horizon, timeline)
        alpha_speed = _derive_smoothing_alpha(idx, speed_horizon, timeline)

        for vessel in fleet.get_vessels():
            expectation = vessel.expectation

            raw_pi_sea = expectation.get_energy_conservation_pi_sea()
            raw_pi_port = expectation.get_energy_conservation_pi_port()

            _smooth_pi_dict(raw_pi_sea, expectation.get_belief_pi_sea_technology(), alpha_tech, idx)
            _smooth_pi_dict(raw_pi_port, expectation.get_belief_pi_port_technology(), alpha_tech, idx)
            _smooth_pi_dict(raw_pi_sea, expectation.get_belief_pi_sea_speed(), alpha_speed, idx)
            _smooth_pi_dict(raw_pi_port, expectation.get_belief_pi_port_speed(), alpha_speed, idx)


def update_regulation_flexibility_beliefs(regulations: dict, vessels: dict, timeline: np.ndarray, idx: int) -> None:
    """
    Update the flexibility cost belief of every flexible regulation and apply the expected policy expenses.

    The raw flexibility cost (the shadow price of the regulation threshold flexibility constraint) is
    smoothed via exponential moving average, in place on the regulation expectation's belief array.
    This prevents small changes in future fuel availability from translating into expectations of
    large flexibility-cost differences.

    The expected flexibility expenses of each policed vessel are then applied as the net flexibility
    units (flexibility units minus surplus units, stored raw by the bunker transfer) valued at the
    smoothed cost. Surplus revenue is implicitly valued at the same smoothed cost through the net units.

    Parameters
    ----------
    regulations
        Mapping of regulation name to regulation object.
    vessels
        Mapping of vessel name to vessel object.
    timeline
        Simulation timeline in days.
    idx
        Current outer time-step index.
    """

    for regulation in regulations.values():

        if regulation.scheme != RegulationSchemeID.FLEXIBLE:
            continue

        flexibility_horizon = regulation.flexibility_horizon.get()
        alpha = _derive_smoothing_alpha(idx, flexibility_horizon, timeline)

        expectation = regulation.expectation
        raw_cost = expectation.get_flexibility_cost()
        belief = expectation.get_belief_flexibility_cost()

        _update_belief_path(raw_cost, belief, alpha, idx)

        for vessel_name, vessel in vessels.items():

            if not regulation.vessel_is_policed(vessel_name):
                continue

            net_units = expectation.get_vessel_net_flexibility_units(vessel_name)
            vessel.expectation.add_policy_expenses_path(idx, net_units[idx:] * belief[idx:])


def record_investment_signals(fleets: dict, idx: int) -> None:
    """
    Store a per-vessel scalar proxy of the investment-signal magnitude.

    Collapses the multi-key smoothed energy-conservation duals into one
    energy-weighted average per vessel (USD/GJ), separately for the technology-
    and speed-horizon beliefs, and writes them to the vessel profile for output.

    Parameters
    ----------
    fleets
        Mapping of fleet id to fleet object.
    idx
        Current outer time-step index.
    """

    for fleet in fleets.values():
        for vessel in fleet.get_vessels():
            expectation = vessel.expectation

            rhs_sea = expectation.get_energy_conservation_rhs_sea()
            rhs_port = expectation.get_energy_conservation_rhs_port()

            signal_technology = _energy_weighted_signal(expectation.get_belief_pi_sea_technology(),
                                                        expectation.get_belief_pi_port_technology(),
                                                        rhs_sea, rhs_port, idx)
            signal_speed = _energy_weighted_signal(expectation.get_belief_pi_sea_speed(),
                                                   expectation.get_belief_pi_port_speed(),
                                                   rhs_sea, rhs_port, idx)

            profile = vessel.profile
            profile.set_investment_signal_technology(idx, signal_technology)
            profile.set_investment_signal_speed(idx, signal_speed)


def _energy_weighted_signal(belief_sea: dict,
                            belief_port: dict,
                            rhs_sea: dict,
                            rhs_port: dict,
                            idx: int,
                            ) -> float:
    """
    Collapse per-(energy-type, leg) belief duals into one energy-weighted scalar.

    Each leg/port dual at `idx` is weighted by its energy-conservation RHS (the
    energy demand the dual prices), combining sea and port contributions. The
    result is the marginal value of energy the vessel faces, in USD/GJ.

    Parameters
    ----------
    belief_sea
        Smoothed sea duals, keyed by energy-demand-type, valued by per-leg arrays.
    belief_port
        Smoothed port duals, same structure indexed by port.
    rhs_sea
        Energy-conservation RHS for sea, same structure as `belief_sea`.
    rhs_port
        Energy-conservation RHS for port, same structure as `belief_port`.
    idx
        Current outer time-step index.

    Returns
    -------
    Energy-weighted average dual at `idx`, or ``np.nan`` when there is no demand.
    """

    weighted_sum = 0.
    weight_total = 0.

    for belief_dict, rhs_dict in ((belief_sea, rhs_sea), (belief_port, rhs_port)):
        for energy_id, belief_legs in belief_dict.items():
            rhs_legs = rhs_dict[energy_id]
            for belief_leg, rhs_leg in zip(belief_legs, rhs_legs):
                weight = rhs_leg[idx]
                weighted_sum += belief_leg[idx] * weight
                weight_total += weight

    if weight_total <= 0.:
        return np.nan

    return weighted_sum / weight_total


def _smooth_pi_dict(raw_dict: dict,
                    belief_dict: dict,
                    alpha: float,
                    idx: int,
                    ) -> None:
    """
    Apply per-leg EMA smoothing to every array in a pi dict, in place.

    Parameters
    ----------
    raw_dict
        Raw LP-dual dict keyed by energy-demand-type, valued by per-leg arrays.
    belief_dict
        Belief dict of the same shape; modified in place.
    alpha
        EMA weight on the new raw projection. ``alpha = 1`` trusts the latest
        projection fully; ``alpha = 0`` ignores it.
    idx
        Current outer time-step index. Only ``s >= idx`` are updated.
    """

    for energy_id, raw_legs in raw_dict.items():
        belief_legs = belief_dict[energy_id]
        for raw_leg, belief_leg in zip(raw_legs, belief_legs):
            _update_belief_path(raw_leg, belief_leg, alpha, idx)


def _update_belief_path(raw_path: np.ndarray,
                        belief: np.ndarray,
                        alpha: float | np.ndarray,
                        idx: int
                        ) -> None:
    """
    Calendar-date belief update for a single per-leg path.

    Match is by calendar index, not look-ahead position, so a given future
    year's belief evolves coherently as successive projections refine it. On
    the first call the prior belief is all-zero, so the belief bootstraps to
    the raw path; subsequent calls blend the new projection with the prior.

    Parameters
    ----------
    raw_path
        Raw forward path from the latest LP solve. Values at ``s < idx`` are
        ignored.
    belief
        Previous belief path. Same length as ``raw_path``. Modified in place.
    alpha
        Smoothing weight. ``alpha = 1`` trusts the new projection fully;
        ``alpha = 0`` ignores it entirely.
    idx
        Current outer time-step index. Only ``s >= idx`` are updated.
    """

    forward_slice = np.s_[idx:]
    belief_forward = belief[forward_slice]
    raw_forward = raw_path[forward_slice]

    if (belief_forward == 0.).all():
        # bootstrap: no prior evidence, adopt the raw path directly.
        belief[forward_slice] = raw_forward
    else:
        # exponential smoothing: blend new projection with the prior belief.
        belief[forward_slice] = alpha * raw_forward + (1. - alpha) * belief_forward


def _derive_smoothing_alpha(idx: int,
                            decision_horizon_years: float,
                            timeline: np.ndarray,
                            ) -> float:
    """
    Derive the EMA smoothing parameter from the decision horizon.

    Shorter horizons give a larger alpha (more responsive). A 5-year
    horizon with 1-year steps gives alpha ~ 0.17; a 3-year horizon
    with 1-year steps gives alpha ~ 0.25.

    Parameters
    ----------
    idx
        Current outer time-step index.
    decision_horizon_years
        Characteristic decision horizon (years).
    timeline
        Simulation timeline in days.

    Returns
    -------
    Smoothing parameter.
    """

    horizon_idx = timeline.size - 1
    if idx > horizon_idx:
        return 1.

    outer_step_years = (timeline[idx] - timeline[idx - 1]) / YEAR
    if outer_step_years <= 0.:
        return 1.

    return 1. / (1. + decision_horizon_years / outer_step_years)
