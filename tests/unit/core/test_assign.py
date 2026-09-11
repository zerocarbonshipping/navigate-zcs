# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for ID validation in navigate.core.assign, shared by every set_* ID setter."""

from __future__ import annotations

import pytest

from navigate.core.assign import BOOL_ID, assign_id
from navigate.core.enum_ import FuelTypeID


class TestAssignId:
    @pytest.mark.parametrize(
        "assignment, id_enum, expected",
        [
            ("TRUE", BOOL_ID, True),
            ("FALSE", BOOL_ID, False),
            ("OIL", FuelTypeID, FuelTypeID.OIL),
        ],
    )
    def test_member_lookup(self, assignment, id_enum, expected):
        assert assign_id(assignment, id_enum) == expected

    def test_unknown_id_raises(self):
        with pytest.raises(ValueError, match="does not accept ID"):
            assign_id("MAYBE", BOOL_ID)

    def test_wildcard_raises_dedicated_message(self):
        with pytest.raises(ValueError, match="wildcards are not supported"):
            assign_id("M*", FuelTypeID)
