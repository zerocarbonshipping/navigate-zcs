# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Single-value shorthand for list-typed node-reference attributes.

Verifies that setters wrapping their argument with ``as_list`` accept both
``Foo("name")`` and ``[Foo("name")]``, and that a bare ``WildcardNodeReference``
is wrapped into a list so the parser's wildcard-expansion pass picks it up.
"""

from __future__ import annotations

import pytest

from navigate.core.node_reference import NodeReference, WildcardNodeReference
from navigate.core.node_type import PORT, REGULATION, TECHNOLOGY, VESSEL
from navigate.core.nodes._policy import _Policy
from navigate.core.nodes.fleet import Fleet
from navigate.core.nodes.fuel import Fuel
from navigate.core.nodes.port import Port
from navigate.core.nodes.route import Route
from navigate.parser.parser import Parser


class TestSingleValueShorthand:
    @pytest.mark.parametrize(
        "node_type, make_node, setter, attribute",
        [
            (PORT, lambda: Route("r"), "set_ports", "ports"),
            (
                PORT,
                lambda: _Policy("p", REGULATION),
                "set_jurisdiction",
                "jurisdiction",
            ),
            (VESSEL, lambda: Fleet("f"), "set_vessels", "assets"),
            (TECHNOLOGY, lambda: Fleet("f"), "set_technologies", "technologies"),
        ],
        ids=[
            "route_ports",
            "policy_jurisdiction",
            "fleet_vessels",
            "fleet_technologies",
        ],
    )
    def test_setter_accepts_single_reference(
        self, node_type, make_node, setter, attribute
    ):
        ref = NodeReference(node_type, "name_a")
        node_single = make_node()
        node_list = make_node()

        getattr(node_single, setter)(ref)
        getattr(node_list, setter)([ref])

        assert getattr(node_single, attribute) == getattr(node_list, attribute) == [ref]


class TestBareWildcardShorthand:
    """A bare ``Foo("*")`` should expand the same as ``[Foo("*")]``."""

    @staticmethod
    def _make_parser_with_fuels(*names):
        parser = Parser()
        for name in names:
            parser.nodes.fuels[name] = Fuel(name)
        return parser

    def test_bare_wildcard_in_setter_expands_via_parser(self):
        parser = Parser()
        parser.nodes.ports["port_a"] = Port("port_a")
        parser.nodes.ports["port_b"] = Port("port_b")

        route = Route("r")
        route.set_ports(WildcardNodeReference(PORT, "*"))

        parser._replace_references_on_attribute(route, route.ports)

        assert {p.name for p in route.ports} == {"port_a", "port_b"}
