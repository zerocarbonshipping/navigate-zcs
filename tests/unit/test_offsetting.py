# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for emission offset reclassification on vessel profiles."""
from unittest.mock import MagicMock

import numpy as np

# pre-load bunker to avoid circular import via navigate.policy.__init__
from navigate.bunker.bunker_algorithm import BunkerAlgorithm  # noqa: F401
from navigate.core.enum_ import LevySchemeID
from navigate.policy.offsetting import _reclassify_vessel_policy_units, calculate_offsetting

N_STEPS = 5


def _make_vessel(name, remedial_units=None, levy_units=None):
    """Create a mock vessel with a profile storing per-policy remedial/levy and scalar offset arrays.

    Parameters
    ----------
    remedial_units : dict[str, float] | None
        Per-regulation remedial units, e.g. {'reg_a': 100.}.
    levy_units : dict[str, float] | None
        Per-levy emission units, e.g. {'levy_a': 50.}.
    """
    profile = MagicMock()

    remedial_data = {}
    for policy_name, val in (remedial_units or {}).items():
        arr = np.zeros(N_STEPS)
        arr[:] = val
        remedial_data[policy_name] = arr
    levy_data = {}
    for policy_name, val in (levy_units or {}).items():
        arr = np.zeros(N_STEPS)
        arr[:] = val
        levy_data[policy_name] = arr
    offset_arr = np.zeros(N_STEPS)

    def get_remedial(policy_name, idx=np.s_[:]):
        return remedial_data[policy_name][idx] if policy_name in remedial_data else 0.

    def add_remedial(policy_name, idx, units):
        if policy_name not in remedial_data:
            remedial_data[policy_name] = np.zeros(N_STEPS)
        remedial_data[policy_name][idx] += units

    def get_levy(policy_name, idx=np.s_[:]):
        return levy_data[policy_name][idx] if policy_name in levy_data else 0.

    def add_levy(policy_name, idx, units):
        if policy_name not in levy_data:
            levy_data[policy_name] = np.zeros(N_STEPS)
        levy_data[policy_name][idx] += units

    profile.get_remedial_units = get_remedial
    profile.add_remedial_units = add_remedial
    profile.get_levy_units = get_levy
    profile.add_levy_units = add_levy
    profile.add_offset = lambda offset, idx=np.s_[:]: offset_arr.__setitem__(idx, offset_arr[idx] + offset)

    profile._remedial_data = remedial_data
    profile._levy_data = levy_data
    profile._offset_arr = offset_arr

    vessel = MagicMock()
    vessel.get_name.return_value = name
    vessel.profile = profile
    return vessel


def _make_regulation(name='reg', policed_vessels=None):
    """Create a mock regulation."""
    reg = MagicMock()
    reg.get_name.return_value = name
    if policed_vessels is None:
        reg.vessel_is_policed.return_value = True
    else:
        reg.vessel_is_policed.side_effect = lambda v: v in policed_vessels
    return reg


def _make_levy(name='levy', policed_vessels=None):
    """Create a mock levy."""
    levy = MagicMock()
    levy.get_name.return_value = name
    if policed_vessels is None:
        levy.vessel_is_policed.return_value = True
    else:
        levy.vessel_is_policed.side_effect = lambda v: v in policed_vessels
    return levy


# accessors matching the calling convention in offsetting.py; production builds these as
# closures over the current time-step index, and every test below operates at idx 0.
_get_remedial = lambda p, n: p.get_remedial_units(n, 0)
_add_remedial = lambda p, n, d: p.add_remedial_units(n, 0, d)
_get_levy = lambda p, n: p.get_levy_units(n, 0)
_add_levy = lambda p, n, d: p.add_levy_units(n, 0, d)


