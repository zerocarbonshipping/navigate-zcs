# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for wildcard support in core assign, util, and node references."""

from __future__ import annotations

import pytest

from navigate.core.assign import assign_id_list, expand_id_wildcard
from navigate.core.enum_ import (
    EnergyDemandTypeID,
    EnergyDemandTypePortID,
    FuelTypeID,
)
from navigate.util import matching_keys, retrieve_keys

# ── expand_id_wildcard ────────────────────────────────────────────────────────


class TestExpandIdWildcard:
    def test_star_matches_all(self):
        result = expand_id_wildcard("*", FuelTypeID)
        assert set(result) == set(FuelTypeID)

    def test_prefix_pattern(self):
        result = expand_id_wildcard("M*", FuelTypeID)
        assert FuelTypeID.METHANE in result
        assert FuelTypeID.METHANOL in result
        assert FuelTypeID.OIL not in result

    def test_question_mark(self):
        result = expand_id_wildcard("OI?", FuelTypeID)
        assert result == [FuelTypeID.OIL]

    def test_no_match_raises(self):
        with pytest.raises(ValueError, match=r"wildcard 'Z\*' did not match any of "):
            expand_id_wildcard("Z*", FuelTypeID)

    def test_exact_name_matches_single(self):
        result = expand_id_wildcard("AMMONIA", FuelTypeID)
        assert result == [FuelTypeID.AMMONIA]

    @pytest.mark.parametrize(
        ("pattern", "expected"),
        [
            ("*", {EnergyDemandTypeID.ELECTRICAL, EnergyDemandTypeID.HEAT}),
            ("H*", {EnergyDemandTypeID.HEAT}),
            ("?LECTRICAL", {EnergyDemandTypeID.ELECTRICAL}),
        ],
        ids=["star", "prefix", "question_mark"],
    )
    def test_member_tuple_domain_expands_to_its_members(self, pattern, expected):
        # a command whose attribute holds a subset of the enum registers that
        # subset, so the expansion stays inside what the attribute holds
        result = expand_id_wildcard(pattern, EnergyDemandTypePortID)
        assert set(result) == expected

    def test_member_tuple_domain_rejects_excluded_member(self):
        with pytest.raises(
            ValueError,
            match=r"wildcard 'P\*' did not match any of ELECTRICAL, HEAT$",
        ):
            expand_id_wildcard("P*", EnergyDemandTypePortID)


# ── assign_id_list with wildcards ─────────────────────────────────────────────


class TestAssignIdListWildcard:
    def test_wildcard_in_list_expands(self):
        result = assign_id_list(["M*"], FuelTypeID)
        assert FuelTypeID.METHANE in result
        assert FuelTypeID.METHANOL in result

    def test_mixed_wildcard_and_exact(self):
        result = assign_id_list(["OIL", "M*"], FuelTypeID)
        assert result[0] == FuelTypeID.OIL
        assert FuelTypeID.METHANE in result
        assert FuelTypeID.METHANOL in result

    def test_length_check_after_expansion(self):
        with pytest.raises(ValueError, match="must contain exactly"):
            assign_id_list(["*"], FuelTypeID, length=2)

    def test_no_wildcard_unchanged(self):
        result = assign_id_list(["HYDROGEN"], FuelTypeID)
        assert result == [FuelTypeID.HYDROGEN]


# ── retrieve_keys ─────────────────────────────────────────────────────────────


class TestRetrieveKeys:
    def test_no_match_raises(self):
        with pytest.raises(KeyError):
            retrieve_keys("Z*", {"OIL": 1})

    def test_non_string_key_passthrough(self):
        result = retrieve_keys(FuelTypeID.OIL, {FuelTypeID.OIL: 1})
        assert result == [FuelTypeID.OIL]

    @pytest.mark.parametrize(
        "allowed_keys",
        [{FuelTypeID.AMMONIA: 1}, (FuelTypeID.AMMONIA,), {}],
        ids=["dict", "tuple", "empty"],
    )
    def test_absent_non_string_key_raises(self, allowed_keys):
        # returning the key unchecked let a command write an entry outside the
        # prepopulated set, where nothing reads it (CODESTYLE: dictionaries
        # keyed by nodes or enum members are prepopulated at initialization).
        # The key is named, not carried: a KeyError renders its argument with
        # 'repr', so the member itself would reach the deck error as
        # <FuelTypeID.OIL: 1> rather than 'OIL'
        with pytest.raises(KeyError, match=r"^'OIL'$"):
            retrieve_keys(FuelTypeID.OIL, allowed_keys)


# ── matching_keys ─────────────────────────────────────────────────────────────


class TestMatchingKeys:
    @pytest.mark.parametrize(
        ("pattern", "keys", "expected"),
        [
            ("a", {"a": 1, "b": 2}, {"a"}),
            ("a*", {"a1": 1, "a2": 2, "b": 3}, {"a1", "a2"}),
            ("z", {"a": 1}, set()),
            ("z*", {"a": 1}, set()),
        ],
    )
    def test_matches(self, pattern, keys, expected):
        assert set(matching_keys(pattern, keys)) == expected
