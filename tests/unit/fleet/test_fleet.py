# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for Fleet module-level helper functions."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from navigate.core import Scalar
from navigate.core.increment import VesselIncrement
from navigate.core.node_type import FLEET, VESSEL
from navigate.core.nodes.fleet import Fleet
from navigate.fleet import planning as fleet_planning
from navigate.fleet.conversion import (
    _ConversionCandidate,
    _ConversionProposal,
    is_retrofit_cycle,
    reconcile_fuel_conversion_caps,
)
from navigate.fleet.planning import (
    calculate_modelled_newbuilds,
    calculate_modelled_uptake,
    calculate_orderbook_newbuilds,
)
from navigate.fleet.technology_adoption import (
    _CapContribution,
    _get_remaining_lifetime,
    _reconcile_retrofit_technology_caps,
    _RetrofitProposal,
    _scale_tails_to_cap,
    _transfer_retrofit_uptake,
    reconcile_newbuild_technology_caps,
)
from navigate.util import YEAR

# slack on `uptake <= cap` checks: the DCM's limit projection iterates in floating
# point, so a share sitting exactly on its cap may overshoot it by rounding noise
CAP_TOLERANCE = 1e-9

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vessel(name):
    """Create a mock Vessel with minimal interface."""
    v = MagicMock()
    v.name = name
    v.type = VESSEL
    v.is_type.side_effect = lambda t: t == VESSEL
    return v


# ---------------------------------------------------------------------------
# Module-level helper functions
# ---------------------------------------------------------------------------


class TestIsRetrofitCycle:
    """Test _is_retrofit_cycle standalone function."""

    @pytest.mark.parametrize(
        ("age", "frequency", "dt", "expected"),
        [
            (5.0, 5.0, 1.0, True),
            (3.0, 5.0, 1.0, False),
            # age == time_step means vessel just entered, should not retrofit
            (1.0, 1.0, 1.0, False),
            # the age is rounded before the modulo, so float drift just below a
            # multiple of the frequency still lands on the cycle
            (4.9999999, 5.0, 1.0, True),
        ],
    )
    def test_cycle(self, age, frequency, dt, expected):
        assert is_retrofit_cycle(age, frequency, dt) is expected


class TestGetRemainingLifetime:
    """Test _get_remaining_lifetime."""

    @pytest.mark.parametrize(
        ("age", "expected"),
        [
            (0.0, 24),
            (24.0, 0),
            (30.0, 0),
        ],
    )
    def test_remaining(self, age, expected):
        vessel = _make_vessel("v")
        vessel.lifetime = Scalar(25)
        assert _get_remaining_lifetime(vessel, age=age, dt=1.0) == expected


# ---------------------------------------------------------------------------
# Technology cap reconciliation (per-year flow caps)
# ---------------------------------------------------------------------------


def _make_technology(name: str):
    t = MagicMock()
    t.name = name
    return t


def _make_package(technologies):
    package = MagicMock()
    package.technologies = technologies
    return package


def _make_fleet_with_technologies(technology_names: list[str]) -> Fleet:
    """Fleet stub, CAPEX-sorted cumulative-prefix packages for `technology_names`."""
    technologies = [_make_technology(n) for n in technology_names]
    packages = [_make_package(technologies[:i]) for i in range(len(technologies) + 1)]
    fleet = Fleet.__new__(Fleet)
    fleet.technology_packages = packages
    return fleet


# ---------------------------------------------------------------------------
# Fuel-conversion cap reconciliation
# ---------------------------------------------------------------------------


def _make_fleet_for_cap(
    pair_limits: dict[tuple[str, str], float] | None = None,
) -> Fleet:
    """
    Build a Fleet stub configured just for `reconcile_fuel_conversion_caps`.

    The cap is a fraction-of-fleet-per-year per (from, to) pair; missing pairs
    default to Scalar(1.) (unlimited).
    """
    fleet = Fleet.__new__(Fleet)
    fleet.fuel_conversion_limit = {
        pair: Scalar(limit) for pair, limit in (pair_limits or {}).items()
    }
    return fleet


def _proposals(
    items: dict[tuple[str, int], dict[str, float]],
) -> list[_ConversionProposal]:
    """Map (name_from, increment_idx) -> {name_to: count} into the proposal shape."""
    return [
        _ConversionProposal(
            name_from,
            increment_idx,
            0.0,
            1.0,
            {
                name_to: _ConversionCandidate(
                    metric=0.0,
                    limit=1.0,
                    energy_per_vessel=0.0,
                    charge=0.0,
                    window=0.0,
                    count=count,
                )
                for name_to, count in conversions.items()
            },
        )
        for (name_from, increment_idx), conversions in items.items()
    ]