class TestReclassifyVesselRemedialUnits:
    """Tests for _reclassify_vessel_remedial_units."""

    def test_remedial_units_reclassified_as_offset(self):
        """Per-vessel remedial units should become offsets."""
        v1 = _make_vessel('v1', remedial_units={'reg': 100.})
        vessels = {'v1': v1}
        multipliers = {'v1': 50.}
        regulation = _make_regulation(name='reg')
        idx = 0

        _reclassify_vessel_policy_units(regulation, vessels, multipliers, idx,
                                        _get_remedial, _add_remedial)

        assert abs(v1.profile._offset_arr[idx] - 100.) < 1e-6
        assert abs(v1.profile._remedial_data['reg'][idx]) < 1e-6

    def test_multiple_vessels_independent(self):
        """Each vessel's remedial units are independently reclassified."""
        v1 = _make_vessel('v1', remedial_units={'reg': 100.})
        v2 = _make_vessel('v2', remedial_units={'reg': 200.})
        vessels = {'v1': v1, 'v2': v2}
        multipliers = {'v1': 50., 'v2': 30.}
        regulation = _make_regulation(name='reg')
        idx = 0

        _reclassify_vessel_policy_units(regulation, vessels, multipliers, idx,
                                        _get_remedial, _add_remedial)

        assert abs(v1.profile._offset_arr[idx] - 100.) < 1e-6
        assert abs(v2.profile._offset_arr[idx] - 200.) < 1e-6
        assert abs(v1.profile._remedial_data['reg'][idx]) < 1e-6
        assert abs(v2.profile._remedial_data['reg'][idx]) < 1e-6

    def test_unpoliced_vessel_skipped(self):
        """Vessels not policed by the regulation should not be affected."""
        v1 = _make_vessel('v1', remedial_units={'reg': 100.})
        v2 = _make_vessel('v2', remedial_units={'reg': 200.})
        vessels = {'v1': v1, 'v2': v2}
        multipliers = {'v1': 50., 'v2': 30.}
        regulation = _make_regulation(name='reg', policed_vessels=['v1'])
        idx = 0

        _reclassify_vessel_policy_units(regulation, vessels, multipliers, idx,
                                        _get_remedial, _add_remedial)

        assert abs(v1.profile._offset_arr[idx] - 100.) < 1e-6
        # v2 unchanged
        assert abs(v2.profile._offset_arr[idx]) < 1e-6
        assert abs(v2.profile._remedial_data['reg'][idx] - 200.) < 1e-6

    def test_only_reclassifies_own_regulation(self):
        """Only remedial units from the target regulation should be reclassified."""
        v1 = _make_vessel('v1', remedial_units={'reg_a': 100., 'reg_b': 50.})
        vessels = {'v1': v1}
        multipliers = {'v1': 10.}
        regulation = _make_regulation(name='reg_a')
        idx = 0

        _reclassify_vessel_policy_units(regulation, vessels, multipliers, idx,
                                        _get_remedial, _add_remedial)

        # reg_a reclassified as offset
        assert abs(v1.profile._offset_arr[idx] - 100.) < 1e-6
        assert abs(v1.profile._remedial_data['reg_a'][idx]) < 1e-6
        # reg_b untouched
        assert abs(v1.profile._remedial_data['reg_b'][idx] - 50.) < 1e-6

    def test_zero_remedial_units_no_offset(self):
        """Vessels with no remedial units should not get offsets."""
        v1 = _make_vessel('v1', remedial_units={'reg': 0.})
        vessels = {'v1': v1}
        multipliers = {'v1': 50.}
        regulation = _make_regulation(name='reg')
        idx = 0

        _reclassify_vessel_policy_units(regulation, vessels, multipliers, idx,
                                        _get_remedial, _add_remedial)

        assert abs(v1.profile._offset_arr[idx]) < 1e-6

    def test_vessel_not_in_multipliers_skipped(self):
        """Vessels not in the multiplier map (inactive) should be skipped."""
        v1 = _make_vessel('v1', remedial_units={'reg': 100.})
        vessels = {'v1': v1}
        multipliers = {}  # v1 not present
        regulation = _make_regulation(name='reg')
        idx = 0

        _reclassify_vessel_policy_units(regulation, vessels, multipliers, idx,
                                        _get_remedial, _add_remedial)

        assert abs(v1.profile._offset_arr[idx]) < 1e-6
        assert abs(v1.profile._remedial_data['reg'][idx] - 100.) < 1e-6


