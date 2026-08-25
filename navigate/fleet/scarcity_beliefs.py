# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.util import derive_smoothing_alpha, update_belief_path


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

        alpha_tech = derive_smoothing_alpha(idx, tech_horizon, timeline)
        alpha_speed = derive_smoothing_alpha(idx, speed_horizon, timeline)

        for vessel in fleet.get_vessels():
            expectation = vessel.expectation

            raw_pi_sea = expectation.get_energy_conservation_pi_sea()
            raw_pi_port = expectation.get_energy_conservation_pi_port()

            _smooth_pi_dict(raw_pi_sea, expectation.get_belief_pi_sea_technology(), alpha_tech, idx)
            _smooth_pi_dict(raw_pi_port, expectation.get_belief_pi_port_technology(), alpha_tech, idx)
            _smooth_pi_dict(raw_pi_sea, expectation.get_belief_pi_sea_speed(), alpha_speed, idx)
            _smooth_pi_dict(raw_pi_port, expectation.get_belief_pi_port_speed(), alpha_speed, idx)


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
            update_belief_path(raw_leg, belief_leg, alpha, idx)
