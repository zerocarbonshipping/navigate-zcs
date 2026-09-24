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


class TestCommandReferenceWildcard:
    def test_enum_domain_expands_wildcard(self):
        """set_slip_fraction has FuelTypeID domain — M* expands to fuel names."""
        call_log = []

        class DummyNode:
            def set_slip_fraction(self, fuel_type, value):
                call_log.append((fuel_type, value))

            def __str__(self):
                return "DummyNode"

        node = DummyNode()
        ref = CommandReference(
            "set_slip_fraction", ["M*", 0.03], source=SourceLocation("test.inc", 1)
        )
        ref.execute(node)

        fuel_types = [c[0] for c in call_log]
        assert "METHANE" in fuel_types
        assert "METHANOL" in fuel_types
        assert all(c[1] == 0.03 for c in call_log)

    def test_no_domain_passes_wildcard_through(self):
        """set_include_vessel has no domain — * passes through as-is."""
        call_log = []

        class DummyNode:
            def set_include_vessel(self, vessel_name, include):
                call_log.append((vessel_name, include))

            def __str__(self):
                return "DummyNode"

        node = DummyNode()
        ref = CommandReference(
            "set_include_vessel", ["*", "TRUE"], source=SourceLocation("test.inc", 1)
        )
        ref.execute(node)

        assert call_log == [("*", "TRUE")]

    def test_no_wildcard_calls_once(self):
        call_log = []

        class DummyNode:
            def set_slip_fraction(self, a, b):
                call_log.append((a, b))

            def __str__(self):
                return "DummyNode"

        node = DummyNode()
        ref = CommandReference(
            "set_slip_fraction", ["METHANE", 0.03], source=SourceLocation("test.inc", 1)
        )
        ref.execute(node)

        assert call_log == [("METHANE", 0.03)]

    def test_argument_beyond_the_domain_skips_expansion(self):
        """set_consumption_ttw registers one domain; its emission arg is untouched."""
        call_log = []

        class DummyNode:
            def set_consumption_ttw(self, fuel_type, emission_name, value):
                call_log.append((fuel_type, emission_name, value))

            def __str__(self):
                return "DummyNode"

        node = DummyNode()
        ref = CommandReference(
            "set_consumption_ttw",
            ["M*", "co2_*", 0.5],
            source=SourceLocation("test.inc", 1),
        )
        ref.execute(node)

        fuel_types = [c[0] for c in call_log]
        assert "METHANE" in fuel_types
        assert "METHANOL" in fuel_types
        assert all(c[1] == "co2_*" for c in call_log)
        assert all(c[2] == 0.5 for c in call_log)

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

    def test_expand_star_returns_all_nodes_of_type(self):
        parser = self._make_parser_with_fuels("fuel_a", "fuel_b", "fuel_c")
        matched = parser._expand_wildcard_node_reference(
            WildcardNodeReference("Fuel", "*"), "loc"
        )
        assert {n.name for n in matched} == {"fuel_a", "fuel_b", "fuel_c"}

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
            route,
            Assignment("Ports", WildcardNodeReference("Port", "*"), SourceLocation()),
            "Route",
        )

        assert route.ports == []
        parser._flush_pending_assignments()

        assert {p.name for p in route.ports} == {"port_a", "port_b"}
