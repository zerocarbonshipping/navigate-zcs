# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The element-wise sum every profile's total getters build on."""

from __future__ import annotations

import numpy as np

from navigate.core.profiles._base_profile import _BaseProfile

TIMELINE = np.array([0.0, 1.0, 2.0])


def _profile():
    profile = _BaseProfile()
    profile._initialize_base(TIMELINE)
    return profile


def test_an_empty_dict_sums_to_a_zero_timeline():
    # a deck with no Emission node hands the sum an empty dict keyed by emission
    total = _profile()._sum_values({})

    # assert_array_equal broadcasts a scalar, so the shape is checked apart
    assert total.shape == TIMELINE.shape
    np.testing.assert_array_equal(total, 0.0)


def test_the_values_are_summed_element_wise():
    values = {"co2": np.array([1.0, 2.0, 3.0]), "ch4": np.array([0.5, 0.0, 4.0])}

    total = _profile()._sum_values(values)

    np.testing.assert_array_equal(total, [1.5, 2.0, 7.0])
