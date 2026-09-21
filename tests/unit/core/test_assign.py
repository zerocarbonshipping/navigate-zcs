# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Tests for navigate.core.assign, the validation boundary behind every setter.

CODESTYLE's "Input validation and dynamic access" makes this module the one
place that checks deck input, so these pin the messages and the accept/reject
rules the DSL reference promises. Messages are sentence fragments because
``Parser._apply_assignment`` prefixes them with the node and attribute.
"""

from __future__ import annotations

import numpy as np
import pytest

from navigate.core.assign import (
    _check_scalar,
    assign_boolean,
    assign_bound,
    assign_fraction_list,
    assign_id,
    assign_integer,
    assign_list,
    assign_value,
    command_assignment_to_boolean_dict,
    command_assignment_to_dict,
    command_assignment_to_tuple_dict,
)
from navigate.core.enum_ import FuelTypeID
from navigate.core.expression import Expression
from navigate.core.node_type import FORECAST, FUEL, VARIABLE
from navigate.core.nodes.curve import Curve
from navigate.core.nodes.forecast import Forecast
from navigate.core.nodes.fuel import Fuel
from navigate.core.nodes.variable import Variable
from navigate.core.scalar import Scalar
from navigate.core.table_data import TableData
from navigate.core.wildcard import WildcardNodeReference

DATE = np.datetime64("2024-01-01", "D")


# ── assign_id ─────────────────────────────────────────────────────────────────


class TestAssignId:
    def test_member_lookup(self):
        assert assign_id("OIL", FuelTypeID) is FuelTypeID.OIL

    def test_unknown_id_raises(self):
        with pytest.raises(ValueError, match="does not accept ID"):
            assign_id("MAYBE", FuelTypeID)

    def test_wildcard_raises_dedicated_message(self):
        with pytest.raises(ValueError, match="wildcards are not supported"):
            assign_id("M*", FuelTypeID)


# ── assign_bound ──────────────────────────────────────────────────────────────


class TestAssignBound:
    @pytest.mark.parametrize(
        ("assignment", "expected"),
        [("-INF", -np.inf), ("INF", np.inf)],
    )
    def test_keyword_lookup(self, assignment, expected):
        assert assign_bound(assignment) == expected

    @pytest.mark.parametrize(
        "assignment",
        ["MAYBE", "inf", ""],
        ids=["unknown", "wrong_case", "empty"],
    )
    def test_other_token_rejected_as_a_value_error(self, assignment):
        # a ValueError is what the parser turns into a deck-located message; a
        # KeyError would be reported as a missing name instead
        with pytest.raises(
            ValueError,
            match="only allows assignment of scalars, -INF or INF, but got",
        ):
            assign_bound(assignment)

    @pytest.mark.parametrize("assignment", [-2.0, 0.0, 1e30])
    def test_scalar_returned(self, assignment):
        assert assign_bound(assignment) == assignment

    @pytest.mark.parametrize(
        "assignment",
        [3, True, [1.0, 2.0], TableData(rows=[[1.0, 2.0]]), DATE, Curve("c")],
        ids=["integer", "boolean", "list", "table", "date", "node"],
    )
    def test_non_scalar_rejected_as_a_value_error(self, assignment):
        # the bound setters route everything that is not a float here, and an
        # unhashable value must not escape the keyword lookup as a TypeError
        with pytest.raises(
            ValueError,
            match="only allows assignment of scalars, -INF or INF, but got",
        ):
            assign_bound(assignment)


# ── assign_boolean ────────────────────────────────────────────────────────────


class TestAssignBoolean:
    @pytest.mark.parametrize(
        ("assignment", "expected"),
        [("TRUE", True), ("FALSE", False)],
    )
    def test_keyword_lookup(self, assignment, expected):
        assert assign_boolean(assignment) is expected

    @pytest.mark.parametrize(
        "assignment",
        ["MAYBE", "true", ""],
        ids=["unknown", "wrong_case", "empty"],
    )
    def test_other_token_rejected_as_a_value_error(self, assignment):
        # a ValueError is what the parser turns into a deck-located message; a
        # KeyError would be reported as a missing name instead
        with pytest.raises(
            ValueError, match="only allows assignment of TRUE or FALSE, but got"
        ):
            assign_boolean(assignment)


# ── _check_scalar ─────────────────────────────────────────────────────────────


class TestCheckScalar:
    @pytest.mark.parametrize(
        "assignment",
        [1.0, Scalar(1.0)],
        ids=["float", "wrapped_float"],
    )
    def test_accepts_scalar_within_bounds(self, assignment):
        assert _check_scalar(assignment, lower=0.0, upper=2.0) is None

    def test_unbounded_by_default(self):
        assert _check_scalar(1e30) is None

    @pytest.mark.parametrize(
        "assignment",
        [3, "OIL", None],
        ids=["int", "str", "none"],
    )
    def test_rejects_non_scalar(self, assignment):
        with pytest.raises(ValueError, match="requires a scalar"):
            _check_scalar(assignment)

    @pytest.mark.parametrize(
        ("value", "bounds"),
        [
            (0.0, {"lower": 0.0, "inclusive_lower": True}),
            (2.0, {"upper": 2.0, "inclusive_upper": True}),
        ],
        ids=["on_inclusive_lower", "on_inclusive_upper"],
    )
    def test_value_on_inclusive_bound_accepted(self, value, bounds):
        assert _check_scalar(value, **bounds) is None

    @pytest.mark.parametrize(
        ("value", "bounds", "message"),
        [
            (0.0, {"lower": 0.0, "inclusive_lower": False}, r"must be > 0\.0"),
            (2.0, {"upper": 2.0, "inclusive_upper": False}, r"must be < 2\.0"),
            (-1.0, {"lower": 0.0}, r"must be ≥ 0\.0"),
            (3.0, {"upper": 2.0}, r"must be ≤ 2\.0"),
        ],
        ids=["on_exclusive_lower", "on_exclusive_upper", "below_lower", "above_upper"],
    )
    def test_out_of_bounds_rejected(self, value, bounds, message):
        with pytest.raises(ValueError, match=message):
            _check_scalar(value, **bounds)


# ── assign_integer ────────────────────────────────────────────────────────────


class TestAssignInteger:
    @pytest.mark.parametrize(
        ("assignment", "expected"),
        [(5.0, 5), (-3.0, -3), (0.0, 0)],
        ids=["positive", "negative", "zero"],
    )
    def test_whole_float_becomes_int(self, assignment, expected):
        result = assign_integer(assignment)
        assert result == expected
        assert isinstance(result, int)

    @pytest.mark.parametrize(
        ("assignment", "expected"),
        [(3.000001, 3), (2.999999, 3), (-2.999999, -3), (-3.000001, -3)],
        ids=["above", "below", "negative_above", "negative_below"],
    )
    def test_tolerance_is_symmetric(self, assignment, expected):
        # TOLERANCE (1e-5) forgives a deck value written just off a whole
        # number, and forgives it equally on either side of that number
        assert assign_integer(assignment) == expected

    @pytest.mark.parametrize(
        "assignment",
        [2.5, 2.99, 3.01],
        ids=["half", "below_outside_tolerance", "above_outside_tolerance"],
    )
    def test_fractional_value_rejected(self, assignment):
        with pytest.raises(ValueError, match="only allows assignment of integers"):
            assign_integer(assignment)

    def test_int_argument_rejected(self):
        # the DSL only ever produces floats; _check_scalar guards the boundary,
        # naming the kind it got rather than echoing a value that reads as one
        with pytest.raises(ValueError, match="requires a scalar, but got integer"):
            assign_integer(3)

    def test_bounds_checked_before_rounding(self):
        with pytest.raises(ValueError, match=r"must be ≥ 1\.0"):
            assign_integer(0.0, lower=1.0)

    def test_exclusive_bound_forwarded(self):
        with pytest.raises(ValueError, match=r"must be > 1\.0"):
            assign_integer(1.0, lower=1.0, inclusive_lower=False)


# ── assign_value ──────────────────────────────────────────────────────────────


class TestAssignValue:
    @pytest.mark.parametrize(
        "assignment",
        [9.0, Scalar(9.0)],
        ids=["float", "wrapped_float"],
    )
    def test_bounds_forwarded(self, assignment):
        with pytest.raises(ValueError, match=r"must be ≤ 1\.0"):
            assign_value(assignment, lower=0.0, upper=1.0)

    def test_scalar_rejected_when_not_allowed(self):
        with pytest.raises(ValueError, match="but got scalar"):
            assign_value(5.0, scalar=False, type_=FORECAST)

    def test_date_rejected_by_default(self):
        with pytest.raises(ValueError, match="but got date"):
            assign_value(DATE)

    def test_date_accepted_when_allowed(self):
        assert assign_value(DATE, scalar=False, date=True) == DATE

    @pytest.mark.parametrize(
        "assignment",
        [[1.0], (1.0,)],
        ids=["list", "tuple"],
    )
    def test_sequence_rejected(self, assignment):
        with pytest.raises(ValueError, match="but got list"):
            assign_value(assignment)

    def test_node_rejected_when_no_type_is_allowed(self):
        # the shape of every scalar-only setter; a setter allowing no kind at
        # all is an implementation error and is not a configuration under test
        with pytest.raises(
            ValueError,
            match=r'only allows assignment of scalars, but got Forecast\("f"\)',
        ):
            assign_value(Forecast("f"))

    @pytest.mark.parametrize(
        "node_class",
        [Forecast, Variable],
        ids=["first_member", "last_member"],
    )
    def test_tuple_type_accepts_any_member(self, node_class):
        # the shape the Vessel and machinery OPEX setters pass
        node = node_class("n")
        assert assign_value(node, type_=(FORECAST, VARIABLE)) is not None

    def test_tuple_type_rejects_non_member(self):
        with pytest.raises(
            ValueError, match="nodes of type Forecast or Variable, but got Curve"
        ):
            assign_value(Curve("c"), type_=(FORECAST, VARIABLE))

    @pytest.mark.parametrize(
        ("assignment", "arguments", "message"),
        [
            ("FLAT", {}, "only allows assignment of scalars, but got FLAT"),
            ("FLAT", {"type_": FORECAST}, "nodes of type Forecast, but got FLAT"),
            (3, {}, "only allows assignment of scalars, but got integer"),
            (True, {}, "only allows assignment of scalars, but got boolean"),
            (None, {}, "only allows assignment of scalars, but got None"),
        ],
        ids=["token", "token_with_allowed_types", "int", "bool", "none"],
    )
    def test_unrecognized_value_rejected(self, assignment, arguments, message):
        # a typo such as 'Capex = FLAT' arrives as a str, and an int or a bool
        # is deliberately left unwrapped by as_scalar (test_wrap.py), so this
        # is the boundary that has to refuse all of them. An int is named by
        # its kind, never echoed: 'but got 3' under 'only allows scalars'
        # contradicts itself for anyone who has not read as_scalar
        with pytest.raises(ValueError, match=message):
            assign_value(assignment, **arguments)

    def test_table_is_rejected_by_kind(self):
        # a pasted table body is named like a list, not echoed row by row
        table = TableData(rows=[[2020.0, 1e6], [2030.0, 2e6]])
        with pytest.raises(
            ValueError,
            match="scalars and nodes of type Forecast or Variable, but got table",
        ):
            assign_value(table, type_=(FORECAST, VARIABLE))

    @pytest.mark.parametrize(
        "assignment",
        [Expression('1 + Forecast("x")'), Variable("v")],
        ids=["expression", "calculator_node"],
    )
    def test_bounded_values_receive_the_attribute_bounds(self, assignment):
        assign_value(
            assignment, scalar=False, type_=(FORECAST, VARIABLE), lower=0.0, upper=5.0
        )

        assert assignment.internal_bounds == (0.0, 5.0)


# ── assign_list ───────────────────────────────────────────────────────────────


class TestAssignList:
    @pytest.mark.parametrize(
        ("assignment", "length", "message"),
        [
            ([1.0, 2.0], 3, "must contain exactly 3 values"),
            ([1.0], (2, None), "must contain at least 2 values"),
            ([1.0, 2.0, 3.0], (None, 2), "must contain at most 2 values"),
        ],
        ids=["exact", "lower_bound", "upper_bound"],
    )
    def test_length_violation(self, assignment, length, message):
        with pytest.raises(ValueError, match=message):
            assign_list(assignment, length=length)

    def test_default_length_skips_the_check(self):
        assert assign_list([1.0, 2.0], length=None) == [1.0, 2.0]

    @pytest.mark.parametrize(
        "entries",
        [[Fuel("oil"), Fuel("oil")], [WildcardNodeReference(FUEL, "*")] * 2],
        ids=["nodes", "wildcards"],
    )
    def test_duplicate_references_rejected(self, entries):
        with pytest.raises(ValueError, match=r"requires all entries .* to be unique"):
            assign_list(entries, unique=True, scalar=False, type_=FUEL)

    def test_uniqueness_ignores_floats(self):
        # _check_list_is_unique only inspects node entries, so unique=True is a
        # no-op for a list of numbers
        assert assign_list([1.0, 1.0], unique=True) == [1.0, 1.0]


# ── assign_fraction_list ──────────────────────────────────────────────────────


class TestAssignFractionList:
    def test_unit_sum_is_untouched(self):
        fractions, rescaled = assign_fraction_list([0.25, 0.75])

        assert fractions == pytest.approx([0.25, 0.75])
        assert rescaled is False

    def test_rescaled_and_flagged_beyond_one_percent(self):
        fractions, rescaled = assign_fraction_list([0.4, 0.4])

        assert fractions == pytest.approx([0.5, 0.5])
        assert rescaled is True

    def test_rescaled_silently_within_one_percent(self):
        # the flag gates the caller's log line, not the rescaling itself
        fractions, rescaled = assign_fraction_list([0.5, 0.505])

        assert sum(fractions) == pytest.approx(1.0)
        assert rescaled is False

    def test_the_passed_list_is_left_alone(self):
        # the setters assign the returned list, so rescaling must not reach
        # the list the parser still holds
        passed = [0.4, 0.4]
        assign_fraction_list(passed)

        assert passed == pytest.approx([0.4, 0.4])

    @pytest.mark.parametrize(
        ("fractions", "expected"),
        [([0.0, 0.0], [0.0, 0.0]), ([], [])],
        ids=["all_zero", "empty"],
    )
    def test_nothing_to_rescale(self, fractions, expected):
        # a zero total cannot be scaled to one, so the values stand as written
        result, rescaled = assign_fraction_list(fractions)

        assert result == expected
        assert rescaled is False

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="does not allow negative values"):
            assign_fraction_list([-0.1, 1.1])

    def test_non_list_rejected(self):
        with pytest.raises(ValueError, match="only allows assignment of lists"):
            assign_fraction_list((0.5, 0.5))


# ── command_assignment_to_dict ────────────────────────────────────────────────


class TestCommandAssignmentToDict:
    def test_literal_key_assigns_one_entry(self):
        assignment_dict = {"oil": None, "ammonia": None}
        command_assignment_to_dict("oil", 1.0, assignment_dict)

        assert isinstance(assignment_dict["oil"], Scalar)
        assert assignment_dict["ammonia"] is None

    def test_wildcard_assigns_every_match(self):
        assignment_dict = {"bio_a": None, "bio_b": None, "fossil": None}
        command_assignment_to_dict("bio_*", 1.0, assignment_dict)

        assert isinstance(assignment_dict["bio_a"], Scalar)
        assert isinstance(assignment_dict["bio_b"], Scalar)
        assert assignment_dict["fossil"] is None

    def test_float_arrives_wrapped(self):
        assignment_dict = {"oil": None}
        command_assignment_to_dict("oil", 2.0, assignment_dict)

        assert assignment_dict["oil"].get() == 2.0

    def test_unmatched_key_raises(self):
        with pytest.raises(KeyError, match="missing"):
            command_assignment_to_dict("missing", 1.0, {"oil": None})

    def test_bounds_forwarded(self):
        with pytest.raises(ValueError, match=r"must be ≤ 1\.0"):
            command_assignment_to_dict("oil", 9.0, {"oil": None}, upper=1.0)


# ── command_assignment_to_tuple_dict ──────────────────────────────────────────


class TestCommandAssignmentToTupleDict:
    def test_wildcard_expands_the_cross_product(self):
        assignment_dict = {
            ("a", "x"): None,
            ("b", "x"): None,
            ("a", "y"): None,
            ("b", "y"): None,
        }
        command_assignment_to_tuple_dict(("*", "x"), 1.0, assignment_dict)

        assert isinstance(assignment_dict[("a", "x")], Scalar)
        assert isinstance(assignment_dict[("b", "x")], Scalar)
        assert assignment_dict[("a", "y")] is None

    def test_unmatched_key_raises(self):
        with pytest.raises(KeyError, match="missing"):
            command_assignment_to_tuple_dict(("missing", "x"), 1.0, {("a", "x"): None})

    @pytest.mark.parametrize(
        ("key", "match"),
        [
            (("a", "b"), "a, b"),
            ((FuelTypeID.OIL, FuelTypeID.AMMONIA), "OIL, AMMONIA"),
        ],
        ids=["names", "enum_members"],
    )
    def test_empty_dict_raises_with_the_joined_key(self, key, match):
        # the dict is empty when a dependent dict was never seeded, so the key
        # has nothing to match; enum keys are named, not str.join-ed
        with pytest.raises(KeyError, match=match):
            command_assignment_to_tuple_dict(key, 1.0, {})

    def test_bounds_forwarded(self):
        with pytest.raises(ValueError, match=r"must be ≤ 1\.0"):
            command_assignment_to_tuple_dict(
                ("a", "x"), 9.0, {("a", "x"): None}, upper=1.0
            )


# ── command_assignment_to_boolean_dict ────────────────────────────────────────


class TestCommandAssignmentToBooleanDict:
    @pytest.mark.parametrize(
        ("assignment", "expected"),
        [("TRUE", True), ("FALSE", False)],
    )
    def test_assigns_boolean(self, assignment, expected):
        assignment_dict = {"oil": None}
        command_assignment_to_boolean_dict("oil", assignment, assignment_dict)

        assert assignment_dict["oil"] is expected

    def test_invalid_value_raises_before_the_key_is_looked_up(self):
        with pytest.raises(ValueError, match="only allows assignment of TRUE or FALSE"):
            command_assignment_to_boolean_dict("oil", "MAYBE", {"oil": None})

    def test_unmatched_wildcard_is_silent_when_allowed(self):
        assignment_dict = {"oil": None}
        command_assignment_to_boolean_dict(
            "bio_*", "TRUE", assignment_dict, allow_empty=True
        )

        assert assignment_dict == {"oil": None}

    def test_unmatched_wildcard_raises_when_not_allowed(self):
        with pytest.raises(KeyError, match="bio"):
            command_assignment_to_boolean_dict("bio_*", "TRUE", {"oil": None})

    def test_unmatched_literal_key_raises_even_when_allowed(self):
        # allow_empty only forgives a wildcard that matched nothing
        with pytest.raises(KeyError, match="missing"):
            command_assignment_to_boolean_dict(
                "missing", "TRUE", {"oil": None}, allow_empty=True
            )