class TestReclassifyVesselLevyUnits:
    """Tests for _reclassify_vessel_levy_units."""

    def test_levy_units_reclassified_as_offset(self):
        """Per-vessel levy units should become offsets."""
        v1 = _make_vessel('v1', levy_units={'levy_a': 50.})
        vessels = {'v1': v1}
        multipliers = {'v1': 10.}
        levy = _make_levy(name='levy_a')
        idx = 0

        _reclassify_vessel_policy_units(levy, vessels, multipliers, idx,
                                        _get_levy, _add_levy)

        assert abs(v1.profile._offset_arr[idx] - 50.) < 1e-6
        assert abs(v1.profile._levy_data['levy_a'][idx]) < 1e-6

    def test_only_reclassifies_own_levy(self):
        """Only units from the target levy should be reclassified."""
        v1 = _make_vessel('v1', levy_units={'levy_a': 50., 'levy_b': 30.})
        vessels = {'v1': v1}
        multipliers = {'v1': 10.}
        levy = _make_levy(name='levy_a')
        idx = 0

        _reclassify_vessel_policy_units(levy, vessels, multipliers, idx,
                                        _get_levy, _add_levy)

        assert abs(v1.profile._offset_arr[idx] - 50.) < 1e-6
        assert abs(v1.profile._levy_data['levy_a'][idx]) < 1e-6
        # levy_b untouched
        assert abs(v1.profile._levy_data['levy_b'][idx] - 30.) < 1e-6

    def test_unpoliced_vessel_skipped(self):
        """Vessels not policed by the levy should not be affected."""
        v1 = _make_vessel('v1', levy_units={'levy_a': 50.})
        v2 = _make_vessel('v2', levy_units={'levy_a': 30.})
        vessels = {'v1': v1, 'v2': v2}
        multipliers = {'v1': 10., 'v2': 10.}
        levy = _make_levy(name='levy_a', policed_vessels=['v1'])
        idx = 0

        _reclassify_vessel_policy_units(levy, vessels, multipliers, idx,
                                        _get_levy, _add_levy)

        assert abs(v1.profile._offset_arr[idx] - 50.) < 1e-6
        assert abs(v2.profile._offset_arr[idx]) < 1e-6
        assert abs(v2.profile._levy_data['levy_a'][idx] - 30.) < 1e-6


