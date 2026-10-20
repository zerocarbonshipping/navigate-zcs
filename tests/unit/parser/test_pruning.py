# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Which declared nodes take part in the run, and what becomes of the rest.

A node is reachable when a chain of references connects it to a root type.
`prune` is checked on synthetic declarations; the parser is checked on
decks: it keeps only the reachable nodes, warns once about the others, drops
the EVENTS blocks and the jurisdiction references that name them, and leaves
their required attributes unchecked.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest

import navigate.core.nodes
from helpers.parser_decks import FLEET, FUEL
from navigate.core.dsl import SECTION_DEFINE
from navigate.core.node_registry import NODE_CLASS
from navigate.core.node_type import CURVE, PORT, VARIABLE, VESSEL
from navigate.core.node_type import FLEET as FLEET_TYPE
from navigate.exceptions import DeckError
from navigate.parser._collect import (
    Collector,
    Declaration,
    EventBlock,
    Origin,
)
from navigate.parser._lark_parser import (
    Assignment,
    Command,
    NodeReference,
    SourceLocation,
)
from navigate.parser._library import Library
from navigate.parser._prune import NON_ACTIVATING, ROOT_TYPES, prune
from navigate.parser._resolve import resolve
from navigate.util import attribute_to_setter

NON_ROOT_TYPES = sorted(set(NODE_CLASS) - set(ROOT_TYPES))


def _reference(node_type, *names):
    """Return a reference value: one node, or a list of them."""
    references = [NodeReference(node_type, name) for name in names]
    return references[0] if len(names) == 1 else references


def _reachable(declarations, events=()):
    """Prune synthetic declarations; return the kept (type, name) keys."""
    collector = Collector(Library(None))
    for node_type, name, body in declarations:
        collector.declarations[(node_type, name)] = Declaration(
            node_type, name, list(body), Origin.DECK, SourceLocation()
        )
    collector.events.extend(events)

    return prune(collector, resolve(collector)).kept


def _fleet_chain():
    """Return the declarations of a Fleet -> Vessel -> machinery and route chain."""
    return [
        (FLEET_TYPE, "fleet", [Assignment("Vessels", _reference(VESSEL, "vessel"))]),
        (
            VESSEL,
            "vessel",
            [
                Assignment("PropulsionConverter", _reference("Converter", "conv")),
                Assignment("Tanks", _reference("Tank", "tank")),
                Assignment("Route", _reference("Route", "route")),
            ],
        ),
        ("Converter", "conv", []),
        ("Tank", "tank", []),
        ("Route", "route", [Assignment("Ports", _reference(PORT, "port"))]),
        (PORT, "port", []),
    ]


FLEET_CHAIN_KEYS = [(node_type, name) for node_type, name, _ in _fleet_chain()]


