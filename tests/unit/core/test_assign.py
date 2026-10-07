# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Tests for navigate.core.assign, the validation boundary behind every setter.

CODESTYLE's "Validation and dynamic access" makes this module the one
place that checks deck input, so these pin the messages and the accept/reject
rules the DSL reference promises. Messages are sentence fragments because
``Parser._call_setter`` prefixes them with the node and attribute.
"""

from __future__ import annotations

import numpy as np
import pytest

from navigate.core.assign import (
    _check_scalar,
    assign_boolean,
    assign_bound,
    assign_date,
    assign_fraction_list,
    assign_id,
    assign_id_list,
    assign_integer,
    assign_list,
    assign_member,
    assign_reference,
    assign_reference_list,
    assign_value,
    command_assignment_to_boolean_dict,
    expand_id_wildcard,
    write_matching_key_pairs,
    write_matching_keys,
)
from navigate.core.bounds import Bounds
from navigate.core.enum_ import PORT_ENERGY_DEMANDS, EnergyDemandID, FuelTypeID
from navigate.core.expression import Expression
from navigate.core.node_type import (
    CURVE,
    FEEDSTOCK,
    FORECAST,
    FUEL,
    PORT,
    PROCESS,
    VARIABLE,
)
from navigate.core.nodes.curve import Curve
from navigate.core.nodes.feedstock import Feedstock
from navigate.core.nodes.fleet import Fleet
from navigate.core.nodes.forecast import Forecast
from navigate.core.nodes.fuel import Fuel
from navigate.core.nodes.plant import Plant
from navigate.core.nodes.port import Port
from navigate.core.nodes.process import Process
from navigate.core.nodes.producer import Producer
from navigate.core.nodes.surface import Surface
from navigate.core.nodes.variable import Variable
from navigate.core.scalar import Scalar
from navigate.core.table_data import TableData

DATE = np.datetime64("2024-01-01", "D")


# -- assign_id -----------------------------------------------------------------


class TestAssignId:
    def test_member_lookup(self):
        assert assign_id("OIL", FuelTypeID) is FuelTypeID.OIL

    def test_unknown_id_raises(self):
        with pytest.raises(ValueError, match="does not accept ID"):
            assign_id("MAYBE", FuelTypeID)

    def test_wildcard_raises_dedicated_message(self):
        with pytest.raises(ValueError, match="wildcards are not supported"):
            assign_id("M*", FuelTypeID)

    @pytest.mark.parametrize(
        ("assignment", "kind"),
        [
            ([1.0, 2.0], "list"),
            (TableData(rows=[[1.0, 2.0]]), "table"),
            (DATE, "date"),
            (Curve("c"), r'Curve\("c"\)'),
        ],
        ids=["list", "table", "date", "node"],
    )
    def test_non_string_rejected_as_a_value_error(self, assignment, kind):
        # every ID setter hands the raw deck value here, and an unhashable one
        # must not escape the enum lookup as a TypeError, which carries no deck
        # line for the parser to report
        with pytest.raises(
            ValueError, match=f"only allows assignment of IDs, but got {kind}"
        ):
            assign_id(assignment, FuelTypeID)


# -- assign_member -------------------------------------------------------------


class TestAssignMember:
    """
    The ID check for an attribute holding a subset of an enum.

    The setter's own rejection is pinned here too: the sentence a deck author
    reads is this function's, and it must name what the wildcard spelling of
    the same command names.
    """

    def test_accepted_member(self):
        assert (
            assign_member("ELECTRICAL", PORT_ENERGY_DEMANDS)
            is EnergyDemandID.ELECTRICAL
        )

    @pytest.mark.parametrize(
        "assignment",
        ["PROPULSION", "BOGUS", "H*"],
        ids=["excluded_member", "unknown_id", "wildcard"],
    )
    def test_unaccepted_id_names_the_accepted_members(self, assignment):
        # the parser expands a wildcard against the same members before the
        # setter is reached, so one arriving here is an unaccepted name like
        # any other
        with pytest.raises(ValueError, match="ELECTRICAL, HEAT") as rejected:
            assign_member(assignment, PORT_ENERGY_DEMANDS)

        assert str(rejected.value) == (
            f"only allows assignment of ELECTRICAL, HEAT, but got {assignment}"
        )

    @pytest.mark.parametrize(
        ("assignment", "kind"),
        [
            ([1.0, 2.0], "list"),
            (TableData(rows=[[1.0, 2.0]]), "table"),
            (DATE, "date"),
            (Curve("c"), r'Curve\("c"\)'),
        ],
        ids=["list", "table", "date", "node"],
    )
    def test_non_string_rejected_as_a_value_error(self, assignment, kind):
        with pytest.raises(
            ValueError, match=f"only allows assignment of IDs, but got {kind}"
        ):
            assign_member(assignment, PORT_ENERGY_DEMANDS)

    def test_agrees_with_the_wildcard_rejection(self):
        # both spellings of a command must name one accepted set, or a deck
        # author reads two different rules for the same argument
        accepted = "ELECTRICAL, HEAT"

        with pytest.raises(ValueError, match=accepted) as literal:
            assign_member("PROPULSION", PORT_ENERGY_DEMANDS)

        with pytest.raises(ValueError, match=accepted) as wildcard:
            expand_id_wildcard("P*", PORT_ENERGY_DEMANDS)

        assert str(literal.value) == (
            f"only allows assignment of {accepted}, but got PROPULSION"
        )
        assert str(wildcard.value) == (f"wildcard 'P*' did not match any of {accepted}")

    def test_the_port_saving_setter_names_the_demands_it_accepts(self):
        with pytest.raises(
            ValueError,
            match="only allows assignment of ELECTRICAL, HEAT, but got PROPULSION",
        ):
            Fleet("fleet").set_operational_saving_port("PROPULSION", 0.1)


# -- assign_id_list ------------------------------------------------------------


class TestAssignIdList:
    @pytest.mark.parametrize(
        ("element", "kind"),
        [
            (1.0, "scalar"),
            ([1.0, 2.0], "list"),
            (TableData(rows=[[1.0, 2.0]]), "table"),
        ],
        ids=["float", "list", "table"],
    )
    def test_non_string_element_rejected_as_a_value_error(self, element, kind):
        # name_contains_wildcards takes a str; a non-string element must fall
        # through to assign_id instead of raising a TypeError there first
        with pytest.raises(
            ValueError, match=f"only allows assignment of IDs, but got {kind}"
        ):
            assign_id_list([element], FuelTypeID)


# -- assign_bound --------------------------------------------------------------


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
        ("assignment", "flags", "message"),
        [
            (-np.inf, {"inclusive_lower": False}, "must be finite, but got -inf"),
            ("-INF", {"inclusive_lower": False}, "must be finite, but got -inf"),
            (np.inf, {"inclusive_upper": False}, "must be finite, but got inf"),
            ("INF", {"inclusive_upper": False}, "must be finite, but got inf"),
        ],
        ids=["minus_inf", "minus_inf_keyword", "inf", "inf_keyword"],
    )
    def test_excluded_infinity_rejected(self, assignment, flags, message):
        # a bound refuses the infinity on the side it does not bound, whether
        # the deck spells it as a number or as a keyword
        with pytest.raises(ValueError, match=message):
            assign_bound(assignment, **flags)

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


# -- assign_boolean ------------------------------------------------------------


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

    @pytest.mark.parametrize(
        ("assignment", "kind"),
        [
            ([1.0, 2.0], "list"),
            (TableData(rows=[[1.0, 2.0]]), "table"),
            (DATE, "date"),
            (Curve("c"), r'Curve\("c"\)'),
        ],
        ids=["list", "table", "date", "node"],
    )
    def test_non_keyword_value_rejected_as_a_value_error(self, assignment, kind):
        # the boolean setters hand the raw deck value here, and an unhashable
        # one must not escape the keyword lookup as a TypeError, which carries
        # no deck line for the parser to report
        with pytest.raises(
            ValueError,
            match=f"only allows assignment of TRUE or FALSE, but got {kind}",
        ):
            assign_boolean(assignment)


# -- assign_date ---------------------------------------------------------------


class TestAssignDate:
    def test_date_returned_as_is(self):
        assert assign_date(DATE) == DATE

    def test_non_date_rejected_as_a_value_error(self):
        with pytest.raises(
            ValueError, match="only allows assignment of dates, but got scalar"
        ):
            assign_date(5.0)


# -- _check_scalar -------------------------------------------------------------


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


# -- assign_integer ------------------------------------------------------------


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

    @pytest.mark.parametrize(
        ("assignment", "bounds", "message"),
        [
            (np.inf, {}, "must be finite, but got inf"),
            (-np.inf, {}, "must be finite, but got -inf"),
            (np.inf, {"lower": 1.0}, "must be finite, but got inf"),
        ],
        ids=["inf", "minus_inf", "inf_above_a_finite_lower"],
    )
    def test_infinity_rejected_as_a_value_error(self, assignment, bounds, message):
        # no integer is infinite, and rounding infinity raises an OverflowError,
        # which carries no deck line for the parser to report
        with pytest.raises(ValueError, match=message):
            assign_integer(assignment, **bounds)


# -- assign_value --------------------------------------------------------------


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
            assign_value(5.0, allow_scalar=False, type_=FORECAST)

    def test_date_rejected_by_default(self):
        with pytest.raises(ValueError, match="but got date"):
            assign_value(DATE)

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
        "make_assignment",
        [lambda: Expression('1 + Forecast("x")'), lambda: Variable("v")],
        ids=["expression", "calculator_node"],
    )
    @pytest.mark.parametrize(
        ("inclusive_lower", "inclusive_upper"),
        [(False, True), (True, False)],
        ids=["exclusive_lower", "exclusive_upper"],
    )
    def test_bounded_values_receive_the_attribute_bounds(
        self, make_assignment, inclusive_lower, inclusive_upper
    ):
        # a fresh value per case, as a calculator merges the bounds it is offered
        assignment = make_assignment()
        assign_value(
            assignment,
            allow_scalar=False,
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            upper=5.0,
            inclusive_lower=inclusive_lower,
            inclusive_upper=inclusive_upper,
        )

        assert assignment.internal_bounds == Bounds(
            0.0, 5.0, inclusive_lower, inclusive_upper
        )

    @pytest.mark.parametrize(
        ("assignment", "arguments", "message"),
        [
            (np.inf, {}, "must be finite, but got inf"),
            (-np.inf, {}, "must be finite, but got -inf"),
            (Scalar(np.inf), {}, "must be finite, but got inf"),
            (np.inf, {"lower": 0.0}, "must be finite, but got inf"),
            (-np.inf, {"upper": 1.0}, "must be finite, but got -inf"),
            # allowing infinity does not lift a finite bound
            (-np.inf, {"lower": 0.0, "allow_infinite": True}, r"must be ≥ 0\.0"),
        ],
        ids=[
            "inf",
            "minus_inf",
            "wrapped_inf",
            "inf_above_a_finite_lower",
            "minus_inf_below_a_finite_upper",
            "minus_inf_below_a_finite_lower_when_allowed",
        ],
    )
    def test_infinity_rejected(self, assignment, arguments, message):
        with pytest.raises(ValueError, match=message):
            assign_value(assignment, **arguments)

    @pytest.mark.parametrize(
        ("assignment", "arguments"),
        [
            (np.inf, {"allow_infinite": True}),
            (-np.inf, {"allow_infinite": True}),
            (np.inf, {"lower": 0.0, "allow_infinite": True}),
            # a finite bound keeps the inclusive flag the setter asked for
            (0.0, {"lower": 0.0}),
            (1.0, {"upper": 1.0}),
            (1e300, {}),
        ],
        ids=[
            "inf_allowed",
            "minus_inf_allowed",
            "inf_allowed_above_a_finite_lower",
            "on_a_finite_lower",
            "on_a_finite_upper",
            "large_finite",
        ],
    )
    def test_accepted(self, assignment, arguments):
        assert assign_value(assignment, **arguments) == assignment

    @pytest.mark.parametrize(
        "make_assignment",
        [lambda: Expression('1 + Forecast("x")'), lambda: Variable("v")],
        ids=["expression", "calculator_node"],
    )
    @pytest.mark.parametrize(
        ("allow_infinite", "inclusive"),
        [(False, False), (True, True)],
        ids=["refused", "allowed"],
    )
    def test_infinite_bounds_are_exclusive_unless_infinity_is_allowed(
        self, make_assignment, allow_infinite, inclusive
    ):
        assignment = make_assignment()
        assign_value(
            assignment,
            allow_scalar=False,
            type_=(FORECAST, VARIABLE),
            allow_infinite=allow_infinite,
        )

        assert assignment.internal_bounds == Bounds(
            -np.inf, np.inf, inclusive, inclusive
        )

    @pytest.mark.parametrize("value", [np.inf, -np.inf], ids=["inf", "minus_inf"])
    def test_an_infinite_calculator_fails_where_infinity_is_refused(self, value):
        variable = Variable("unlimited")
        variable.set_value(value)
        assign_value(variable, type_=VARIABLE)

        with pytest.raises(
            ValueError,
            match=rf'Variable\("unlimited"\): must be finite, but got {value}',
        ):
            variable.get()

    def test_an_infinite_calculator_passes_where_infinity_is_allowed(self):
        variable = Variable("unlimited")
        variable.set_value(np.inf)
        assign_value(variable, type_=VARIABLE, lower=0.0, allow_infinite=True)

        assert variable.get() == np.inf

    def test_an_infinite_expression_fails_where_infinity_is_refused(self):
        # the expression answers what the variable it references holds, and
        # the variable itself is referenced by no attribute that refuses it
        variable = Variable("unlimited")
        variable.set_value(np.inf)
        expression = Expression('2 * Variable("unlimited")')
        expression.node_references = [variable]
        assign_value(expression, type_=VARIABLE, lower=0.0)

        with pytest.raises(ValueError, match="must be finite, but got inf"):
            expression.get()

    def test_a_calculator_at_an_exclusive_bound_fails_like_the_literal(self):
        # the literal is refused at assignment, the calculator holding the same
        # value once it is evaluated, both in the words _check_scalar uses
        with pytest.raises(ValueError, match=r"must be > 0\.0, but got 0\.0"):
            assign_value(0.0, lower=0.0, inclusive_lower=False)

        variable = Variable("zero")
        variable.set_value(0.0)
        assign_value(variable, type_=VARIABLE, lower=0.0, inclusive_lower=False)

        with pytest.raises(
            ValueError, match=r'Variable\("zero"\): must be > 0\.0, but got 0\.0'
        ):
            variable.get()

    @pytest.mark.parametrize(
        "arguments",
        [{}, {"allow_scalar": False, "type_": CURVE}],
        ids=["scalar", "calculator_type"],
    )
    def test_expression_accepted_where_the_value_is_evaluated(self, arguments):
        expression = Expression("1 + 2")
        assert assign_value(expression, **arguments) is expression

    def test_expression_rejected_where_the_attribute_does_not_evaluate(self):
        # a Forecast read for its table, not through its getter, takes no
        # expression although its type is a calculator
        with pytest.raises(
            ValueError, match="nodes of type Forecast, but got expression"
        ):
            assign_value(
                Expression('Forecast("f")'),
                allow_scalar=False,
                type_=FORECAST,
                allow_expression=False,
            )


# -- assign_list ---------------------------------------------------------------


class TestAssignList:
    @pytest.mark.parametrize(
        ("assignment", "min_length", "message"),
        [
            ([1.0, 2.0], 3, "must contain at least 3 values"),
            ([], 1, "must contain at least 1 values"),
        ],
        ids=["one_short", "empty"],
    )
    def test_length_violation(self, assignment, min_length, message):
        with pytest.raises(ValueError, match=message):
            assign_list(assignment, min_length=min_length)

    @pytest.mark.parametrize(
        ("assignment", "min_length"),
        [([1.0, 2.0], 2), ([1.0, 2.0, 3.0], 2), ([], 0)],
        ids=["at_minimum", "above_minimum", "empty_at_zero"],
    )
    def test_length_at_or_above_the_minimum_is_accepted(self, assignment, min_length):
        assert assign_list(assignment, min_length=min_length) == assignment

    def test_default_minimum_accepts_an_empty_list(self):
        assert assign_list([]) == []

    @pytest.mark.parametrize("value", [np.inf, -np.inf], ids=["inf", "minus_inf"])
    def test_infinite_entry_rejected_by_default(self, value):
        with pytest.raises(ValueError, match=f"must be finite, but got {value}"):
            assign_list([1.0, value])

    @pytest.mark.parametrize("value", [np.inf, -np.inf], ids=["inf", "minus_inf"])
    def test_infinite_entry_accepted_where_allowed(self, value):
        assert assign_list([1.0, value], allow_infinite=True) == [1.0, value]


# -- assign_reference ----------------------------------------------------------


class TestAssignReference:
    def test_accepted_node_returned_as_is(self):
        fuel = Fuel("oil")
        assert assign_reference(fuel, FUEL) is fuel

    @pytest.mark.parametrize(
        "node",
        [Feedstock("f"), Process("p")],
        ids=["first_member", "last_member"],
    )
    def test_tuple_type_accepts_any_member(self, node):
        # the shape the Process feeds setter passes
        assert assign_reference(node, (FEEDSTOCK, PROCESS)) is node

    @pytest.mark.parametrize(
        ("assignment", "type_", "message"),
        [
            (
                Port("p"),
                FUEL,
                'only allows assignment of nodes of type Fuel, but got Port("p")',
            ),
            (
                Fuel("oil"),
                (FEEDSTOCK, PROCESS),
                "only allows assignment of nodes of type Feedstock or Process, "
                'but got Fuel("oil")',
            ),
            (
                Variable("v"),
                FUEL,
                'only allows assignment of nodes of type Fuel, but got Variable("v")',
            ),
            (
                1.0,
                FUEL,
                "only allows assignment of nodes of type Fuel, but got scalar",
            ),
            (
                [Fuel("oil")],
                FUEL,
                "only allows assignment of nodes of type Fuel, but got list",
            ),
            (
                TableData(rows=[[1.0, 2.0]]),
                FUEL,
                "only allows assignment of nodes of type Fuel, but got table",
            ),
            (
                "oil",
                FUEL,
                "only allows assignment of nodes of type Fuel, but got oil",
            ),
        ],
        ids=[
            "wrong_type",
            "tuple_non_member",
            "calculator",
            "float",
            "list",
            "table",
            "token",
        ],
    )
    def test_anything_but_an_accepted_node_rejected(self, assignment, type_, message):
        # compared whole: the sentence a deck author reads must not drift
        with pytest.raises(ValueError, match="nodes of type") as rejected:
            assign_reference(assignment, type_)

        assert str(rejected.value) == message

    @pytest.mark.parametrize(
        ("type_", "message"),
        [
            (PORT, "only allows assignment of nodes of type Port"),
            (
                (FEEDSTOCK, PROCESS),
                "only allows assignment of nodes of type Feedstock or Process",
            ),
        ],
        ids=["single_type", "tuple_type"],
    )
    def test_expression_rejected(self, type_, message):
        # a node reference is read as the node itself, never evaluated, so an
        # expression there has nothing to evaluate it and is refused by kind
        with pytest.raises(ValueError, match=message) as rejected:
            assign_reference(Expression('Port("x")'), type_)

        assert str(rejected.value) == f"{message}, but got expression"


# -- assign_reference_list -----------------------------------------------------


class TestAssignReferenceList:
    def test_duplicate_references_rejected(self):
        with pytest.raises(ValueError, match=r"requires all entries .* to be unique"):
            assign_reference_list([Fuel("oil"), Fuel("oil")], FUEL, unique=True)

    def test_uniqueness_checked_before_the_entries(self):
        # a duplicate is reported ahead of an entry that is no node at all
        with pytest.raises(ValueError, match=r"requires all entries .* to be unique"):
            assign_reference_list([Fuel("oil"), Fuel("oil"), 1.0], FUEL, unique=True)

    def test_duplicates_accepted_unless_unique(self):
        fuels = [Fuel("oil"), Fuel("oil")]
        assert assign_reference_list(fuels, FUEL) is fuels

    def test_bare_reference_wrapped_in_a_list(self):
        fuel = Fuel("oil")
        assert assign_reference_list(fuel, FUEL) == [fuel]

    def test_expression_entry_rejected(self):
        with pytest.raises(ValueError, match="nodes of type Port") as rejected:
            assign_reference_list([Expression('Port("x")')], PORT)

        assert str(rejected.value) == (
            "only allows assignment of nodes of type Port, but got expression"
        )


# -- assign_fraction_list ------------------------------------------------------


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
        "fractions",
        [[0.0, 0.0], [0, 0], [], [1e-9, 0.0]],
        ids=["all_zero", "all_zero_integers", "empty", "below_rounding"],
    )
    def test_zero_total_rejected(self, fractions):
        # a zero total cannot be rescaled to 1, and the total is rounded
        # before the check, so a list too small to survive the rounding is
        # no distribution either
        with pytest.raises(ValueError, match="requires entries summing to more than 0"):
            assign_fraction_list(fractions)

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="does not allow negative values"):
            assign_fraction_list([-0.1, 1.1])

    def test_non_list_rejected(self):
        with pytest.raises(ValueError, match="only allows assignment of lists"):
            assign_fraction_list((0.5, 0.5))

    @pytest.mark.parametrize(
        ("entry", "message"),
        [
            (Variable("v"), r'but got Variable\("v"\)'),
            (Curve("c"), r'but got Curve\("c"\)'),
            ([0.5], "but got list"),
            (TableData(rows=[[1.0, 2.0]]), "but got table"),
            (DATE, "but got date"),
        ],
        ids=["variable", "curve", "nested_list", "table", "date"],
    )
    def test_non_number_entry_rejected(self, entry, message):
        # the sign check compares every entry against 0.0, so a value of
        # another kind used to escape as a TypeError the parser cannot locate
        with pytest.raises(
            ValueError, match=f"only allows assignment of plain numbers, {message}"
        ):
            assign_fraction_list([0.5, entry])

    @pytest.mark.parametrize(
        ("fractions", "message"),
        [
            (
                [10**400, 1],
                "only allows assignment of finite numbers, "
                "but got a number too large for a float",
            ),
            ([np.inf, 1.0], "only allows assignment of finite numbers, but got inf"),
            ([-np.inf, 1.0], "only allows assignment of finite numbers, but got -inf"),
            ([np.nan, 1.0], "only allows assignment of finite numbers, but got nan"),
            ([1e308, 1e308], "requires entries whose sum is finite"),
        ],
        ids=["int_too_large", "inf", "negative_inf", "nan", "total_overflows"],
    )
    def test_non_finite_rejected(self, fractions, message):
        # floating an int too large for a float used to escape as an
        # OverflowError the parser cannot locate, an infinite entry or total
        # rescaled to NaN, and NaN passes the sign check; the grammar reads
        # INF, so a deck reaches the infinite case. The huge int is named
        # rather than echoed, since its digits would swamp the deck error
        with pytest.raises(ValueError, match=message):
            assign_fraction_list(fractions)

    @pytest.mark.parametrize(
        ("fractions", "expected", "is_rescaled"),
        [
            ([1, 1], [0.5, 0.5], True),
            ([1], [1.0], False),
            ([1, 0], [1.0, 0.0], False),
            ([True, False], [1.0, 0.0], False),
        ],
        ids=["rescales", "single", "unit_sum", "booleans"],
    )
    def test_whole_number_entries_take_the_float_path(
        self, fractions, expected, is_rescaled
    ):
        # the kind check accepts whole numbers because they are floated before
        # the rescale, so acceptance no longer depends on the total: only a
        # list the rescale happened to divide used to reach assign_list as
        # floats, and every other whole-number list was rejected as an integer
        result, is_rescaled_result = assign_fraction_list(fractions)

        assert result == pytest.approx(expected)
        assert all(isinstance(fraction, float) for fraction in result)
        assert is_rescaled_result is is_rescaled


# -- write_matching_keys -------------------------------------------------------


class TestWriteMatchingKeys:
    def test_literal_key_assigns_one_entry(self):
        assignment_dict = {"oil": None, "ammonia": None}
        write_matching_keys("oil", Scalar(1.0), assignment_dict)

        assert isinstance(assignment_dict["oil"], Scalar)
        assert assignment_dict["ammonia"] is None

    def test_wildcard_assigns_every_match(self):
        assignment_dict = {"bio_a": None, "bio_b": None, "fossil": None}
        write_matching_keys("bio_*", Scalar(1.0), assignment_dict)

        assert isinstance(assignment_dict["bio_a"], Scalar)
        assert isinstance(assignment_dict["bio_b"], Scalar)
        assert assignment_dict["fossil"] is None

    def test_unmatched_key_raises(self):
        with pytest.raises(KeyError, match="missing"):
            write_matching_keys("missing", 1.0, {"oil": None})


# -- write_matching_key_pairs --------------------------------------------------


class TestWriteMatchingKeyPairs:
    def test_wildcard_expands_the_cross_product(self):
        assignment_dict = {
            ("a", "x"): None,
            ("b", "x"): None,
            ("a", "y"): None,
            ("b", "y"): None,
        }
        write_matching_key_pairs(("*", "x"), Scalar(1.0), assignment_dict)

        assert isinstance(assignment_dict[("a", "x")], Scalar)
        assert isinstance(assignment_dict[("b", "x")], Scalar)
        assert assignment_dict[("a", "y")] is None

    def test_unmatched_key_raises(self):
        with pytest.raises(KeyError, match="missing"):
            write_matching_key_pairs(("missing", "x"), 1.0, {("a", "x"): None})

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
            write_matching_key_pairs(key, 1.0, {})


# -- command_assignment_to_boolean_dict ----------------------------------------


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


# -- setters that accept infinity ----------------------------------------------


def _bunkering_limit(value):
    port = Port("p")
    port.bunkering_limit = {"fuel": None}
    port.set_bunkering_limit("fuel", value)
    return port.bunkering_limit["fuel"].get()


def _feed_constraint(value):
    producer = Producer("p")
    producer.feed_constraints = {"feed": None}
    producer.set_feed_constraint("feed", value)
    return producer.feed_constraints["feed"].get()


def _maximum_speed_change(value):
    fleet = Fleet("f")
    fleet.set_maximum_speed_change(value)
    return fleet.maximum_speed_change.get()


def _below(value):
    curve = Curve("c")
    curve.set_below(value)
    return curve._below


def _above(value):
    curve = Curve("c")
    curve.set_above(value)
    return curve._above


def _outside(value):
    surface = Surface("s")
    surface.set_outside(value)
    return surface._outside


def _value(value):
    variable = Variable("v")
    variable.set_value(value)
    return variable._value


class TestInfinityOptIns:
    """
    Only the setters where infinity means something accept INF.

    A limit reads INF as no limit, and a value defining a calculator is left to
    the bounds of each attribute the calculator is assigned to; every other
    setter rejects it.
    """

    @pytest.mark.parametrize(
        "assign",
        [_bunkering_limit, _feed_constraint, _maximum_speed_change],
        ids=["bunkering_limit", "feed_constraint", "maximum_speed_change"],
    )
    def test_a_limit_accepts_inf(self, assign):
        assert assign(np.inf) == np.inf

    @pytest.mark.parametrize(
        "assign",
        [_below, _above, _outside, _value],
        ids=["below", "above", "outside", "value"],
    )
    @pytest.mark.parametrize("value", [np.inf, -np.inf], ids=["inf", "minus_inf"])
    def test_a_calculator_definition_accepts_either_infinity(self, assign, value):
        assert assign(value) == value

    @pytest.mark.parametrize(
        "assign",
        [
            lambda value: Producer("p").set_maximum_development(value),
            lambda value: Plant("p").set_capacity(value),
            lambda value: Variable("v").set_addition(value),
        ],
        ids=["maximum_development", "capacity", "addition"],
    )
    def test_a_default_setter_rejects_inf(self, assign):
        with pytest.raises(ValueError, match="must be finite, but got inf"):
            assign(np.inf)
