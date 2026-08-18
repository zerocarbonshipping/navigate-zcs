# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for Fleet module-level helper functions."""
from unittest.mock import MagicMock

import numpy as np
import pytest

from navigate.asset import Increment
from navigate.core import Scalar
from navigate.core.enum_ import EnergyDemandTypeID
from navigate.core.id_ import FLEET, VESSEL
from navigate.core.misc import YEAR
from navigate.vessel.fleet import Fleet
from navigate.vessel.fleet import fleet_evolution
from navigate.vessel.fleet.fleet_conversion import reconcile_fuel_conversion_caps
from navigate.vessel.fleet.fleet_evolution import (
    calculate_modelled_newbuilds,
    calculate_modelled_uptake,
    calculate_orderbook_newbuilds,
)
from navigate.vessel.fleet.fleet_technology import (
    reconcile_newbuild_technology_caps,
    reconcile_retrofit_technology_caps,
    transfer_retrofit_uptake,
)
from navigate.vessel.fleet.fleet_utils import (
    calculate_increments,
    calculate_projected_multipliers,
    get_remaining_lifetime,
    is_retrofit_cycle,
    net_energy_from_raw,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_vessel(name):
    """Create a mock Vessel with minimal interface."""
    v = MagicMock()
    v.get_name.return_value = name
    v.get_type.return_value = VESSEL
    v._type = VESSEL
    v.is_type.side_effect = lambda t: t == VESSEL
    return v


# ---------------------------------------------------------------------------
# Module-level helper functions
# ---------------------------------------------------------------------------

class TestIsRetrofitCycle:
    """Test _is_retrofit_cycle standalone function."""

    def test_age_zero_not_retrofit(self):
        assert is_retrofit_cycle(0.0, 5.0, 1.0) is False

    def test_age_one_not_retrofit(self):
        assert is_retrofit_cycle(1.0, 5.0, 1.0) is False

    def test_age_five_is_retrofit(self):
        assert is_retrofit_cycle(5.0, 5.0, 1.0) is True

    def test_age_ten_is_retrofit(self):
        assert is_retrofit_cycle(10.0, 5.0, 1.0) is True

    def test_age_three_not_retrofit_freq_five(self):
        assert is_retrofit_cycle(3.0, 5.0, 1.0) is False

    def test_first_time_step_excluded(self):
        # age == time_step means vessel just entered, should not retrofit
        assert is_retrofit_cycle(1.0, 1.0, 1.0) is False


class TestCalculateProjectedMultipliers:
    """Test _calculate_projected_multipliers."""

    def test_constant_trade(self):
        trade = np.array([100., 100., 100.])
        result = calculate_projected_multipliers(50., trade)
        np.testing.assert_array_almost_equal(result, [50., 50., 50.])

    def test_doubling_trade(self):
        trade = np.array([100., 200.])
        result = calculate_projected_multipliers(10., trade)
        np.testing.assert_array_almost_equal(result, [10., 20.])

    def test_single_point(self):
        trade = np.array([50.])
        result = calculate_projected_multipliers(20., trade)
        np.testing.assert_array_almost_equal(result, [20.])


class TestCalculateIncrements:
    """Test _calculate_increments."""

    def test_equal_uptake(self):
        uptakes = np.array([0.5, 0.5])
        cargo_miles = np.array([100., 100.])
        result = calculate_increments(uptakes, cargo_miles, 1000.)
        np.testing.assert_array_almost_equal(result, [5., 5.])

    def test_unequal_cargo_miles(self):
        uptakes = np.array([1.0])
        cargo_miles = np.array([200.])
        result = calculate_increments(uptakes, cargo_miles, 1000.)
        np.testing.assert_array_almost_equal(result, [5.])

    def test_zero_trade_gap(self):
        uptakes = np.array([0.5, 0.5])
        cargo_miles = np.array([100., 100.])
        result = calculate_increments(uptakes, cargo_miles, 0.)
        np.testing.assert_array_almost_equal(result, [0., 0.])


class TestGetRemainingLifetime:
    """Test _get_remaining_lifetime."""

    def test_new_vessel(self):
        vessel = _make_vessel("v")
        vessel.lifetime = Scalar(25)
        assert get_remaining_lifetime(vessel, age=0.0, dt=1.0) == 24

    def test_old_vessel(self):
        vessel = _make_vessel("v")
        vessel.lifetime = Scalar(25)
        assert get_remaining_lifetime(vessel, age=24.0, dt=1.0) == 0

    def test_beyond_lifetime(self):
        vessel = _make_vessel("v")
        vessel.lifetime = Scalar(25)
        assert get_remaining_lifetime(vessel, age=30.0, dt=1.0) == 0


class TestNetEnergyFromRaw:
    """Test net_energy_from_raw."""

    def test_no_savings(self):
        raw = {EnergyDemandTypeID.PROPULSION: [100., 200.]}
        sav = {EnergyDemandTypeID.PROPULSION: [0., 0.]}
        result = net_energy_from_raw(raw, sav)
        assert result[EnergyDemandTypeID.PROPULSION] == pytest.approx([100., 200.])

    def test_half_savings(self):
        raw = {EnergyDemandTypeID.PROPULSION: [100., 200.]}
        sav = {EnergyDemandTypeID.PROPULSION: [0.5, 0.5]}
        result = net_energy_from_raw(raw, sav)
        assert result[EnergyDemandTypeID.PROPULSION] == pytest.approx([50., 100.])

    def test_full_savings(self):
        raw = {EnergyDemandTypeID.PROPULSION: [100.]}
        sav = {EnergyDemandTypeID.PROPULSION: [1.0]}
        result = net_energy_from_raw(raw, sav)
        assert result[EnergyDemandTypeID.PROPULSION] == pytest.approx([0.])

    def test_multiple_energy_types(self):
        raw = {
            EnergyDemandTypeID.PROPULSION: [100.],
            EnergyDemandTypeID.ELECTRICAL: [50.],
        }
        sav = {
            EnergyDemandTypeID.PROPULSION: [0.1],
            EnergyDemandTypeID.ELECTRICAL: [0.2],
        }
        result = net_energy_from_raw(raw, sav)
        assert result[EnergyDemandTypeID.PROPULSION] == pytest.approx([90.])
        assert result[EnergyDemandTypeID.ELECTRICAL] == pytest.approx([40.])


# ---------------------------------------------------------------------------
# Technology cap reconciliation (per-year flow caps)
# ---------------------------------------------------------------------------

def _make_technology(name: str):
    t = MagicMock()
    t.get_name.return_value = name
    return t


def _make_package(technologies):
    package = MagicMock()
    package.technologies = technologies
    return package


def _make_fleet_with_technologies(technology_names: list[str]) -> Fleet:
    """Bare Fleet stub with CAPEX-sorted cumulative-prefix packages for `technology_names`."""
    technologies = [_make_technology(n) for n in technology_names]
    packages = [_make_package(technologies[:i]) for i in range(len(technologies) + 1)]
    fleet = Fleet.__new__(Fleet)
    fleet.technology_packages = packages
    return fleet


# ---------------------------------------------------------------------------
# Fuel-conversion cap reconciliation
# ---------------------------------------------------------------------------

def _make_fleet_for_cap(pair_limits: dict[tuple[str, str], float] | None = None) -> Fleet:
    """
    Build a Fleet stub configured just for `reconcile_fuel_conversion_caps`. The cap is now a
    fraction-of-fleet-per-year per (from, to) pair; missing pairs default to Scalar(1.) (unlimited).
    """
    fleet = Fleet.__new__(Fleet)
    fleet.fuel_conversion_limit = {pair: Scalar(limit) for pair, limit in (pair_limits or {}).items()}
    return fleet


def _proposals(items: dict[tuple[str, int], dict[str, float]]) -> dict:
    """items maps (name_from, increment_idx) -> {name_to: count}; wraps into the proposal dict shape."""
    return {key: {'age': 0., 'dt': 1., 'conversions': dict(conv), 'costs_per_vessel': {}}
            for key, conv in items.items()}


def _conv_total(proposals: dict, pair: tuple[str, str]) -> float:
    return sum(p['conversions'].get(pair[1], 0.) for (name_from, _increment_idx), p in proposals.items()
               if name_from == pair[0])


class TestReconcileFuelConversionCaps:
    """Test `_reconcile_fuel_conversion_caps` — the per-pair flow cap."""

    def test_no_pair_limit_no_op(self):
        # All limits at default 1.0 (100% of fleet/yr) ⇒ proposals untouched.
        fleet = _make_fleet_for_cap(pair_limits={('x', 'y'): 1.0, ('x', 'z'): 1.0})
        proposals = _proposals({('x', 0): {'y': 3., 'z': 2.}})
        reconcile_fuel_conversion_caps(fleet, proposals, time_step=YEAR, existing_total=100.)
        np.testing.assert_almost_equal(_conv_total(proposals, ('x', 'y')), 3.)
        np.testing.assert_almost_equal(_conv_total(proposals, ('x', 'z')), 2.)

    def test_pair_cap_binds(self):
        # 100 vessels, x→y limited to 0.05 ⇒ pair_cap = 5/yr. Proposed 8 → 5; x→z (limit 1.0) untouched.
        fleet = _make_fleet_for_cap(pair_limits={('x', 'y'): 0.05, ('x', 'z'): 1.0})
        proposals = _proposals({('x', 0): {'y': 8., 'z': 1.}})
        reconcile_fuel_conversion_caps(fleet, proposals, time_step=YEAR, existing_total=100.)
        np.testing.assert_almost_equal(_conv_total(proposals, ('x', 'y')), 5.)
        np.testing.assert_almost_equal(_conv_total(proposals, ('x', 'z')), 1.)

    def test_pair_caps_independent(self):
        # Per-pair caps are independent: each lane is checked in isolation, no global pool.
        fleet = _make_fleet_for_cap(pair_limits={('x', 'y'): 0.04, ('x', 'z'): 0.03})
        proposals = _proposals({('x', 0): {'y': 8., 'z': 9.}})
        reconcile_fuel_conversion_caps(fleet, proposals, time_step=YEAR, existing_total=100.)
        np.testing.assert_almost_equal(_conv_total(proposals, ('x', 'y')), 4.)
        np.testing.assert_almost_equal(_conv_total(proposals, ('x', 'z')), 3.)

    def test_pair_cap_aggregates_across_increments(self):
        # Same pair (x→y) appears in two different increments — pair-cap binds on the sum.
        fleet = _make_fleet_for_cap(pair_limits={('x', 'y'): 0.05})
        # Two increments of x→y: 4 and 6. Sum=10 > pair_cap=5 ⇒ scale 0.5 each.
        proposals = _proposals({('x', 0): {'y': 4.}, ('x', 1): {'y': 6.}})
        reconcile_fuel_conversion_caps(fleet, proposals, time_step=YEAR, existing_total=100.)
        np.testing.assert_almost_equal(proposals[('x', 0)]['conversions']['y'], 2.)
        np.testing.assert_almost_equal(proposals[('x', 1)]['conversions']['y'], 3.)

    def test_time_step_scales_budget(self):
        # 5-year time_step with pair_limit=0.1 ⇒ pair_cap = 0.5 × 100 = 50.
        fleet = _make_fleet_for_cap(pair_limits={('x', 'y'): 0.1})
        proposals = _proposals({('x', 0): {'y': 60.}})
        reconcile_fuel_conversion_caps(fleet, proposals, time_step=5.0 * YEAR, existing_total=100.)
        np.testing.assert_almost_equal(_conv_total(proposals, ('x', 'y')), 50.)

    def test_zero_existing_no_op(self):
        # Empty fleet ⇒ early return, proposals untouched.
        fleet = _make_fleet_for_cap(pair_limits={('x', 'y'): 0.1})
        proposals = _proposals({('x', 0): {'y': 5.}})
        reconcile_fuel_conversion_caps(fleet, proposals, time_step=YEAR, existing_total=0.)
        np.testing.assert_almost_equal(proposals[('x', 0)]['conversions']['y'], 5.)


# ---------------------------------------------------------------------------
# Retrofit-technology cap reconciliation
# ---------------------------------------------------------------------------

def _make_fleet_for_retrofit(technology_names: list[str], retrofit_limits: dict[str, float],
                             multiplier_increments: list[np.ndarray]) -> Fleet:
    fleet = _make_fleet_with_technologies(technology_names)
    fleet.retrofit_technology_limit = {n: Scalar(retrofit_limits.get(n, 1.0)) for n in technology_names}
    # Default: every increment fully at package 0 (current = 1.0 for package_idx=0 proposals). Tests
    # that exercise stratified vessels overwrite the package_uptake on a specific Increment directly.
    n_packages = len(technology_names) + 1
    fleet.increments = [
        [Increment(multiplier=float(m), age=0., dt=1., package_uptake=_package_at_zero(n_packages))
         for m in counts]
        for counts in multiplier_increments
    ]
    return fleet


def _package_at_zero(n_packages: int) -> np.ndarray:
    """Package-uptake vector with all mass at package 0 — i.e., no technology installed yet."""
    arr = np.zeros(n_packages)
    arr[0] = 1.
    return arr


def _retrofit_count(proposals: list, sorted_idx: int) -> float:
    """Sum the eligibility-weighted retrofit shares adding the technology at `sorted_idx` across proposals."""
    total = 0.
    for (_vessel_idx, _age_idx, package_idx, choices, current) in proposals:
        if package_idx > sorted_idx:
            continue

        k_start = sorted_idx - package_idx + 1
        if k_start >= len(choices):
            continue

        total += current * float(np.sum(choices[k_start:]))
    return total


class TestReconcileRetrofitTechnologyCaps:
    """Test `_reconcile_retrofit_technology_caps` — the per-year flow cap on retrofits per technology."""

    def test_no_cap_no_op(self):
        # Defaults at 1.0/yr ⇒ proposals untouched.
        fleet = _make_fleet_for_retrofit(["A", "B"], {}, [np.array([10.])])
        proposals = [(0, 0, 0, np.array([0.2, 0.3, 0.5]), 1.)]
        before = proposals[0][3].copy()
        reconcile_retrofit_technology_caps(fleet, proposals, time_step=YEAR, multipliers_total=100.)
        np.testing.assert_array_almost_equal(proposals[0][3], before)

    def test_cap_binds(self):
        # A capped at 0.05 (5/yr against y=100); proposed retrofits-to-A = (0.3+0.5)*10 = 8 ⇒ scale to 5.
        fleet = _make_fleet_for_retrofit(["A", "B"], {"A": 0.05, "B": 1.0}, [np.array([10.])])
        proposals = [(0, 0, 0, np.array([0.2, 0.3, 0.5]), 1.)]
        reconcile_retrofit_technology_caps(fleet, proposals, time_step=YEAR, multipliers_total=100.)
        np.testing.assert_almost_equal(_retrofit_count(proposals, 0) * 10., 5.)
        np.testing.assert_almost_equal(np.sum(proposals[0][3]), 1.)  # still sums to 1

    def test_caps_independent(self):
        # B at index 1 capped at 0.02 (2/yr); A unconstrained.
        # Proposed B = 0.5 * 10 = 5 → scale to 2 (factor 0.4); proposed A only on choices[1:] still.
        fleet = _make_fleet_for_retrofit(["A", "B"], {"A": 1.0, "B": 0.02}, [np.array([10.])])
        proposals = [(0, 0, 0, np.array([0.2, 0.3, 0.5]), 1.)]
        reconcile_retrofit_technology_caps(fleet, proposals, time_step=YEAR, multipliers_total=100.)
        # B (sorted_idx=1) is at 2.
        np.testing.assert_almost_equal(_retrofit_count(proposals, 1) * 10., 2.)

    def test_aggregates_across_proposals(self):
        # Two proposals from package_idx=0 with multipliers 4 and 6; A cap 0.05 (5/yr).
        # Proposed A across proposals = 0.8*4 + 0.8*6 = 8 ⇒ each scaled by 5/8.
        fleet = _make_fleet_for_retrofit(["A", "B"], {"A": 0.05}, [np.array([4., 6.])])
        proposals = [
            (0, 0, 0, np.array([0.2, 0.3, 0.5]), 1.),
            (0, 1, 0, np.array([0.2, 0.3, 0.5]), 1.),
        ]
        reconcile_retrofit_technology_caps(fleet, proposals, time_step=YEAR, multipliers_total=100.)
        # Aggregate A across both: 0.8*5/8*(4+6) = 5
        agg_A = (np.sum(proposals[0][3][1:]) * 4. + np.sum(proposals[1][3][1:]) * 6.)
        np.testing.assert_almost_equal(agg_A, 5.)

    def test_time_step_scales_budget(self):
        # 5-year time_step with limit 0.05 ⇒ cap = 0.05 * 100 * 5 = 25.
        fleet = _make_fleet_for_retrofit(["A"], {"A": 0.05}, [np.array([100.])])
        proposals = [(0, 0, 0, np.array([0.5, 0.5]), 1.)]  # 50 retrofits-to-A unconstrained
        reconcile_retrofit_technology_caps(fleet, proposals, time_step=5.0 * YEAR, multipliers_total=100.)
        agg_A = np.sum(proposals[0][3][1:]) * 100.
        np.testing.assert_almost_equal(agg_A, 25.)

    def test_zero_multipliers_total_no_op(self):
        fleet = _make_fleet_for_retrofit(["A"], {"A": 0.05}, [np.array([10.])])
        proposals = [(0, 0, 0, np.array([0.5, 0.5]), 1.)]
        before = proposals[0][3].copy()
        reconcile_retrofit_technology_caps(fleet, proposals, time_step=YEAR, multipliers_total=0.)
        np.testing.assert_array_almost_equal(proposals[0][3], before)


class TestReconcileRetrofitTechnologyCapsEligibility:
    """Eligibility-share weighting: cap aggregation must use `multiplier · current` (Codex Finding 2)."""

    def test_stratified_split_does_not_double_count(self):
        # Vessel split 50/50 between package 0 and package 1. Two proposals, one per package_idx, same
        # choices. Cap on B (sorted_idx=1): package_idx=0 contributes 10·0.5·0.5 = 2.5; package_idx=1
        # contributes 10·0.5·0.8 = 4.0; aggregate = 6.5. With cap 0.05·100=5, scale = 5/6.5.
        # The buggy code (no `current` factor) would compute aggregate = 10·0.5 + 10·0.8 = 13, scale ≈ 5/13.
        fleet = _make_fleet_for_retrofit(["A", "B"], {"A": 1.0, "B": 0.05}, [np.array([10.])])
        fleet.increments[0][0].package_uptake = np.array([0.5, 0.5, 0.])
        proposals = [
            (0, 0, 0, np.array([0.2, 0.3, 0.5]), 0.5),
            (0, 0, 1, np.array([0.2, 0.3, 0.5]), 0.5),
        ]
        reconcile_retrofit_technology_caps(fleet, proposals, time_step=YEAR, multipliers_total=100.)
        # Post-reconcile aggregate for B equals the cap.
        agg_B = (
            0.5 * 10. * float(np.sum(proposals[0][3][2:]))   # package_idx=0 → k_start=2
            + 0.5 * 10. * float(np.sum(proposals[1][3][1:]))  # package_idx=1 → k_start=1
        )
        np.testing.assert_almost_equal(agg_B, 5.)

    def test_zero_current_proposal_excluded_from_aggregate(self):
        # A proposal with current = 0 must not consume cap budget.
        fleet = _make_fleet_for_retrofit(["A"], {"A": 0.05}, [np.array([10.])])
        proposals = [
            (0, 0, 0, np.array([0.5, 0.5]), 1.0),  # eligible: contributes 10·1·0.5 = 5
            (0, 0, 0, np.array([0.5, 0.5]), 0.0),  # ineligible: current=0
        ]
        reconcile_retrofit_technology_caps(fleet, proposals, time_step=YEAR, multipliers_total=100.)
        # Cap is exactly at the eligible aggregate, so neither proposal should be scaled.
        np.testing.assert_array_almost_equal(proposals[0][3], np.array([0.5, 0.5]))
        np.testing.assert_array_almost_equal(proposals[1][3], np.array([0.5, 0.5]))

    def test_partial_current_aggregation(self):
        # Single proposal at package_idx=0 with current=0.4: only 4 vessels of the 10-multiplier are eligible.
        # Proposed retrofits-to-A = 0.4 · 10 · 0.8 = 3.2; cap 5/yr does not bind.
        fleet = _make_fleet_for_retrofit(["A", "B"], {"A": 0.05}, [np.array([10.])])
        fleet.increments[0][0].package_uptake = np.array([0.4, 0.6, 0.])
        proposals = [(0, 0, 0, np.array([0.2, 0.3, 0.5]), 0.4)]
        before = proposals[0][3].copy()
        reconcile_retrofit_technology_caps(fleet, proposals, time_step=YEAR, multipliers_total=100.)
        np.testing.assert_array_almost_equal(proposals[0][3], before)

    def test_transfer_matches_eligibility_weight(self):
        # Reconciler and `_transfer_retrofit_uptake` must agree on the count of vessels retrofitting to
        # each technology. With current=0.4, multiplier=10, choices=[0.2,0.3,0.5]: count for A
        # (sorted_idx=0) = 10·0.4·(0.3+0.5) = 3.2; share-of-fleet = 3.2 / 10 = 0.32.
        fleet = _make_fleet_for_retrofit(["A", "B"], {}, [np.array([10.])])
        fleet.increments[0][0].package_uptake = np.array([0.4, 0.6, 0.])
        fleet.assets = [_make_vessel("v0")]
        fleet.profile = MagicMock()
        proposals = [(0, 0, 0, np.array([0.2, 0.3, 0.5]), 0.4)]
        transfer_retrofit_uptake(fleet, proposals, idx=0)
        # The profile setter is called once per (vessel, technology). Inspect args to find technology "A".
        calls = {c.args[1]: c.args[3] for c in fleet.profile.set_retrofit_technology_uptake.call_args_list}
        np.testing.assert_almost_equal(calls["A"], 0.32)
        np.testing.assert_almost_equal(calls["B"], 0.4 * 0.5)  # k_start=2, tail=0.5 → 0.4·10·0.5 / 10 = 0.2


# ---------------------------------------------------------------------------
# Newbuild-technology cap reconciliation
# ---------------------------------------------------------------------------

def _make_fleet_for_newbuild_technology(technology_names: list[str], newbuild_limits: dict[str, float],
                                        newbuild_uptake: list[np.ndarray], n_vessels: int) -> Fleet:
    fleet = _make_fleet_with_technologies(technology_names)
    fleet.newbuild_technology_limit = {n: Scalar(newbuild_limits.get(n, 1.0)) for n in technology_names}
    fleet.newbuild_package_uptake = newbuild_uptake
    fleet.assets = [_make_vessel(f"v{i}") for i in range(n_vessels)]
    fleet.profile = MagicMock()
    return fleet


class TestReconcileNewbuildTechnologyCaps:
    """Test `_reconcile_newbuild_technology_caps` — the per-year flow cap on newbuild installs per technology."""

    def test_no_cap_no_op(self):
        fleet = _make_fleet_for_newbuild_technology(
            ["A", "B"], {}, [np.array([0.2, 0.3, 0.5])], n_vessels=1)
        before = fleet.newbuild_package_uptake[0].copy()
        reconcile_newbuild_technology_caps(fleet, np.array([10.]), time_step=YEAR, multipliers_total=100.)
        np.testing.assert_array_almost_equal(fleet.newbuild_package_uptake[0], before)

    def test_cap_binds(self):
        # A capped at 0.05 (5/yr against y=100); proposed installs-of-A = (0.3+0.5)*10 = 8 → scale to 5.
        fleet = _make_fleet_for_newbuild_technology(
            ["A", "B"], {"A": 0.05, "B": 1.0}, [np.array([0.2, 0.3, 0.5])], n_vessels=1)
        reconcile_newbuild_technology_caps(fleet, np.array([10.]), time_step=YEAR, multipliers_total=100.)
        installs_A = float(np.sum(fleet.newbuild_package_uptake[0][1:])) * 10.
        np.testing.assert_almost_equal(installs_A, 5.)
        np.testing.assert_almost_equal(np.sum(fleet.newbuild_package_uptake[0]), 1.)

    def test_caps_independent(self):
        # B at sorted_idx=1 capped at 0.02 (2/yr); A unconstrained.
        fleet = _make_fleet_for_newbuild_technology(
            ["A", "B"], {"A": 1.0, "B": 0.02}, [np.array([0.2, 0.3, 0.5])], n_vessels=1)
        reconcile_newbuild_technology_caps(fleet, np.array([10.]), time_step=YEAR, multipliers_total=100.)
        installs_B = float(fleet.newbuild_package_uptake[0][2]) * 10.
        np.testing.assert_almost_equal(installs_B, 2.)

    def test_aggregates_across_vessels(self):
        # Two vessel types, each with 5 newbuilds and same uptake. A cap 0.05 (5/yr).
        # Proposed A = 0.8*5 + 0.8*5 = 8 ⇒ each scaled by 5/8.
        fleet = _make_fleet_for_newbuild_technology(
            ["A", "B"], {"A": 0.05},
            [np.array([0.2, 0.3, 0.5]), np.array([0.2, 0.3, 0.5])], n_vessels=2)
        reconcile_newbuild_technology_caps(fleet, np.array([5., 5.]), time_step=YEAR, multipliers_total=100.)
        agg_A = (float(np.sum(fleet.newbuild_package_uptake[0][1:])) * 5.
                 + float(np.sum(fleet.newbuild_package_uptake[1][1:])) * 5.)
        np.testing.assert_almost_equal(agg_A, 5.)

    def test_zero_increments_no_contribution(self):
        # Vessel 0 has 0 newbuilds ⇒ doesn't contribute. Vessel 1 carries the binding.
        fleet = _make_fleet_for_newbuild_technology(
            ["A"], {"A": 0.05},
            [np.array([0.5, 0.5]), np.array([0.5, 0.5])], n_vessels=2)
        reconcile_newbuild_technology_caps(fleet, np.array([0., 100.]), time_step=YEAR, multipliers_total=100.)
        installs_A = float(fleet.newbuild_package_uptake[1][1]) * 100.
        np.testing.assert_almost_equal(installs_A, 5.)

    def test_zero_multipliers_total_no_op(self):
        fleet = _make_fleet_for_newbuild_technology(
            ["A"], {"A": 0.05}, [np.array([0.5, 0.5])], n_vessels=1)
        before = fleet.newbuild_package_uptake[0].copy()
        reconcile_newbuild_technology_caps(fleet, np.array([10.]), time_step=YEAR, multipliers_total=0.)
        np.testing.assert_array_almost_equal(fleet.newbuild_package_uptake[0], before)


# ---------------------------------------------------------------------------
# Modelled-uptake cap projection (per-vessel cap_share → inter/intra DCM caps)
# ---------------------------------------------------------------------------

def _make_uniform_sensitivity() -> MagicMock:
    """Stub sensitivity with an odds ratio of 1 — beta is 0, giving equal raw shares before clipping."""
    s = MagicMock()
    s.get.return_value = 1.0
    return s


def _make_fleet_for_modelled_uptakes(fuel_types: list[str], freight_rates: list[float]) -> tuple[Fleet, list]:
    """
    Build a Fleet and vessel list wired for `_calculate_modelled_uptakes`. Uses an odds ratio of 1 at
    both DCM levels so the unconstrained shares are 1/N, making cap effects directly observable.
    """
    fleet = Fleet.__new__(Fleet)
    fleet._type = FLEET
    fleet.name = "test_fleet"
    fleet.inter_fuel_sensitivity = _make_uniform_sensitivity()
    fleet.intra_fuel_sensitivity = _make_uniform_sensitivity()

    vessels = []
    for i, (fuel, rate) in enumerate(zip(fuel_types, freight_rates)):
        v = _make_vessel(f"v{i}")
        v.fuel_type = fuel
        exp = MagicMock()
        exp.get_freight_rate.return_value = rate
        v.expectation = exp
        vessels.append(v)

    return fleet, vessels


class TestModelledUptakesCapProjection:
    """Per-vessel `cap_share` projected onto the two-level (inter/intra fuel) DCM."""

    def test_no_cap_baseline(self):
        # Uniform uptake with no caps: two same-fuel vessels get equal shares (0.5 each).
        fleet, vessels = _make_fleet_for_modelled_uptakes(["x", "x"], [1., 1.])
        uptake = calculate_modelled_uptake(fleet, vessels, idx=0, cap_share=None)
        np.testing.assert_array_almost_equal(uptake, [0.5, 0.5])

    def test_same_fuel_caps_sum(self):
        # Two same-fuel vessels each capped at 0.4 ⇒ joint group cap = 0.8.
        # Uniform raw shares within group are [0.5, 0.5]; intra-cap is [0.5, 0.5] (cap/0.8); both clipped to 0.5.
        # Inter-fuel: only one group, so it absorbs the full 1.0 — but it is capped at 0.8 on the group level,
        # so total uptake = group_cap * intra_share = 0.8 * 0.5 = 0.4 per vessel; combined = 0.8.
        # The old max-based code would produce combined ≤ 0.4.
        fleet, vessels = _make_fleet_for_modelled_uptakes(["x", "x"], [1., 1.])
        uptake = calculate_modelled_uptake(fleet, vessels, idx=0, cap_share=np.array([0.4, 0.4]))
        assert uptake[0] <= 0.4 + 1e-9
        assert uptake[1] <= 0.4 + 1e-9
        np.testing.assert_almost_equal(uptake.sum(), 0.8)

    def test_same_fuel_caps_asymmetric(self):
        # Caps [0.6, 0.2] ⇒ group cap = 0.8; intra limits = [0.75, 0.25]; clipped uniform shares [0.5, 0.5]
        # become [0.5, 0.25] then redistributed → [0.75, 0.25]. Final per-vessel: 0.6 and 0.2.
        fleet, vessels = _make_fleet_for_modelled_uptakes(["x", "x"], [1., 1.])
        uptake = calculate_modelled_uptake(fleet, vessels, idx=0, cap_share=np.array([0.6, 0.2]))
        assert uptake[0] <= 0.6 + 1e-9
        assert uptake[1] <= 0.2 + 1e-9
        np.testing.assert_almost_equal(uptake.sum(), 0.8)

    def test_caps_sum_exceeds_one_clamped(self):
        # Caps [0.7, 0.7]: sum = 1.4 ⇒ group cap clamped to 1.0. Intra limits [0.7, 0.7] (each ≥ 0.5 raw),
        # so unconstrained shares [0.5, 0.5] are unchanged. Inter-fuel cap 1.0 ⇒ fuel_share = 1.0.
        # Per-vessel = 0.5 each (≤ 0.7 cap respected); combined = 1.0.
        fleet, vessels = _make_fleet_for_modelled_uptakes(["x", "x"], [1., 1.])
        uptake = calculate_modelled_uptake(fleet, vessels, idx=0, cap_share=np.array([0.7, 0.7]))
        assert uptake[0] <= 0.7 + 1e-9
        assert uptake[1] <= 0.7 + 1e-9
        np.testing.assert_almost_equal(uptake.sum(), 1.0)

    def test_zero_cap_group_zeroed(self):
        # Two fuels: x has cap=0 (group hard-capped to 0), y has cap=1. Inter-fuel limits = [0., 1.],
        # so fuel_share = [0., 1.]. Per-vessel uptakes: [0, 1] (the y vessel gets the whole budget).
        fleet, vessels = _make_fleet_for_modelled_uptakes(["x", "y"], [1., 1.])
        uptake = calculate_modelled_uptake(fleet, vessels, idx=0, cap_share=np.array([0., 1.]))
        np.testing.assert_almost_equal(uptake[0], 0.)
        np.testing.assert_almost_equal(uptake[1], 1.)

    def test_multi_group_mixed(self):
        # Fuels [x, x, y] with caps [0.3, 0.3, 0.2]. Group A (xx) cap = 0.6, group B (y) cap = 0.2.
        # Inter-fuel limits = [0.6, 0.2]; sum = 0.8 < 1 ⇒ infeasible at the inter level — apply_limits
        # clips fuel_shares to [0.6, 0.2] and the trade gap is partially unfilled (sum < 1). Per vessel:
        # group A internally splits 0.6 by intra limits [0.5, 0.5] → 0.3 each; group B → 0.2.
        fleet, vessels = _make_fleet_for_modelled_uptakes(["x", "x", "y"], [1., 1., 1.])
        uptake = calculate_modelled_uptake(fleet, vessels, idx=0, cap_share=np.array([0.3, 0.3, 0.2]))
        assert uptake[0] <= 0.3 + 1e-9
        assert uptake[1] <= 0.3 + 1e-9
        assert uptake[2] <= 0.2 + 1e-9
        np.testing.assert_almost_equal(uptake[0] + uptake[1], 0.6)
        np.testing.assert_almost_equal(uptake[2], 0.2)


# ---------------------------------------------------------------------------
# Newbuild-limit enforcement
# ---------------------------------------------------------------------------

def _make_fleet_for_newbuilds(cargo_miles: list[float],
                              orderbooks: list[float] | None = None,
                              current_uptake: list[float] | None = None) -> Fleet:
    """
    Build a Fleet stub for `calculate_orderbook_newbuilds` / `calculate_modelled_newbuilds`.
    All vessels share one fuel type with uniform DCM sensitivities, so the modelled uptake
    is driven purely by `cap_share`. Orderbooks are plain floats (cumulative vessel counts).
    """
    n = len(cargo_miles)
    fleet, vessels = _make_fleet_for_modelled_uptakes(["x"] * n, [1.] * n)
    fleet.assets = vessels

    for v, cm in zip(vessels, cargo_miles):
        v.expectation.get_cargo_miles.return_value = cm

    names = [v.get_name() for v in vessels]
    fleet.allow_vessel = dict.fromkeys(names, True)
    fleet.newbuild_available = dict.fromkeys(names, True)
    fleet.orderbooks = list(orderbooks) if orderbooks is not None else []
    fleet.orders_delivered = np.zeros(n)
    fleet.orders_postponed = np.zeros(n)
    fleet.current_uptake = np.array(current_uptake if current_uptake is not None else np.zeros(n))
    fleet.profile = MagicMock()

    return fleet


def _spy_on_modelled_uptake(monkeypatch) -> dict:
    """Replace `calculate_modelled_uptake` with a zero-uptake spy recording the cap_share it receives."""
    captured = {}

    def fake_uptake(fleet, vessels, idx, cap_share=None):
        captured["cap_share"] = cap_share
        return np.zeros(len(vessels))

    monkeypatch.setattr(fleet_evolution, "calculate_modelled_uptake", fake_uptake)

    return captured


class TestOrderbookNewbuildLimit:
    """Test the per-vessel newbuild-count cap inside `calculate_orderbook_newbuilds`."""

    def test_unconstrained_cap_no_op(self):
        # trade gap (10 cm) exceeds the ordered trade (5 cm) and the cap is slack: full delivery
        fleet = _make_fleet_for_newbuilds(cargo_miles=[1.], orderbooks=[5.])
        delivery, capacity, cap_remaining = calculate_orderbook_newbuilds(
            fleet, trade_gap=10., cap_count=np.array([100.]), idx=0)
        np.testing.assert_almost_equal(delivery, [5.])
        np.testing.assert_almost_equal(capacity, 5.)
        np.testing.assert_almost_equal(cap_remaining, [95.])
        np.testing.assert_almost_equal(fleet.orders_postponed, [0.])

    def test_cap_binds_excess_postponed(self):
        # 5 vessels ordered but the cap allows 2: 2 delivered, 3 postponed, budget exhausted
        fleet = _make_fleet_for_newbuilds(cargo_miles=[1.], orderbooks=[5.])
        delivery, capacity, cap_remaining = calculate_orderbook_newbuilds(
            fleet, trade_gap=10., cap_count=np.array([2.]), idx=0)
        np.testing.assert_almost_equal(delivery, [2.])
        np.testing.assert_almost_equal(capacity, 2.)
        np.testing.assert_almost_equal(cap_remaining, [0.])
        np.testing.assert_almost_equal(fleet.orders_delivered, [2.])
        np.testing.assert_almost_equal(fleet.orders_postponed, [3.])

    def test_postponed_redelivery_respects_cap(self):
        # orders postponed by the cap in one step are still subject to the next step's cap
        fleet = _make_fleet_for_newbuilds(cargo_miles=[1.], orderbooks=[5.])
        calculate_orderbook_newbuilds(fleet, trade_gap=10., cap_count=np.array([2.]), idx=0)
        delivery, _, cap_remaining = calculate_orderbook_newbuilds(
            fleet, trade_gap=10., cap_count=np.array([1.]), idx=1)
        np.testing.assert_almost_equal(delivery, [1.])
        np.testing.assert_almost_equal(cap_remaining, [0.])
        np.testing.assert_almost_equal(fleet.orders_delivered, [3.])
        np.testing.assert_almost_equal(fleet.orders_postponed, [2.])

    def test_cap_independent_per_vessel(self):
        # the cap is a per-vessel budget: v0 is capped, v1 is not
        fleet = _make_fleet_for_newbuilds(cargo_miles=[1., 1.], orderbooks=[4., 3.])
        delivery, _, cap_remaining = calculate_orderbook_newbuilds(
            fleet, trade_gap=100., cap_count=np.array([1., 100.]), idx=0)
        np.testing.assert_almost_equal(delivery, [1., 3.])
        np.testing.assert_almost_equal(cap_remaining, [0., 97.])
        np.testing.assert_almost_equal(fleet.orders_postponed, [3., 0.])


class TestModelledNewbuildLimit:
    """Test the per-vessel newbuild-count cap inside `calculate_modelled_newbuilds`."""

    def test_inertia_clipped_to_cap(self):
        # inertia alone demands 10 vessels (uptake 1 * trade_gap 10 / cm 1) but the cap allows 4;
        # the remaining budget is zero, so the modelled DCM receives cap_share 0 and adds nothing
        fleet = _make_fleet_for_newbuilds(cargo_miles=[1.], current_uptake=[1.])
        increments, capacity = calculate_modelled_newbuilds(
            fleet, trade_gap=10., cap_count=np.array([4.]), idx=0)
        np.testing.assert_almost_equal(increments, [4.])
        np.testing.assert_almost_equal(capacity, 4.)

    def test_cap_share_derivation(self, monkeypatch):
        # cap_share[v] = min(remaining cap * cargo_miles / trade_gap, 1) after the inertia clip:
        # v0's budget (3) is consumed by inertia (5 down to 3), v1's budget (4) exceeds the
        # residual trade gap (7 cm / 2 cm-per-vessel), so its share clamps to 1
        captured = _spy_on_modelled_uptake(monkeypatch)

        fleet = _make_fleet_for_newbuilds(cargo_miles=[1., 2.], current_uptake=[0.5, 0.])
        calculate_modelled_newbuilds(fleet, trade_gap=10., cap_count=np.array([3., 4.]), idx=0)
        np.testing.assert_almost_equal(captured["cap_share"], [0., 1.])

    def test_cap_share_ones_when_trade_gap_filled(self, monkeypatch):
        # inertia fills the whole trade gap, so the count cap is moot and cap_share defaults to 1
        captured = _spy_on_modelled_uptake(monkeypatch)

        fleet = _make_fleet_for_newbuilds(cargo_miles=[1.], current_uptake=[1.])
        calculate_modelled_newbuilds(fleet, trade_gap=5., cap_count=np.array([10.]), idx=0)
        np.testing.assert_almost_equal(captured["cap_share"], [1.])

    def test_budget_threading_across_stages(self):
        # mirrors perform_fleet_evolution: the orderbook consumes part of the shared budget and
        # its returned remainder caps the inertia + modelled stage, keeping totals within budget
        fleet = _make_fleet_for_newbuilds(cargo_miles=[1.], orderbooks=[4.], current_uptake=[1.])
        cap_count = np.array([5.])

        delivery, capacity, cap_remaining = calculate_orderbook_newbuilds(
            fleet, trade_gap=10., cap_count=cap_count, idx=0)
        trade_gap = 10. - capacity

        increments, _ = calculate_modelled_newbuilds(fleet, trade_gap, cap_remaining, idx=0)

        np.testing.assert_almost_equal(delivery, [4.])
        np.testing.assert_almost_equal(increments, [1.])
        assert np.all(delivery + increments <= cap_count + 1e-9)