class TestPrune:
    # input:    | one declared root node, e.g. Fleet "x", and nothing else
    # expected: -> the node is reachable
    @pytest.mark.parametrize("node_type", ROOT_TYPES)
    def test_a_lone_root_node_is_reachable(self, node_type):
        assert _reachable([(node_type, "x", [])]) == [(node_type, "x")]

    # input:    | one declared non-root node, e.g. Vessel "x", and nothing else
    # expected: -> nothing is reachable
    @pytest.mark.parametrize("node_type", NON_ROOT_TYPES)
    def test_a_lone_non_root_node_is_unreachable(self, node_type):
        assert _reachable([(node_type, "x", [])]) == []

    # input:    | fleet holds vessel, vessel sails route, route visits port
    #           | orphan_vessel sails orphan_route, which visits port and orphan_port
    # expected: -> orphan_port, orphan_route and orphan_vessel are unreachable;
    #              the shared port is kept
    def test_an_orphan_chain_is_unreachable_and_a_shared_node_is_kept(self):
        declarations = [
            *_fleet_chain(),
            (
                VESSEL,
                "orphan_vessel",
                [Assignment("Route", _reference("Route", "orphan_route"))],
            ),
            (
                "Route",
                "orphan_route",
                [Assignment("Ports", _reference(PORT, "port", "orphan_port"))],
            ),
            (PORT, "orphan_port", []),
        ]

        assert _reachable(declarations) == FLEET_CHAIN_KEYS

    # input:    | producer owns plant, plant runs process a; a and b feed each other
    #           | c and d feed each other, and nothing reaches them
    # expected: -> processes c and d are unreachable, and the walk ends
    def test_reference_cycles_terminate(self):
        declarations = [
            (
                "Producer",
                "producer",
                [Assignment("Plants", _reference("Plant", "plant"))],
            ),
            ("Plant", "plant", [Assignment("Process", _reference("Process", "a"))]),
            ("Process", "a", [Assignment("Feeds", _reference("Process", "b"))]),
            ("Process", "b", [Assignment("Feeds", _reference("Process", "a"))]),
            ("Process", "c", [Assignment("Feeds", _reference("Process", "d"))]),
            ("Process", "d", [Assignment("Feeds", _reference("Process", "c"))]),
        ]

        assert _reachable(declarations) == [
            ("Producer", "producer"),
            ("Plant", "plant"),
            ("Process", "a"),
            ("Process", "b"),
        ]

    # input:    | EVENTS: Vessel "ghost" { Capex = Variable("var") }
    #           | ghost is in no fleet
    # expected: -> var and ghost are unreachable; aimed at the fleet's vessel
    #              instead, var is reachable
    @pytest.mark.parametrize(
        ("target", "expected"),
        [("vessel", [(VARIABLE, "var")]), ("ghost", [])],
        ids=["reachable_target", "unreachable_target"],
    )
    def test_an_events_reference_counts_only_from_a_reachable_target(
        self, target, expected
    ):
        declarations = [*_fleet_chain(), (VARIABLE, "var", []), (VESSEL, "ghost", [])]
        event = EventBlock(
            None,
            VESSEL,
            target,
            [Assignment("Capex", _reference(VARIABLE, "var"))],
            SourceLocation(),
        )

        assert _reachable(declarations, [event]) == [*FLEET_CHAIN_KEYS, *expected]

    # input:    | Fleet "fleet" { set_initial_technology_share("*", Curve("tc")) }
    # expected: -> Curve "tc" is reachable through the command argument
    def test_a_command_argument_keeps_its_reference(self):
        declarations = _fleet_chain()
        declarations[0][2].append(
            Command("set_initial_technology_share", ["*", _reference(CURVE, "tc")])
        )
        declarations.append((CURVE, "tc", []))

        assert _reachable(declarations) == [*FLEET_CHAIN_KEYS, (CURVE, "tc")]

    # input:    | Levy "levy" { Jurisdiction = [Port("port"), Port("other")] }
    #           | only port is on a route
    # expected: -> Port "other" is unreachable: only a Route activates a Port
    def test_only_a_route_activates_a_port(self):
        declarations = [
            *_fleet_chain(),
            (
                "Levy",
                "levy",
                [Assignment("Jurisdiction", _reference(PORT, "port", "other"))],
            ),
            (PORT, "other", []),
        ]

        assert _reachable(declarations) == [*FLEET_CHAIN_KEYS, ("Levy", "levy")]


GHOST_VESSEL = """
Vessel "ghost" {
    PropulsionConverter = Converter("propulsion")
    NominalCapacity = 5000
    Tanks = [Tank("tank")]
}
"""
CO2 = 'Emission "co2" { GlobalWarmingPotential = 1.0 }\n'
LEVY_TEMPLATE = """
Levy "{name}" {{
    Scheme = BOTH
    Emissions = [Emission("co2")]
    Fuels = [Fuel("oil")]
    Jurisdiction = {jurisdiction}
    Level = 30
    {extra}
}}
"""


def _levy(jurisdiction='[Port("port")]', extra="", name="levy"):
    return LEVY_TEMPLATE.format(name=name, jurisdiction=jurisdiction, extra=extra)


@pytest.fixture
def read_fleet_deck(read_deck):
    def read(extra="", events=None):
        return read_deck(FLEET + FUEL + CO2 + extra, events=events)

    return read


