# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for domain-specific wildcard expansion in CommandReference."""

from __future__ import annotations

import pytest

from navigate.core.enum_ import SimulationSectionID
from navigate.core.nodes.fleet import Fleet
from navigate.core.nodes.fuel import Fuel
from navigate.core.nodes.port import Port
from navigate.core.nodes.route import Route
from navigate.exceptions import DeckFormatError
from navigate.parser._commands import CommandReference
from navigate.parser._lark_parser import Assignment, SourceLocation
from navigate.parser._node_reference import WildcardNodeReference
from navigate.parser.parser import Parser

# ── CommandReference domain-aware wildcard expansion ─────────────────────────


class _Recorder:
    """Stand-in node recording the arguments of every command call."""

    def __init__(self):
        self.calls = []

    def __str__(self):
        return "DummyNode"

    def set_slip_fraction(self, fuel_type, value):
        self.calls.append((fuel_type, value))

    def set_include_vessel(self, vessel_name, include):
        self.calls.append((vessel_name, include))

    def set_consumption_ttw(self, fuel_type, emission_name, value):
        self.calls.append((fuel_type, emission_name, value))


def _execute(command, inputs):
    """Run a command on a recorder and return the calls it received."""
    node = _Recorder()
    CommandReference(command, inputs, source=SourceLocation("test.inc", 1)).execute(
        node
    )
    return node.calls


class TestCommandReferenceWildcard:
    def test_enum_domain_expands_wildcard(self):
        """set_slip_fraction has FuelTypeID domain — M* expands to fuel names."""
        calls = _execute("set_slip_fraction", ["M*", 0.03])

        fuel_types = [call[0] for call in calls]
        assert "METHANE" in fuel_types
        assert "METHANOL" in fuel_types
        assert all(call[1] == 0.03 for call in calls)

    def test_no_domain_passes_wildcard_through(self):
        """set_include_vessel has no domain — * passes through as-is."""
        assert _execute("set_include_vessel", ["*", "TRUE"]) == [("*", "TRUE")]

    def test_argument_beyond_the_domain_skips_expansion(self):
        """set_consumption_ttw registers one domain; its emission arg is untouched."""
        calls = _execute("set_consumption_ttw", ["M*", "co2_*", 0.5])

        fuel_types = [call[0] for call in calls]
        assert "METHANE" in fuel_types
        assert "METHANOL" in fuel_types
        assert all(call[1:] == ("co2_*", 0.5) for call in calls)

    def test_subset_domain_expands_to_the_members_the_attribute_holds(self):
        """set_operational_saving_port accepts the in-port demands only."""
        fleet = Fleet("fleet")
        ref = CommandReference(
            "set_operational_saving_port",
            ["*", 0.1],
            source=SourceLocation("test.inc", 1),
        )
        ref.execute(fleet)

        saving = fleet.operational_saving_port
        assert {demand.name for demand in saving} == {"ELECTRICAL", "HEAT"}
        assert all(value.get() == 0.1 for value in saving.values())


# ── WildcardNodeReference expansion via Parser ────────────────────────────────


class TestWildcardNodeReferenceExpansion:
    @staticmethod
    def _make_parser_with_fuels(*names):
        parser = Parser()
        for name in names:
            parser.nodes.fuels[name] = Fuel(name)
        return parser

    @staticmethod
    def _make_parser_with_ports(*names):
        parser = Parser()
        for name in names:
            parser.nodes.ports[name] = Port(name)
        return parser

    def test_expand_prefix_pattern(self):
        parser = self._make_parser_with_fuels("bio_a", "bio_b", "fossil_c")
        matched = parser._expand_wildcard_node_reference(
            WildcardNodeReference("Fuel", "bio_*"), "loc"
        )
        assert {n.name for n in matched} == {"bio_a", "bio_b"}

    def test_expand_no_match_raises(self):
        parser = self._make_parser_with_fuels("fuel_a")
        with pytest.raises(
            DeckFormatError,
            match=r"loc: Wildcard 'missing_\*' did not match any Fuel",
        ):
            parser._expand_wildcard_node_reference(
                WildcardNodeReference("Fuel", "missing_*"), "loc"
            )

    def test_list_splice_preserves_surrounding_entries(self):
        parser = self._make_parser_with_ports("port_a", "port_b", "other")

        marker_before = "BEFORE"
        marker_after = "AFTER"
        expanded = parser._expand_wildcards(
            [marker_before, WildcardNodeReference("Port", "port_*"), marker_after],
            "loc",
        )

        assert expanded[0] == marker_before
        assert expanded[-1] == marker_after
        assert {n.name for n in expanded[1:-1]} == {"port_a", "port_b"}

    def test_wildcard_outside_list_expands_to_a_list(self):
        parser = self._make_parser_with_ports("port_a", "port_b")
        expanded = parser._expand_wildcards(WildcardNodeReference("Port", "*"), "loc")
        assert {n.name for n in expanded} == {"port_a", "port_b"}

    def test_pending_assignment_reaches_the_setter_expanded(self):
        # the setter never sees the wildcard: the parser holds the assignment
        # back and flushes it once the registry is complete
        parser = self._make_parser_with_ports("port_a", "port_b")
        parser._current_section = SimulationSectionID.DEFINE
        route = Route("r")
        parser.nodes.routes["r"] = route

        parser._apply_assignment(
            [route],
            Assignment("Ports", WildcardNodeReference("Port", "*"), SourceLocation()),
            "Route",
        )

        assert route.ports == []
        parser._flush_pending_assignments()

        assert {p.name for p in route.ports} == {"port_a", "port_b"}
