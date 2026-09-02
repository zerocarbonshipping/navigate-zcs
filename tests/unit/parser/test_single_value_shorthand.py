# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Single-value shorthand for list-typed node-reference attributes.

Verifies that setters wrapping their argument with ``as_list`` accept both
``Foo("name")`` and ``[Foo("name")]``, and that a bare ``WildcardNodeReference``
is wrapped into a list so the parser's wildcard-expansion pass picks it up.
"""

from navigate.core.node_reference import NodeReference, WildcardNodeReference
from navigate.core.node_type import PORT, REGULATION, TECHNOLOGY, VESSEL
from navigate.core.nodes._policy import _Policy
from navigate.core.nodes.fleet import Fleet
from navigate.core.nodes.fuel import Fuel
from navigate.core.nodes.port import Port
from navigate.core.nodes.route import Route
from navigate.parser.parser import Parser


class TestSingleValueShorthand:

    def test_route_ports_accepts_single_reference(self):
        ref = NodeReference(PORT, "port_a")
        route_single = Route("r1")
        route_list = Route("r2")

        route_single.set_ports(ref)
        route_list.set_ports([ref])

        assert route_single.ports == route_list.ports == [ref]

    def test_policy_jurisdiction_accepts_single_reference(self):
        ref = NodeReference(PORT, "port_a")
        policy_single = _Policy("p1", REGULATION)
        policy_list = _Policy("p2", REGULATION)

        policy_single.set_jurisdiction(ref)
        policy_list.set_jurisdiction([ref])

        assert policy_single.jurisdiction == policy_list.jurisdiction == [ref]

    def test_fleet_vessels_accepts_single_reference(self):
        ref = NodeReference(VESSEL, "vessel_oil")
        fleet_single = Fleet("f1")
        fleet_list = Fleet("f2")

        fleet_single.set_vessels(ref)
        fleet_list.set_vessels([ref])

        assert fleet_single.assets == fleet_list.assets == [ref]

    def test_fleet_technologies_accepts_single_reference(self):
        ref = NodeReference(TECHNOLOGY, "tech_a")
        fleet_single = Fleet("f1")
        fleet_list = Fleet("f2")

        fleet_single.set_technologies(ref)
        fleet_list.set_technologies([ref])

        assert fleet_single.technologies == fleet_list.technologies == [ref]


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