class TestUnused:
    # input:    | Vessel "ghost" { PropulsionConverter = Converter("propulsion") ... }
    #           | ghost is in no fleet and has no Route
    # expected: -> one "declared but not used" warning naming Vessel("ghost"),
    #              only vessel is built, and no missing-Route error
    def test_an_unreachable_node_is_left_out_with_one_warning(
        self, read_fleet_deck, caplog
    ):
        # the ghost has no Route, so a successful read also pins that an unused
        # node's required attributes are never checked
        with caplog.at_level(logging.WARNING):
            parser = read_fleet_deck(GHOST_VESSEL)

        warnings = [
            record
            for record in caplog.records
            if "declared but not used" in record.message
        ]
        assert len(warnings) == 1
        assert 'Vessel("ghost")' in warnings[0].message
        assert set(parser.nodes.vessels) == {"vessel"}

    # input:    | Vessel "ghost" { ... }   in no fleet
    #           | Levy "levy" { ... set_include_vessel("*", TRUE) }
    # expected: -> the levy's include_vessel keys are only vessel, no ghost
    def test_dependency_dicts_hold_no_unused_node(self, read_fleet_deck):
        parser = read_fleet_deck(
            GHOST_VESSEL + _levy(extra='set_include_vessel("*", TRUE)')
        )

        assert set(parser.nodes.levies["levy"].include_vessel) == {"vessel"}

    # input:    | Start
    #           | Vessel "ghost" { PropulsionLoad = 12 }   ghost is unused
    #           | Vessel "*" { PropulsionLoad = 11 }
    # expected: -> only the "*" block is kept, and the warning says
    #              Dropped 1 EVENTS statement(s) targeting only unused node(s)
    @pytest.mark.parametrize("dated", [True, False], ids=["dated", "start"])
    def test_an_events_block_on_an_unused_node_is_dropped(
        self, read_fleet_deck, caplog, dated
    ):
        timing = 'Date "01-01-2027"\n' if dated else ""
        events = (
            f"Start\n{timing}"
            'Vessel "ghost" { Capex = 12 }\n'
            'Vessel "*" { Capex = 11 }\n'
        )

        with caplog.at_level(logging.WARNING):
            parser = read_fleet_deck(GHOST_VESSEL, events=events)

        targets = [
            block.pattern for blocks in parser._events.values() for block, _ in blocks
        ]
        assert targets == ["*"]
        assert (
            "Dropped 1 EVENTS statement(s) targeting only unused node(s)" in caplog.text
        )

    # input:    | Vessel "ghost" { ... }   unused
    #           | Levy "levy" { ... set_include_vessel("ghost", TRUE) }
    # expected: -> DeckError "'set_include_vessel' attempts to reference
    #              non-existing name(s) 'ghost'."
    def test_a_command_naming_an_unused_node_is_rejected(self, read_fleet_deck):
        define = GHOST_VESSEL + _levy(extra='set_include_vessel("ghost", TRUE)')

        with pytest.raises(
            DeckError,
            match=(
                r"'set_include_vessel' attempts to reference non-existing name\(s\) "
                r"'ghost'\.$"
            ),
        ):
            read_fleet_deck(define)

    # input:    | Levy "levy" { Jurisdiction = [Port("port"), Port("other")] }
    #           | Levy "levy_two" { same Jurisdiction }
    #           | Port "other" { }   on no route
    # expected: -> only port is built, both jurisdictions hold only port, and each
    #              levy warns 'Levy("...") Jurisdiction: Port("other")'
    def test_an_unrouted_jurisdiction_port_is_dropped_from_every_policy(
        self, read_fleet_deck, caplog
    ):
        jurisdiction = '[Port("port"), Port("other")]'
        define = (
            _levy(jurisdiction)
            + _levy(jurisdiction, name="levy_two")
            + 'Port "other" { }\n'
        )

        with caplog.at_level(logging.WARNING):
            parser = read_fleet_deck(define)

        assert set(parser.nodes.ports) == {"port"}
        for name in ("levy", "levy_two"):
            ports = parser.nodes.levies[name].jurisdiction
            assert [port.name for port in ports] == ["port"]
            assert f'Levy("{name}") Jurisdiction: Port("other")' in caplog.text


class TestNonActivating:
    # input:    | every entry of NON_ACTIVATING, e.g. a Levy's Jurisdiction
    # expected: -> the attribute is DEFINE-only and holds a list of nodes
    def test_each_entry_is_a_define_only_list_attribute(self):
        # the prune walks EVENTS bodies as activating, which holds because
        # no non-activating attribute can be assigned there
        for owner_type, attribute in NON_ACTIVATING:
            entry = NODE_CLASS[owner_type].deck_attributes[attribute]
            assert entry.sections == SECTION_DEFINE

            owner = NODE_CLASS[owner_type]("pin")
            setter = getattr(owner, attribute_to_setter(attribute))
            setter([NODE_CLASS[PORT]("target")])
            assert isinstance(getattr(owner, attribute.lower()), list)

    # input:    | every assign_reference call with PORT in navigate/core/nodes and
    #           | navigate/core/general_nodes
    # expected: -> the sites found are exactly Route ports and policy jurisdiction
    def test_every_port_reference_site_is_classified(self):
        # a new Port-typed reference site must be an activating Route edge or
        # a NON_ACTIVATING entry, so no reference kind activates a port
        # unclassified
        classified = {("route.py", "ports"), ("_policy.py", "jurisdiction")}
        site = re.compile(
            r"^.*\bassign_reference(?:_list)?\((?:[^()]|\([^()]*\))*?\bPORT\b",
            re.MULTILINE,
        )
        list_attribute = re.compile(r"\s*self\.(\w+)\s*=\s*assign_\w+\(")
        core = Path(navigate.core.nodes.__file__).parents[1]

        found = set()
        for path in [
            *(core / "nodes").glob("*.py"),
            *(core / "general_nodes").glob("*.py"),
        ]:
            for line in site.findall(path.read_text()):
                match = list_attribute.match(line)
                found.add((path.name, match.group(1) if match else line.strip()))

        assert found == classified
