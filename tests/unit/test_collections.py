# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.util.collections."""

from __future__ import annotations

import numpy as np

from navigate.util import add_dicts


def test_add_dicts_leaves_its_inputs_unmutated_and_unaliased():
    first_value = np.array([1.0, 2.0])
    second_value = np.array([3.0, 4.0])
    result = add_dicts({"a": first_value}, {"a": second_value, "b": second_value})

    np.testing.assert_array_equal(first_value, [1.0, 2.0])
    np.testing.assert_array_equal(second_value, [3.0, 4.0])
    assert not np.shares_memory(result["a"], first_value)
    assert not np.shares_memory(result["b"], second_value)
