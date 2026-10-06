# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests for the yearly cash-flow helpers (navigate/economics/flows.py)."""

from __future__ import annotations

import numpy as np
import pytest

from navigate.core.unit import YEAR_TO_DAYS
from navigate.economics.flows import (
    Component,
    build_operating_flows,
    get_flow_size,
    trim_flow_to_lifetime,
)


@pytest.mark.parametrize(
    ("lifetime", "expected"),
    [
        pytest.param(4.5, 5, id="fractional_rounds_up"),
        pytest.param(4.0 + 1e-9, 4, id="fuzz_collapses_to_year_boundary"),
    ],
)
def test_get_flow_size(lifetime, expected):
    assert get_flow_size(lead_time=0.0, lifetime=lifetime) == expected


class TestBuildOperatingFlows:
    @pytest.mark.parametrize(
        ("time_initial", "lead_time", "expected_overlap"),
        [
            pytest.param(10.0, 2.0, [0.0, 0.0, 1.0, 1.0, 1.0], id="whole_years"),
            # operation runs from the end of the lead time to the end of the
            # flow horizon, so only the commissioning year is prorated
            pytest.param(0.0, 1.5, [0.0, 0.5, 1.0, 1.0, 1.0], id="fractional_lead"),
        ],
    )
    def test_overlap_is_zero_under_construction(
        self, time_initial, lead_time, expected_overlap
    ):
        year_flow, overlap = build_operating_flows(
            time_initial=time_initial * YEAR_TO_DAYS, lead_time=lead_time, lifetime=3.0
        )
        np.testing.assert_array_almost_equal(
            year_flow, (time_initial + np.arange(5.0)) * YEAR_TO_DAYS
        )
        np.testing.assert_array_almost_equal(overlap, expected_overlap)

    def test_matches_component_window(self):
        # the delivery-cost levelization builds its operating window through
        # this helper while the production-cost levelization builds it through
        # Component; both must describe the same window for the levelized
        # delivered cost to be a consistent sum of the two
        component = Component(
            lead_time=1.5, lifetime=3.0, time_initial=7.0 * YEAR_TO_DAYS
        )

        year_flow, overlap = build_operating_flows(
            time_initial=7.0 * YEAR_TO_DAYS, lead_time=1.5, lifetime=3.0
        )

        np.testing.assert_array_almost_equal(year_flow, component.year_flow)
        np.testing.assert_array_almost_equal(overlap, component.constant_overlap)


class TestTrimFlowToLifetime:
    @pytest.mark.parametrize(
        ("lifetime", "expected"),
        [
            pytest.param(4.0, [2.0, 2.0, 2.0, 2.0], id="integer"),
            pytest.param(4.0 + 1e-9, [2.0, 2.0, 2.0, 2.0], id="float_fuzz"),
            pytest.param(4.5, [2.0, 2.0, 2.0, 2.0, 1.0], id="fractional_prorates"),
        ],
    )
    def test_trims_to_lifetime(self, lifetime, expected):
        flow = np.full(10, 2.0)
        np.testing.assert_array_almost_equal(
            trim_flow_to_lifetime(flow, lifetime), expected
        )

    def test_input_flow_untouched(self):
        flow = np.full(10, 2.0)
        trim_flow_to_lifetime(flow, 4.5)
        np.testing.assert_array_equal(flow, np.full(10, 2.0))
