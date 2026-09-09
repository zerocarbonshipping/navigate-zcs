# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests for the yearly cash-flow helpers (navigate/economics/flows.py)."""
import numpy as np

from navigate.core.unit import YEAR_TO_DAYS
from navigate.economics.flows import (
    Component,
    build_operating_flows,
    get_flow_residual,
    get_flow_size,
    trim_flow_to_lifetime,
)


class TestGetFlowSize:

    def test_whole_years(self):
        assert get_flow_size(lead_time=2., lifetime=4.) == 6

    def test_fractional_lifetime_rounds_up(self):
        assert get_flow_size(lead_time=0., lifetime=4.5) == 5

    def test_fuzz_collapses_to_year_boundary(self):
        assert get_flow_size(lead_time=0., lifetime=4. + 1e-9) == 4


class TestBuildOperatingFlows:

    def test_whole_years(self):
        year_flow, overlap = build_operating_flows(time_initial=10. * YEAR_TO_DAYS, lead_time=2., lifetime=3.)
        np.testing.assert_array_almost_equal(year_flow, np.array([10., 11., 12., 13., 14.]) * YEAR_TO_DAYS)
        np.testing.assert_array_almost_equal(overlap, [0., 0., 1., 1., 1.])

    def test_fractional_lead_time_prorates_commissioning_year(self):
        # operation runs from the end of the lead time to the end of the
        # flow horizon, so only the commissioning year is prorated
        year_flow, overlap = build_operating_flows(time_initial=0., lead_time=1.5, lifetime=3.)
        np.testing.assert_array_almost_equal(year_flow, np.arange(5.) * YEAR_TO_DAYS)
        np.testing.assert_array_almost_equal(overlap, [0., 0.5, 1., 1., 1.])

    def test_matches_component_window(self):
        # the delivery-cost levelization builds its operating window through
        # this helper while the production-cost levelization builds it through
        # Component; both must describe the same window for the levelized
        # delivered cost to be a consistent sum of the two
        component = Component()
        component.initialize_flow(lead_time=1.5, lifetime=3., time_initial=7. * YEAR_TO_DAYS)

        year_flow, overlap = build_operating_flows(time_initial=7. * YEAR_TO_DAYS, lead_time=1.5, lifetime=3.)

        np.testing.assert_array_almost_equal(year_flow, component.year_flow)
        np.testing.assert_array_almost_equal(overlap, component.constant_overlap)


class TestGetFlowResidual:

    def test_whole_lifetime_is_not_partial(self):
        assert get_flow_residual(4.) == (False, 0.)

    def test_fractional_lifetime_prorates(self):
        partial, residual = get_flow_residual(4.5)
        assert partial
        np.testing.assert_almost_equal(residual, 0.5)

    def test_fuzz_collapses_to_year_boundary(self):
        assert get_flow_residual(4. + 1e-9) == (False, 0.)


class TestTrimFlowToLifetime:

    def test_integer_lifetime_slices_whole_years(self):
        flow = np.arange(10.)
        np.testing.assert_array_equal(trim_flow_to_lifetime(flow, 4.), [0., 1., 2., 3.])

    def test_fractional_lifetime_prorates_final_year(self):
        flow = np.full(10, 2.)
        np.testing.assert_array_almost_equal(trim_flow_to_lifetime(flow, 4.5), [2., 2., 2., 2., 1.])

    def test_lifetime_rounded_against_float_fuzz(self):
        flow = np.full(10, 2.)
        np.testing.assert_array_equal(trim_flow_to_lifetime(flow, 4. + 1e-9),
                                      trim_flow_to_lifetime(flow, 4.))

    def test_input_flow_untouched(self):
        flow = np.full(10, 2.)
        trim_flow_to_lifetime(flow, 4.5)
        np.testing.assert_array_equal(flow, np.full(10, 2.))
