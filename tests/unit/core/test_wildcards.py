# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for wildcard expansion of IDs and of command keys."""

from __future__ import annotations

import pytest

from navigate.core.assign import assign_id_list, expand_id_wildcard
from navigate.core.enum_ import (
    EnergyDemandTypeID,
    EnergyDemandTypePortID,
    FuelTypeID,
)
from navigate.util import retrieve_keys

# ── expand_id_wildcard ────────────────────────────────────────────────────────


class TestExpandIdWildcard:
    @pytest.mark.parametrize(
        ("pattern", "expected"),
        [
            ("*", set(FuelTypeID)),
            ("M*", {FuelTypeID.METHANE, FuelTypeID.METHANOL}),
            ("OI?", {FuelTypeID.OIL}),
            ("AMMONIA", {FuelTypeID.AMMONIA}),
        ],
        ids=["star", "prefix", "question_mark", "exact"],
    )
    def test_expands_to_the_matching_members(self, pattern, expected):
        assert set(expand_id_wildcard(pattern, FuelTypeID)) == expected

    def test_no_match_raises(self):
        with pytest.raises(ValueError, match=r"wildcard 'Z\*' did not match any of "):
            expand_id_wildcard("Z*", FuelTypeID)

    def test_member_tuple_domain_expands_to_its_members(self):
        # a command whose attribute holds a subset of the enum registers that
        # subset, so the expansion stays inside what the attribute holds
        result = expand_id_wildcard("*", EnergyDemandTypePortID)
        assert set(result) == {EnergyDemandTypeID.ELECTRICAL, EnergyDemandTypeID.HEAT}


# ── assign_id_list with wildcards ─────────────────────────────────────────────


class TestAssignIdListWildcard:
    def test_wildcard_and_exact_entries_expand_in_place(self):
        result = assign_id_list(["OIL", "M*"], FuelTypeID)
        assert result == [FuelTypeID.OIL, FuelTypeID.METHANE, FuelTypeID.METHANOL]

    def test_length_check_after_expansion(self):
        result = assign_id_list(["M*"], FuelTypeID, min_length=2)
        assert {FuelTypeID.METHANE, FuelTypeID.METHANOL} <= set(result)


# ── retrieve_keys ─────────────────────────────────────────────────────────────


def test_retrieve_keys_rejects_an_absent_non_string_key():
    # returning the key unchecked let a command write an entry outside the
    # prepopulated set, where nothing reads it (CODESTYLE: dictionaries keyed
    # by nodes or enum members are prepopulated at initialization). The key is
    # named, not carried: a KeyError renders its argument with 'repr', so the
    # member itself would reach the deck error as <FuelTypeID.OIL: 1> rather
    # than 'OIL'
    with pytest.raises(KeyError, match=r"^'OIL'$"):
        retrieve_keys(FuelTypeID.OIL, {FuelTypeID.AMMONIA: 1})