def _conv_total(proposals: list[_ConversionProposal], pair: tuple[str, str]) -> float:
    return sum(
        proposal.candidates[pair[1]].count
        for proposal in proposals
        if proposal.name_from == pair[0] and pair[1] in proposal.candidates
    )


class TestReconcileFuelConversionCaps:
    """Test `_reconcile_fuel_conversion_caps` — the per-pair flow cap."""

    @pytest.mark.parametrize(
        ("pair_limit", "existing_total"),
        [
            # a limit of 1.0 (100% of the fleet per year) does not bind
            (1.0, 100.0),
            # an empty fleet returns early
            (0.1, 0.0),
        ],
    )
    def test_no_op(self, pair_limit, existing_total):
        fleet = _make_fleet_for_cap(pair_limits={("x", "y"): pair_limit})
        proposals = _proposals({("x", 0): {"y": 5.0}})
        reconcile_fuel_conversion_caps(
            fleet, proposals, time_step=YEAR, existing_total=existing_total
        )
        np.testing.assert_almost_equal(proposals[0].candidates["y"].count, 5.0)

    def test_pair_cap_binds(self):
        # 100 vessels; each (from, to) lane is checked against its own cap, with no
        # global pool: x→y at 0.05 ⇒ 5/yr (8 → 5), x→z at 0.03 ⇒ 3/yr (9 → 3), x→w at
        # 1.0 untouched.
        fleet = _make_fleet_for_cap(
            pair_limits={("x", "y"): 0.05, ("x", "z"): 0.03, ("x", "w"): 1.0}
        )
        proposals = _proposals({("x", 0): {"y": 8.0, "z": 9.0, "w": 1.0}})
        reconcile_fuel_conversion_caps(
            fleet, proposals, time_step=YEAR, existing_total=100.0
        )
        np.testing.assert_almost_equal(_conv_total(proposals, ("x", "y")), 5.0)
        np.testing.assert_almost_equal(_conv_total(proposals, ("x", "z")), 3.0)
        np.testing.assert_almost_equal(_conv_total(proposals, ("x", "w")), 1.0)

    def test_pair_cap_aggregates_across_increments(self):
        # Same pair (x→y) appears in two different increments — pair-cap binds on
        # the sum.
        fleet = _make_fleet_for_cap(pair_limits={("x", "y"): 0.05})
        # Two increments of x→y: 4 and 6. Sum=10 > pair_cap=5 ⇒ scale 0.5 each.
        proposals = _proposals({("x", 0): {"y": 4.0}, ("x", 1): {"y": 6.0}})
        reconcile_fuel_conversion_caps(
            fleet, proposals, time_step=YEAR, existing_total=100.0
        )
        np.testing.assert_almost_equal(proposals[0].candidates["y"].count, 2.0)
        np.testing.assert_almost_equal(proposals[1].candidates["y"].count, 3.0)

    def test_time_step_scales_budget(self):
        # 5-year time_step with pair_limit=0.1 ⇒ pair_cap = 0.5 * 100 = 50.
        fleet = _make_fleet_for_cap(pair_limits={("x", "y"): 0.1})
        proposals = _proposals({("x", 0): {"y": 60.0}})
        reconcile_fuel_conversion_caps(
            fleet, proposals, time_step=5.0 * YEAR, existing_total=100.0
        )
        np.testing.assert_almost_equal(_conv_total(proposals, ("x", "y")), 50.0)


# ---------------------------------------------------------------------------
# Retrofit-technology cap reconciliation
# ---------------------------------------------------------------------------


def _make_fleet_for_retrofit(
    technology_names: list[str],
    retrofit_limits: dict[str, float],
    multiplier_increments: list[np.ndarray],
) -> Fleet:
    fleet = _make_fleet_with_technologies(technology_names)
    fleet.retrofit_technology_limit = {
        n: Scalar(retrofit_limits.get(n, 1.0)) for n in technology_names
    }
    # Default: every increment fully at package 0 (current = 1.0 for package_idx=0
    # proposals). Tests that exercise stratified vessels overwrite the package_uptake on
    # a specific VesselIncrement directly.
    n_packages = len(technology_names) + 1
    fleet.increments = [
        [
            VesselIncrement(
                multiplier=float(m),
                age=0.0,
                age_span=1.0,
                package_uptake=_package_at_zero(n_packages),
            )
            for m in counts
        ]
        for counts in multiplier_increments
    ]
    return fleet


