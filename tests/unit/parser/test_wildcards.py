# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for domain-specific wildcard expansion in CommandReference."""
import pytest

from navigate.core.node_reference import WildcardNodeReference
from navigate.exceptions import DeckFormatError
from navigate.fuel import Fuel
from navigate.parser._commands import CommandReference
from navigate.parser._lark_parser import SourceLoc
from navigate.parser.parser import Parser
from navigate.route import Port

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
        ref = CommandReference("set_slip_fraction", ["M*", 0.03],
                               source=SourceLoc("test.inc", 1))
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
        ref = CommandReference("set_include_vessel", ["*", "TRUE"],
                               source=SourceLoc("test.inc", 1))
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
        ref = CommandReference("set_slip_fraction", ["METHANE", 0.03],
                               source=SourceLoc("test.inc", 1))
        ref.execute(node)

        assert call_log == [("METHANE", 0.03)]

    def test_none_domain_skips_expansion(self):
        """set_consumption_ttw domain is (FuelTypeID, None) — second arg passes through."""
        call_log = []

        class DummyNode:
            def set_consumption_ttw(self, fuel_type, emission_name, value):
                call_log.append((fuel_type, emission_name, value))

            def __str__(self):
                return "DummyNode"

        node = DummyNode()
        ref = CommandReference("set_consumption_ttw", ["M*", "co2_*", 0.5],
                               source=SourceLoc("test.inc", 1))
        ref.execute(node)

        fuel_types = [c[0] for c in call_log]
        assert "METHANE" in fuel_types
        assert "METHANOL" in fuel_types
        assert all(c[1] == "co2_*" for c in call_log)
        assert all(c[2] == 0.5 for c in call_log)


# ── In-list WildcardNodeReference expansion via Parser ────────────────────────

class TestWildcardNodeReferenceExpansion:

    @staticmethod
    def _make_parser_with_fuels(*names):
        parser = Parser()
        for name in names:
            parser.nodes.fuels[name] = Fuel(name)
        return parser

    def test_expand_star_returns_all_nodes_of_type(self):
        parser = self._make_parser_with_fuels("fuel_a", "fuel_b", "fuel_c")
        matched = parser._expand_wildcard_node_reference(WildcardNodeReference("Fuel", "*"))
        assert {n.get_name() for n in matched} == {"fuel_a", "fuel_b", "fuel_c"}

    def test_expand_prefix_pattern(self):
        parser = self._make_parser_with_fuels("bio_a", "bio_b", "fossil_c")
        matched = parser._expand_wildcard_node_reference(WildcardNodeReference("Fuel", "bio_*"))
        assert {n.get_name() for n in matched} == {"bio_a", "bio_b"}

    def test_expand_no_match_raises(self):
        parser = self._make_parser_with_fuels("fuel_a")
        with pytest.raises(DeckFormatError, match="did not match any Fuel nodes"):
            parser._expand_wildcard_node_reference(WildcardNodeReference("Fuel", "missing_*"))

    def test_list_splice_replaces_wildcard_with_concrete_nodes(self):
        parser = self._make_parser_with_fuels("fuel_a", "fuel_b")
        container = [WildcardNodeReference("Fuel", "*")]
        parser._replace_references_on_attribute(node=None, attribute=container[0],
                                                container=container, idx_or_key=0)
        assert {n.get_name() for n in container} == {"fuel_a", "fuel_b"}

    def test_list_splice_preserves_surrounding_entries(self):
        parser = Parser()
        parser.nodes.ports["port_a"] = Port("port_a")
        parser.nodes.ports["port_b"] = Port("port_b")
        parser.nodes.ports["other"] = Port("other")

        marker_before = "BEFORE"
        marker_after = "AFTER"
        container = [marker_before, WildcardNodeReference("Port", "port_*"), marker_after]
        # iterate the list via the same path the parser uses
        parser._replace_references_on_attribute(node=None, attribute=container)

        assert container[0] == marker_before
        assert container[-1] == marker_after
        middle_names = {n.get_name() for n in container[1:-1]}
        assert middle_names == {"port_a", "port_b"}

    def test_wildcard_outside_list_raises(self):
        parser = Parser()
        wildcard = WildcardNodeReference("Fuel", "*")
        with pytest.raises(DeckFormatError, match="Wildcard node references may only appear inside lists"):
            parser._replace_references_on_attribute(node=None, attribute=wildcard,
                                                    container=None, idx_or_key=None)