class TestPhysicalEmissionsAfterOffsetting:
    """Verify that offset emissions produce near-zero net physical emissions.

    Physical emissions = total equivalent WTW - offsets. When the LP's remedial
    units equal the vessel's total emissions (full non-compliance) and offsetting
    is cheaper than the remedial cost, all units become offsets, so the net
    physical emissions should be near zero.

    Note: small discrepancies are expected because regulatory emission factors
    (used for remedial units) may differ from physical emission factors (used
    for WTW totals). We therefore allow a tolerance rather than asserting
    exact zero.
    """

    @staticmethod
    def _make_fleet(vessel, multiplier, idx):
        """Create a mock fleet containing one vessel with a given multiplier."""
        expectation = MagicMock()
        expectation.get_existing_multipliers.return_value = multiplier
        fleet = MagicMock()
        fleet.get_vessels.return_value = [vessel]
        fleet.expectation = expectation
        return fleet

    @staticmethod
    def _make_model_definition(enable, cost):
        """Create a mock ModelDefinition for offsetting."""
        md = MagicMock()
        md.get_enable_offsetting.return_value = enable
        cost_obj = MagicMock()
        cost_obj.get.return_value = cost
        md.get_offsetting_cost.return_value = cost_obj
        return md

    @staticmethod
    def _make_regulation(name, active, allow_offsetting, remedial_cost,
                         remedial_units, remedial_expenses):
        """Create a mock regulation with profile data."""
        reg = MagicMock()
        reg.get_name.return_value = name
        reg.is_active.return_value = active
        reg.allow_offsetting = allow_offsetting
        reg.vessel_is_policed.return_value = True

        cost_obj = MagicMock()
        cost_obj.get.return_value = remedial_cost
        reg.remedial_cost = cost_obj

        profile = MagicMock()
        profile.get_remedial_units.side_effect = lambda idx: remedial_units
        profile.set_offsetting_units = MagicMock()
        profile.set_offsetting_expenses = MagicMock()
        profile.add_remedial_units = MagicMock()
        profile.add_remedial_expenses = MagicMock()
        reg.profile = profile
        reg.get_effective_offset_threshold.return_value = None
        return reg

    def test_regulation_offset_yields_near_zero_physical_emissions(self):
        """When all remedial units are offset, net physical emissions ~ 0."""
        total_wtw = 1000.  # vessel's total equivalent WTW emissions
        remedial_units = 1000.  # regulation penalises entire emission volume
        remedial_cost = 200.
        offsetting_cost = 50.  # cheaper than remedial -> triggers offsetting

        # build vessel whose remedial units equal its total WTW
        v1 = _make_vessel('v1', remedial_units={'reg': remedial_units})
        vessels = {'v1': v1}

        fleet = self._make_fleet(v1, multiplier=1., idx=0)
        fleets = {'fleet1': fleet}

        reg = self._make_regulation(
            name='reg', active=True, allow_offsetting=True,
            remedial_cost=remedial_cost,
            remedial_units=remedial_units, remedial_expenses=remedial_units * remedial_cost)

        model_def = self._make_model_definition(enable=True, cost=offsetting_cost)

        calculate_offsetting(
            regulations={'reg': reg}, levies={},
            vessels=vessels, fleets=fleets,
            model_definition=model_def, idx=0)

        # the vessel offset should equal the remedial units
        vessel_offset = v1.profile._offset_arr[0]
        assert abs(vessel_offset - remedial_units) < 1e-6

        # simulate physical emissions = total_wtw - offset
        physical_emissions = total_wtw - vessel_offset
        assert abs(physical_emissions) < 1e-6, (
            f"Expected near-zero physical emissions, got {physical_emissions}")

    def test_regulation_offset_with_emission_factor_discrepancy(self):
        """Regulatory and physical emission factors may differ, allowing a gap."""
        # physical WTW uses one factor, regulation uses another
        total_wtw = 1050.  # physical WTW slightly higher than regulatory
        remedial_units = 1000.  # regulatory emission volume
        remedial_cost = 200.
        offsetting_cost = 50.

        v1 = _make_vessel('v1', remedial_units={'reg': remedial_units})
        vessels = {'v1': v1}

        fleet = self._make_fleet(v1, multiplier=1., idx=0)
        fleets = {'fleet1': fleet}

        reg = self._make_regulation(
            name='reg', active=True, allow_offsetting=True,
            remedial_cost=remedial_cost,
            remedial_units=remedial_units,
            remedial_expenses=remedial_units * remedial_cost)

        model_def = self._make_model_definition(enable=True, cost=offsetting_cost)

        calculate_offsetting(
            regulations={'reg': reg}, levies={},
            vessels=vessels, fleets=fleets,
            model_definition=model_def, idx=0)

        vessel_offset = v1.profile._offset_arr[0]

        # physical emissions with factor discrepancy
        physical_emissions = total_wtw - vessel_offset
        # should be small relative to total WTW (within 5% tolerance for factor mismatch)
        assert physical_emissions >= 0., "Physical emissions should not go negative"
        assert physical_emissions / total_wtw < 0.05, (
            f"Physical emissions {physical_emissions} are too large relative to WTW {total_wtw}")

    def test_levy_offset_yields_near_zero_physical_emissions(self):
        """When all levy units are offset, net physical emissions ~ 0."""
        total_wtw = 500.
        levy_units = 500.
        levy_level = 100.
        offsetting_cost = 30.
        collected = levy_units * offsetting_cost  # LP used truncated cost

        v1 = _make_vessel('v1', levy_units={'levy_a': levy_units})
        vessels = {'v1': v1}

        fleet = self._make_fleet(v1, multiplier=1., idx=0)
        fleets = {'fleet1': fleet}

        levy = MagicMock()
        levy.get_name.return_value = 'levy_a'
        levy.is_active.return_value = True
        levy.allow_offsetting = True
        levy.scheme = LevySchemeID.PENALTY
        levy.vessel_is_policed.return_value = True

        level_obj = MagicMock()
        level_obj.get.return_value = levy_level
        levy.level = level_obj

        profile = MagicMock()
        profile.get_collected.return_value = collected
        profile.set_offsetting_units = MagicMock()
        profile.set_offsetting_expenses = MagicMock()
        profile.set_collected = MagicMock()
        levy.profile = profile

        model_def = self._make_model_definition(enable=True, cost=offsetting_cost)

        calculate_offsetting(
            regulations={}, levies={'levy_a': levy},
            vessels=vessels, fleets=fleets,
            model_definition=model_def, idx=0)

        vessel_offset = v1.profile._offset_arr[0]
        assert abs(vessel_offset - levy_units) < 1e-6

        physical_emissions = total_wtw - vessel_offset
        assert abs(physical_emissions) < 1e-6, (
            f"Expected near-zero physical emissions, got {physical_emissions}")

    def test_disabled_offsetting_leaves_physical_emissions_unchanged(self):
        """When offsetting is disabled, no offsets are applied."""
        v1 = _make_vessel('v1', remedial_units={'reg': 1000.})
        vessels = {'v1': v1}

        fleet = self._make_fleet(v1, multiplier=1., idx=0)
        fleets = {'fleet1': fleet}

        model_def = self._make_model_definition(enable=False, cost=50.)

        calculate_offsetting(
            regulations={'reg': MagicMock()}, levies={},
            vessels=vessels, fleets=fleets,
            model_definition=model_def, idx=0)

        # no offset applied
        assert abs(v1.profile._offset_arr[0]) < 1e-6