def _package_at_zero(n_packages: int) -> np.ndarray:
    """Package-uptake vector, all mass at package 0 — no technology installed yet."""
    arr = np.zeros(n_packages)
    arr[0] = 1.0
    return arr


def _proposal(
    fleet: Fleet,
    vessel_idx: int,
    age_idx: int,
    package_idx: int,
    choices: np.ndarray,
    current: float,
) -> _RetrofitProposal:
    """Build a retrofit proposal with zero levelized annual costs per step."""
    return _RetrofitProposal(
        vessel_idx,
        fleet.increments[vessel_idx][age_idx],
        package_idx,
        choices,
        current,
        np.zeros_like(choices),
    )


def _retrofit_count(proposals: list, sorted_idx: int) -> float:
    """Sum eligibility-weighted shares adding tech `sorted_idx` across proposals."""
    total = 0.0
    for proposal in proposals:
        if proposal.package_idx > sorted_idx:
            continue

        k_start = sorted_idx - proposal.package_idx + 1
        if k_start >= len(proposal.choices):
            continue

        total += proposal.eligible_share * float(np.sum(proposal.choices[k_start:]))
    return total


class TestReconcileRetrofitTechnologyCaps:
    """Test `_reconcile_retrofit_technology_caps` — the per-year retrofit flow cap."""

    @pytest.mark.parametrize(
        ("limits", "multipliers_total"),
        [
            # defaults at 1.0/yr do not bind
            ({}, 100.0),
            # an empty fleet returns early
            ({"A": 0.05}, 0.0),
        ],
    )
    def test_no_op(self, limits, multipliers_total):
        fleet = _make_fleet_for_retrofit(["A", "B"], limits, [np.array([10.0])])
        proposals = [_proposal(fleet, 0, 0, 0, np.array([0.2, 0.3, 0.5]), 1.0)]
        before = proposals[0].choices.copy()
        _reconcile_retrofit_technology_caps(
            fleet, proposals, time_step=YEAR, multipliers_total=multipliers_total
        )
        np.testing.assert_array_almost_equal(proposals[0].choices, before)

    def test_cap_binds(self):
        # A capped at 0.05 (5/yr against y=100); proposed retrofits-to-A =
        # (0.3+0.5)*10 = 8 ⇒ scale to 5.
        fleet = _make_fleet_for_retrofit(
            ["A", "B"], {"A": 0.05, "B": 1.0}, [np.array([10.0])]
        )
        proposals = [_proposal(fleet, 0, 0, 0, np.array([0.2, 0.3, 0.5]), 1.0)]
        _reconcile_retrofit_technology_caps(
            fleet, proposals, time_step=YEAR, multipliers_total=100.0
        )
        np.testing.assert_almost_equal(_retrofit_count(proposals, 0) * 10.0, 5.0)
        np.testing.assert_almost_equal(
            np.sum(proposals[0].choices), 1.0
        )  # still sums to 1

    def test_aggregates_across_proposals(self):
        # Two proposals from package_idx=0 with multipliers 4 and 6; A cap 0.05 (5/yr).
        # Proposed A across proposals = 0.8*4 + 0.8*6 = 8 ⇒ each scaled by 5/8.
        fleet = _make_fleet_for_retrofit(
            ["A", "B"], {"A": 0.05}, [np.array([4.0, 6.0])]
        )
        proposals = [
            _proposal(fleet, 0, 0, 0, np.array([0.2, 0.3, 0.5]), 1.0),
            _proposal(fleet, 0, 1, 0, np.array([0.2, 0.3, 0.5]), 1.0),
        ]
        _reconcile_retrofit_technology_caps(
            fleet, proposals, time_step=YEAR, multipliers_total=100.0
        )
        # Aggregate A across both: 0.8*5/8*(4+6) = 5
        agg_a = (
            np.sum(proposals[0].choices[1:]) * 4.0
            + np.sum(proposals[1].choices[1:]) * 6.0
        )
        np.testing.assert_almost_equal(agg_a, 5.0)


