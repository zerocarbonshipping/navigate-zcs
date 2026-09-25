# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests for the assignment-boundary wrappers shared by the DSL setters."""

from __future__ import annotations

import numpy as np
import pytest

from navigate.core.scalar import Scalar
from navigate.core.wrap import as_list, as_scalar

# ── as_scalar ─────────────────────────────────────────────────────────────────


class TestAsScalar:
    @pytest.mark.parametrize(
        "value",
        [1.0, 0.0, -2.5, np.float64(3.0)],
        ids=["positive", "zero", "negative", "numpy_float"],
    )
    def test_float_is_wrapped(self, value):
        wrapped = as_scalar(value)
        assert isinstance(wrapped, Scalar)
        assert wrapped.get() == value

    @pytest.mark.parametrize(
        "value",
        [3, True, "OIL", np.datetime64("2024-01-01", "D")],
        ids=["int", "bool", "str", "date"],
    )
    def test_non_float_is_not_wrapped(self, value):
        # the discrimination is isinstance(value, float): int and bool are
        # deliberately outside it, so a deck typo reaches assign_value unwrapped
        assert not isinstance(as_scalar(value), Scalar)


# ── as_list ───────────────────────────────────────────────────────────────────


class TestAsList:
    def test_tuple_becomes_list(self):
        assert as_list((1.0, 2.0)) == [1.0, 2.0]

    @pytest.mark.parametrize(
        "value",
        [1.0, "OIL"],
        ids=["float", "str"],
    )
    def test_bare_value_is_promoted(self, value):
        assert as_list(value) == [value]

    def test_list_is_not_nested(self):
        assert as_list([1.0, 2.0]) == [1.0, 2.0]
