# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for wildcard support in core assign, util, and node references."""
import pytest

from navigate.core.assign import assign_id_list, assign_list, assign_value, expand_id_wildcard
from navigate.core.enum_ import EnergyDemandTypeID, FuelTypeID
from navigate.core.id_ import FUEL, PORT
from navigate.core.node_reference import NodeReference, WildcardNodeReference
from navigate.util import retrieve_keys

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
        with pytest.raises(ValueError, match="wildcard.*did not match"):
            expand_id_wildcard("Z*", FuelTypeID)

    def test_exact_name_matches_single(self):
        result = expand_id_wildcard("AMMONIA", FuelTypeID)
        assert result == [FuelTypeID.AMMONIA]


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


# ── retrieve_keys with enum-keyed dicts ───────────────────────────────────────

class TestRetrieveKeysEnum:

    _key_fn = staticmethod(lambda k: k.name)

    def test_wildcard_matches_enum_names(self):
        d = {FuelTypeID.METHANE: 1, FuelTypeID.METHANOL: 2, FuelTypeID.OIL: 3}
        result = retrieve_keys("M*", d, key_fn=self._key_fn)
        assert set(result) == {FuelTypeID.METHANE, FuelTypeID.METHANOL}

    def test_exact_enum_name_matches(self):
        d = {FuelTypeID.OIL: 1, FuelTypeID.AMMONIA: 2}
        result = retrieve_keys("OIL", d, key_fn=self._key_fn)
        assert result == [FuelTypeID.OIL]

    def test_no_match_raises(self):
        d = {FuelTypeID.OIL: 1}
        with pytest.raises(KeyError):
            retrieve_keys("Z*", d, key_fn=self._key_fn)

    def test_non_string_key_passthrough(self):
        result = retrieve_keys(FuelTypeID.OIL, {FuelTypeID.OIL: 1})
        assert result == [FuelTypeID.OIL]

    def test_star_matches_all_enum_keys(self):
        d = {e: i for i, e in enumerate(EnergyDemandTypeID)}
        result = retrieve_keys("*", d, key_fn=self._key_fn)
        assert set(result) == set(EnergyDemandTypeID)


# ── WildcardNodeReference ─────────────────────────────────────────────────────

class TestWildcardNodeReference:

    def test_basic_attributes(self):
        ref = WildcardNodeReference("Fuel", "bio_*")
        assert ref.get_type() == "Fuel"
        assert ref.pattern == "bio_*"

    def test_repr(self):
        ref = WildcardNodeReference("Vessel", "container_*")
        assert repr(ref) == 'Vessel("container_*")'

    def test_reference_location(self):
        ref = WildcardNodeReference("Fuel", "*")
        ref.reference_location = "test.inc:5"
        assert ref.reference_location == "test.inc:5"

    def test_is_node_reference_subclass(self):
        ref = WildcardNodeReference("Fuel", "*")
        assert isinstance(ref, NodeReference)

    def test_get_name_returns_pattern(self):
        ref = WildcardNodeReference("Fuel", "bio_*")
        assert ref.get_name() == "bio_*"

    def test_inherited_set_internal_bounds_is_callable(self):
        ref = WildcardNodeReference("Fuel", "*")
        ref.set_internal_bounds(0.0, 1.0)
        assert ref.internal_bounds == (0.0, 1.0)


# ── assign_value / assign_list accept WildcardNodeReference ───────────────────

class TestAssignValueWildcardNodeReference:

    def test_assign_value_accepts_matching_type(self):
        ref = WildcardNodeReference(FUEL, "*")
        result = assign_value(ref, scalar=False, type_=FUEL)
        assert result is ref

    def test_assign_value_rejects_mismatched_type(self):
        ref = WildcardNodeReference(FUEL, "*")
        with pytest.raises(ValueError):
            assign_value(ref, scalar=False, type_=PORT)

    def test_assign_list_accepts_wildcard_entries(self):
        entries = [WildcardNodeReference(FUEL, "bio_*"), WildcardNodeReference(FUEL, "fossil_*")]
        result = assign_list(entries, unique=True, scalar=False, type_=FUEL)
        assert result == entries