class TestScaleTailsToCap:
    """The share a binding cap displaces goes to the stay option, not a cheaper one."""

    def test_nested_cap_displaces_to_stay_option(self):
        # Cumulative packages [none, A, A+B] and a cap on B (tail from index 2). 10
        # vessels adopt B at share 0.5, i.e. 5 against a cap of 2, so the tail scales
        # by 2/5 to 0.2 and the displaced 0.3 goes to `none`. The share at A keeps its
        # 0.3 even though A has slack: the package is the unit of choice.
        shares = np.array([0.2, 0.3, 0.5])
        _scale_tails_to_cap([_CapContribution(shares, 2, 10.0)], cap=2.0)
        np.testing.assert_array_almost_equal(shares, [0.5, 0.3, 0.2])


class TestReconcileRetrofitTechnologyCapsEligibility:
    """Eligibility-share weighting: cap aggregation must use `multiplier · current`."""

    @pytest.mark.parametrize(
        ("limits", "package_uptake", "proposed", "capped_idx", "expected"),
        [
            # Vessel split 50/50 between package 0 and package 1, one proposal per
            # package, cap on B (5/yr). Package 0 contributes 10·0.5·0.5 = 2.5, package
            # 1 contributes 10·0.5·0.8 = 4.0; 6.5 > 5 so the aggregate lands on the
            # cap. Without the `current` factor the aggregate would read 13 and the
            # scale 5/13, leaving 2.5.
            ({"B": 0.05}, [0.5, 0.5, 0.0], [(0, 0.5), (1, 0.5)], 1, 5.0),
            # A proposal with current = 0 consumes no budget: the eligible one
            # contributes 10·1·0.8 = 8, exactly the cap, so nothing is scaled.
            ({"A": 0.08}, [1.0, 0.0, 0.0], [(0, 1.0), (0, 0.0)], 0, 8.0),
            # current = 0.4: only 4 of the 10 vessels are eligible, so retrofits-to-A
            # are 0.4·10·0.8 = 3.2 and the 5/yr cap does not bind.
            ({"A": 0.05}, [0.4, 0.6, 0.0], [(0, 0.4)], 0, 3.2),
        ],
    )
    def test_aggregate_weights_by_eligible_share(
        self, limits, package_uptake, proposed, capped_idx, expected
    ):
        fleet = _make_fleet_for_retrofit(["A", "B"], limits, [np.array([10.0])])
        fleet.increments[0][0].package_uptake = np.array(package_uptake)
        proposals = [
            _proposal(fleet, 0, 0, package_idx, np.array([0.2, 0.3, 0.5]), current)
            for package_idx, current in proposed
        ]
        _reconcile_retrofit_technology_caps(
            fleet, proposals, time_step=YEAR, multipliers_total=100.0
        )
        np.testing.assert_almost_equal(
            10.0 * _retrofit_count(proposals, capped_idx), expected
        )

    def test_transfer_matches_eligibility_weight(self):
        # Reconciler and `_transfer_retrofit_uptake` must agree on the count of vessels
        # retrofitting to each technology. With current=0.4, multiplier=10,
        # choices=[0.2,0.3,0.5]: count for A (sorted_idx=0) = 10·0.4·(0.3+0.5) = 3.2;
        # share-of-fleet = 3.2 / 10 = 0.32.
        fleet = _make_fleet_for_retrofit(["A", "B"], {}, [np.array([10.0])])
        fleet.increments[0][0].package_uptake = np.array([0.4, 0.6, 0.0])
        fleet.assets = [_make_vessel("v0")]
        fleet.profile = MagicMock()
        proposals = [_proposal(fleet, 0, 0, 0, np.array([0.2, 0.3, 0.5]), 0.4)]
        _transfer_retrofit_uptake(fleet, proposals, idx=0)
        # The profile setter is called once per (vessel, technology). Inspect args to
        # find technology "A".
        calls = {
            c.args[2]: c.args[3]
            for c in fleet.profile.set_retrofit_technology_uptake.call_args_list
        }
        np.testing.assert_almost_equal(calls["A"], 0.32)
        np.testing.assert_almost_equal(
            calls["B"], 0.4 * 0.5
        )  # k_start=2, tail=0.5 → 0.4·10·0.5 / 10 = 0.2


# ---------------------------------------------------------------------------
# Newbuild-technology cap reconciliation
# ---------------------------------------------------------------------------


