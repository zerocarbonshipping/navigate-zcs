# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Guardrail: no-incentive scenario.

Without any GHG pricing mechanism, the newbuild choice model must allocate
nearly the whole fleet to oil and methane vessels, and the efficiency levers
(technology uptake, operational speed, the resulting energy savings) must
stay approximately at their initial values. The domain contract lives in
simulations/no_incentive/BEHAVIOR.md.
"""
from pathlib import Path

import numpy as np
import pytest

from navigate.core.enum_ import EnergyDemandTypeID, FuelTypeID
from navigate.testing.simulation import check_invariants, run_simulation

SIMULATIONS_DIR = Path(__file__).resolve().parent / "simulations"

# Absolute tolerance on market shares: vessel counts are lumpy at fleet scale
# and the nested-logit allocation carries small numerical noise from the
# LP-coupled fuel pricing. 0.5 percentage points absorbs both without hiding
# a share that is off by a factor of two.
EPS_SHARE = 0.005

# Share ceilings, enforced at every time step — see BEHAVIOR.md.
MAX_METHANOL_SHARE = 0.10
MAX_AMMONIA_SHARE = 0.05
MIN_OIL_METHANE_SHARE = 1. - MAX_METHANOL_SHARE - MAX_AMMONIA_SHARE

# Drift bands for the efficiency levers, each measured against
# the series' initial value; the saving and uptake bands are absolute
# fractions, the speed band relative — see BEHAVIOR.md.
MAX_SAVING_DRIFT = 0.05
MAX_UPTAKE_DRIFT = 0.10
MAX_SPEED_DRIFT_REL = 0.10


@pytest.fixture(scope="module")
def manager():
    return run_simulation(SIMULATIONS_DIR / "no_incentive")


@pytest.fixture(scope="module")
def fleet(manager):
    return manager.nodes.fleets["container_15000_teu"]


@pytest.fixture(scope="module")
def market_shares(fleet):
    """Fleet-wide market share series per fuel type (vessel counts, every
    time step)."""
    fuel_types = {vessel.name: FuelTypeID(vessel.fuel_type) for vessel in fleet.get_vessels()}
    existing = fleet.profile.get_existing_vessels()

    total = np.sum(list(existing.values()), axis=0)
    assert np.all(total > 0.), "Deck validity: the fleet must never be empty"
    shares = {fuel_type: np.zeros_like(total, dtype=float) for fuel_type in fuel_types.values()}
    for name, counts in existing.items():
        shares[fuel_types[name]] += np.asarray(counts) / total
    return shares


@pytest.fixture(scope="module")
def technology_uptake(fleet):
    """Fleet-wide uptake series per technology (the 'Fleet' line of the
    technology_uptake plot)."""
    assert fleet.technologies, "Deck validity: the fleet must carry technologies"

    # deck validity, stricter than the getter's fall-back to 0: a step with
    # no existing vessels would make the stability claim vacuous
    existing = fleet.profile.get_existing_vessels()
    assert np.all(np.sum(list(existing.values()), axis=0) > 0.)

    uptake = fleet.profile.get_fleet_technology_uptake()
    # every configured technology must be measured — a technology silently
    # missing from the profile must not pass by omission
    assert set(uptake) == {technology.get_name() for technology in fleet.technologies}
    return uptake


@pytest.mark.slow
class TestNoIncentive:

    def test_invariants(self, manager):
        check_invariants(manager)

    def test_supply_never_binding(self, manager):
        """Deck validity: supply must be ample so the discrete choice model,
        not a supply constraint, is what keeps the alternative-fuel shares
        small (see BEHAVIOR.md, Mechanism isolated)."""
        for name, producer in manager.nodes.producers.items():
            development = producer.profile.get_development()
            maximum = producer.profile.get_maximum_development()
            assert np.all(development <= 0.5 * maximum), \
                f"Producer '{name}' approaches its development constraint"

    def test_methanol_share_marginal(self, market_shares):
        assert np.all(market_shares[FuelTypeID.METHANOL] <= MAX_METHANOL_SHARE + EPS_SHARE)

    def test_ammonia_share_marginal(self, market_shares):
        assert np.all(market_shares[FuelTypeID.AMMONIA] <= MAX_AMMONIA_SHARE + EPS_SHARE)

    def test_oil_and_methane_dominate(self, market_shares):
        dominant = market_shares[FuelTypeID.OIL] + market_shares[FuelTypeID.METHANE]
        assert np.all(dominant >= MIN_OIL_METHANE_SHARE - EPS_SHARE)

    def test_global_savings_stable(self, manager):
        """The series of the global_energy_saving plot must all stay at their
        initial values: with no incentive, nothing should drive additional
        energy-saving effort."""
        profile = manager.profile
        savings = {
            "propulsion": profile.get_saving(EnergyDemandTypeID.PROPULSION),
            "electrical": profile.get_saving(EnergyDemandTypeID.ELECTRICAL),
            "heat": profile.get_saving(EnergyDemandTypeID.HEAT),
            "technology": profile.get_technology_energy_intensity_saving(),
            "operational": profile.get_operational_energy_intensity_saving(),
            "total": profile.get_energy_intensity_saving(),
        }

        for name, saving in savings.items():
            drift = np.abs(saving - saving[0]).max()
            assert drift <= MAX_SAVING_DRIFT, \
                f"Global {name} energy saving drifts {drift:.3f} from its initial value {saving[0]:.3f}"

    def test_technology_uptake_stable(self, technology_uptake):
        """Fleet-wide uptake of each efficiency technology must stay at its
        initial value: with no incentive, no additional adoption."""
        for name, uptake in technology_uptake.items():
            drift = np.abs(uptake - uptake[0]).max()
            assert drift <= MAX_UPTAKE_DRIFT, \
                f"Uptake of '{name}' drifts {drift:.3f} from its initial value {uptake[0]:.3f}"

    def test_speed_stable(self, fleet):
        """Fleet average speed must stay at its initial value: with no
        incentive, no persistent speed-up or slow-down. The first step holds
        no realized speed (NaN), so the baseline is the first computed step."""
        speed = fleet.profile.get_actual_speed()

        baseline = speed[1]
        assert np.isfinite(baseline)
        assert np.all(np.abs(speed[1:] - baseline) <= MAX_SPEED_DRIFT_REL * baseline)