def _make_fleet_for_newbuild_technology(
    technology_names: list[str],
    newbuild_limits: dict[str, float],
    newbuild_uptake: list[np.ndarray],
    n_vessels: int,
) -> Fleet:
    fleet = _make_fleet_with_technologies(technology_names)
    fleet.newbuild_technology_limit = {
        n: Scalar(newbuild_limits.get(n, 1.0)) for n in technology_names
    }
    fleet.newbuild_package_uptake = newbuild_uptake
    fleet.assets = [_make_vessel(f"v{i}") for i in range(n_vessels)]
    fleet.profile = MagicMock()
    return fleet


class TestReconcileNewbuildTechnologyCaps:
    """Test `_reconcile_newbuild_technology_caps` — the per-year newbuild flow cap."""

    def test_cap_binds(self):
        # A capped at 0.05 (5/yr against y=100); proposed installs-of-A =
        # (0.3+0.5)*10 = 8 → scale to 5.
        fleet = _make_fleet_for_newbuild_technology(
            ["A", "B"], {"A": 0.05, "B": 1.0}, [np.array([0.2, 0.3, 0.5])], n_vessels=1
        )
        reconcile_newbuild_technology_caps(
            fleet, np.array([10.0]), time_step=YEAR, multipliers_total=100.0
        )
        installs_a = float(np.sum(fleet.newbuild_package_uptake[0][1:])) * 10.0
        np.testing.assert_almost_equal(installs_a, 5.0)
        np.testing.assert_almost_equal(np.sum(fleet.newbuild_package_uptake[0]), 1.0)

    def test_zero_increments_no_contribution(self):
        # Vessel 0 has 0 newbuilds ⇒ doesn't contribute. Vessel 1 carries the binding.
        fleet = _make_fleet_for_newbuild_technology(
            ["A"],
            {"A": 0.05},
            [np.array([0.5, 0.5]), np.array([0.5, 0.5])],
            n_vessels=2,
        )
        reconcile_newbuild_technology_caps(
            fleet, np.array([0.0, 100.0]), time_step=YEAR, multipliers_total=100.0
        )
        installs_a = float(fleet.newbuild_package_uptake[1][1]) * 100.0
        np.testing.assert_almost_equal(installs_a, 5.0)


# ---------------------------------------------------------------------------
# Modelled-uptake cap projection (per-vessel cap_share → inter/intra DCM caps)
# ---------------------------------------------------------------------------


def _make_uniform_sensitivity() -> MagicMock:
    """Stub sensitivity, odds ratio 1 — beta 0, equal raw shares before clipping."""
    s = MagicMock()
    s.get.return_value = 1.0
    return s


def _make_fleet_for_modelled_uptakes(
    fuel_types: list[str], freight_rates: list[float]
) -> tuple[Fleet, list]:
    """
    Build a Fleet and vessel list wired for `_calculate_modelled_uptakes`.

    Uses an odds ratio of 1 at both DCM levels so the unconstrained shares are 1/N,
    making cap effects directly observable.
    """
    fleet = Fleet.__new__(Fleet)
    fleet.type = FLEET
    fleet.name = "test_fleet"
    fleet.inter_fuel_sensitivity = _make_uniform_sensitivity()
    fleet.intra_fuel_sensitivity = _make_uniform_sensitivity()

    vessels = []
    for i, (fuel, rate) in enumerate(zip(fuel_types, freight_rates, strict=True)):
        v = _make_vessel(f"v{i}")
        v.primary_fuel_type = fuel
        exp = MagicMock()
        exp.get_freight_rate.return_value = rate
        v.expectation = exp
        vessels.append(v)

    return fleet, vessels


class TestModelledUptakesCapProjection:
    """Per-vessel `cap_share` projected onto the two-level (inter/intra fuel) DCM."""

    @pytest.mark.parametrize(
        "cap_share",
        [
            # each vessel capped at 0.4 ⇒ joint group cap 0.8; a max-based projection
            # would leave the pair at 0.4 combined
            [0.4, 0.4],
            # asymmetric caps: intra limits [0.75, 0.25] of the 0.8 group cap
            [0.6, 0.2],
            # caps summing above one: the group cap clamps to 1.0
            [0.7, 0.7],
        ],
    )
    def test_same_fuel_caps_sum(self, cap_share):
        # Two same-fuel vessels form one inter-fuel group whose cap is the sum of the
        # vessel caps, clamped to 1; the group fills its cap and no vessel exceeds
        # its own.
        fleet, vessels = _make_fleet_for_modelled_uptakes(["x", "x"], [1.0, 1.0])
        uptake = calculate_modelled_uptake(
            fleet, vessels, idx=0, cap_share=np.array(cap_share)
        )
        assert np.all(uptake <= np.array(cap_share) + CAP_TOLERANCE)
        np.testing.assert_almost_equal(uptake.sum(), min(sum(cap_share), 1.0))

    def test_zero_cap_group_zeroed(self):
        # Two fuels: x has cap=0 (group hard-capped to 0), y has cap=1. Inter-fuel
        # limits = [0., 1.], so fuel_share = [0., 1.]. Per-vessel uptakes: [0, 1] (the y
        # vessel gets the whole budget).
        fleet, vessels = _make_fleet_for_modelled_uptakes(["x", "y"], [1.0, 1.0])
        uptake = calculate_modelled_uptake(
            fleet, vessels, idx=0, cap_share=np.array([0.0, 1.0])
        )
        np.testing.assert_almost_equal(uptake[0], 0.0)
        np.testing.assert_almost_equal(uptake[1], 1.0)

    def test_multi_group_mixed(self):
        # Fuels [x, x, y] with caps [0.3, 0.3, 0.2]. Group A (xx) cap = 0.6, group B (y)
        # cap = 0.2. Inter-fuel limits = [0.6, 0.2]; sum = 0.8 < 1 ⇒ infeasible at the
        # inter level — apply_limits clips fuel_shares to [0.6, 0.2] and the trade gap
        # is partially unfilled (sum < 1). Per vessel: group A internally splits 0.6 by
        # intra limits [0.5, 0.5] → 0.3 each; group B → 0.2.
        fleet, vessels = _make_fleet_for_modelled_uptakes(
            ["x", "x", "y"], [1.0, 1.0, 1.0]
        )
        uptake = calculate_modelled_uptake(
            fleet, vessels, idx=0, cap_share=np.array([0.3, 0.3, 0.2])
        )
        assert np.all(uptake <= np.array([0.3, 0.3, 0.2]) + CAP_TOLERANCE)
        np.testing.assert_almost_equal(uptake[0] + uptake[1], 0.6)
        np.testing.assert_almost_equal(uptake[2], 0.2)


# ---------------------------------------------------------------------------
# Newbuild-limit enforcement
# ---------------------------------------------------------------------------


def _make_fleet_for_newbuilds(
    cargo_miles: list[float],
    orderbooks: list[float] | None = None,
    current_uptake: list[float] | None = None,
) -> Fleet:
    """
    Build a Fleet stub for the newbuild-calculation functions.

    Covers `calculate_orderbook_newbuilds` and `calculate_modelled_newbuilds`. All
    vessels share one fuel type with uniform DCM sensitivities, so the modelled uptake
    is driven purely by `cap_share`. Orderbooks are plain floats (cumulative vessel
    counts).
    """
    n = len(cargo_miles)
    fleet, vessels = _make_fleet_for_modelled_uptakes(["x"] * n, [1.0] * n)
    fleet.assets = vessels

    for v, cm in zip(vessels, cargo_miles, strict=True):
        v.expectation.get_cargo_miles.return_value = cm

    names = [v.name for v in vessels]
    fleet.allow_vessel = dict.fromkeys(names, True)
    fleet.newbuild_available = dict.fromkeys(names, True)
    fleet.orderbooks = list(orderbooks) if orderbooks is not None else []
    fleet.orders_delivered = np.zeros(n)
    fleet.orders_postponed = np.zeros(n)
    fleet.current_uptake = np.array(
        current_uptake if current_uptake is not None else np.zeros(n)
    )
    fleet.profile = MagicMock()

    return fleet


def _spy_on_modelled_uptake(monkeypatch) -> dict:
    """Replace `calculate_modelled_uptake` with a zero-uptake spy on the cap_share."""
    captured = {}

    def fake_uptake(fleet, vessels, idx, cap_share):
        captured["cap_share"] = cap_share
        return np.zeros(len(vessels))

    monkeypatch.setattr(fleet_planning, "calculate_modelled_uptake", fake_uptake)

    return captured


class TestOrderbookNewbuildLimit:
    """Test the per-vessel newbuild-count cap inside `calculate_orderbook_newbuilds`."""

    @pytest.mark.parametrize(
        ("orderbooks", "cap_count", "delivery", "cap_remaining", "postponed"),
        [
            # 5 vessels ordered but the cap allows 2: 2 delivered, 3 postponed, budget
            # exhausted
            ([5.0], [2.0], [2.0], [0.0], [3.0]),
            # the cap is slack: full delivery
            ([5.0], [100.0], [5.0], [95.0], [0.0]),
            # the cap is a per-vessel budget: v0 is capped, v1 is not
            ([4.0, 3.0], [1.0, 100.0], [1.0, 3.0], [0.0, 97.0], [3.0, 0.0]),
        ],
    )
    def test_cap_limits_delivery(
        self, orderbooks, cap_count, delivery, cap_remaining, postponed
    ):
        # the trade gap exceeds the ordered trade, so only the cap limits delivery
        cargo_miles = [1.0] * len(orderbooks)
        fleet = _make_fleet_for_newbuilds(
            cargo_miles=cargo_miles, orderbooks=orderbooks
        )
        delivered, capacity, remaining = calculate_orderbook_newbuilds(
            fleet, trade_gap=100.0, cap_count=np.array(cap_count), idx=0
        )
        np.testing.assert_almost_equal(delivered, delivery)
        np.testing.assert_almost_equal(capacity, np.dot(delivery, cargo_miles))
        np.testing.assert_almost_equal(remaining, cap_remaining)
        np.testing.assert_almost_equal(fleet.orders_delivered, delivery)
        np.testing.assert_almost_equal(fleet.orders_postponed, postponed)

    def test_postponed_redelivery_respects_cap(self):
        # orders postponed by the cap in one step are still subject to the next
        # step's cap
        fleet = _make_fleet_for_newbuilds(cargo_miles=[1.0], orderbooks=[5.0])
        calculate_orderbook_newbuilds(
            fleet, trade_gap=10.0, cap_count=np.array([2.0]), idx=0
        )
        delivery, _, cap_remaining = calculate_orderbook_newbuilds(
            fleet, trade_gap=10.0, cap_count=np.array([1.0]), idx=1
        )
        np.testing.assert_almost_equal(delivery, [1.0])
        np.testing.assert_almost_equal(cap_remaining, [0.0])
        np.testing.assert_almost_equal(fleet.orders_delivered, [3.0])
        np.testing.assert_almost_equal(fleet.orders_postponed, [2.0])


class TestModelledNewbuildLimit:
    """Test the per-vessel newbuild-count cap inside `calculate_modelled_newbuilds`."""

    def test_inertia_clipped_to_cap(self):
        # inertia alone demands 10 vessels (uptake 1 * trade_gap 10 / cm 1) but the cap
        # allows 4; the remaining budget is zero, so the modelled DCM receives cap_share
        # 0 and adds nothing
        fleet = _make_fleet_for_newbuilds(cargo_miles=[1.0], current_uptake=[1.0])
        increments, capacity = calculate_modelled_newbuilds(
            fleet, trade_gap=10.0, cap_count=np.array([4.0]), idx=0
        )
        np.testing.assert_almost_equal(increments, [4.0])
        np.testing.assert_almost_equal(capacity, 4.0)

    @pytest.mark.parametrize(
        ("cargo_miles", "current_uptake", "trade_gap", "cap_count", "expected"),
        [
            # cap_share[v] = min(remaining cap * cargo_miles / trade_gap, 1) after the
            # inertia clip: v0's budget (3) is consumed by inertia (5 down to 3), v1's
            # budget (4) exceeds the residual trade gap (7 cm / 2 cm-per-vessel), so
            # its share clamps to 1
            ([1.0, 2.0], [0.5, 0.0], 10.0, [3.0, 4.0], [0.0, 1.0]),
            # inertia fills the whole trade gap, so the count cap is moot and
            # cap_share defaults to 1
            ([1.0], [1.0], 5.0, [10.0], [1.0]),
        ],
    )
    def test_cap_share_derivation(
        self, monkeypatch, cargo_miles, current_uptake, trade_gap, cap_count, expected
    ):
        captured = _spy_on_modelled_uptake(monkeypatch)

        fleet = _make_fleet_for_newbuilds(
            cargo_miles=cargo_miles, current_uptake=current_uptake
        )
        calculate_modelled_newbuilds(
            fleet, trade_gap=trade_gap, cap_count=np.array(cap_count), idx=0
        )
        np.testing.assert_almost_equal(captured["cap_share"], expected)
