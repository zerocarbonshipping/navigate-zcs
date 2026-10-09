# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Which declared nodes take part in the run, and what the prune does to the rest.

A node is reachable when a chain of references connects it to a root type.
`find_unreachable` is checked on synthetic registries; the parser's prune is
checked on decks: it removes the unreachable nodes with one warning, drops the
EVENTS statements and scrubs the jurisdictions that name them, and leaves
their required attributes unchecked.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest

import navigate.core.nodes
from helpers.parser_decks import FLEET, FUEL
from navigate.core import Expression
from navigate.core.general_nodes.bunker_options import BunkerOptions
from navigate.core.general_nodes.model_definition import ModelDefinition
from navigate.core.node_registry import GeneralNodes, Nodes
from navigate.core.node_type import CURVE, LEVY, PORT, VESSEL
from navigate.core.nodes.converter import Converter
from navigate.core.nodes.curve import Curve
from navigate.core.nodes.fleet import Fleet
from navigate.core.nodes.levy import Levy
from navigate.core.nodes.plant import Plant
from navigate.core.nodes.port import Port
from navigate.core.nodes.power_system import PowerSystem
from navigate.core.nodes.process import Process
from navigate.core.nodes.producer import Producer
from navigate.core.nodes.route import Route
from navigate.core.nodes.tank import Tank
from navigate.core.nodes.vessel import Vessel
from navigate.exceptions import CommandError
from navigate.parser._attributes import NODE_ATTRIBUTE_SECTIONS
from navigate.parser._commands import CommandReference
from navigate.parser._event import Event
from navigate.parser._keywords import (
    NODE_GROUP,
    SECTION_DEFINE,
    define_new_node,
    node_group,
)
from navigate.parser._lark_parser import Assignment, NodeDeclaration, SourceLocation
from navigate.parser._node_reference import NodeReference
from navigate.parser._reachability import ACTIVATION_EDGES, ROOT_TYPES, find_unreachable
from navigate.parser.parser import Parser
from navigate.util import attribute_to_instance_name

NON_ROOT_TYPES = sorted(set(NODE_GROUP) - set(ROOT_TYPES))


def _general_nodes():
    return GeneralNodes(
        bunker_options=BunkerOptions(), model_definition=ModelDefinition()
    )


def _events(node_type, name, attribute, value):
    """Return one queued event re-assigning an attribute of a node."""
    event = Event(source=SourceLocation())
    event.add_statement(
        NodeDeclaration(node_type, name, [Assignment(attribute, value)])
    )
    return [event]


def _fleet_chain():
    """Registry with a wired Fleet -> Vessel -> machinery and route chain."""
    nodes = Nodes()
    nodes.fleets["fleet"] = fleet = Fleet("fleet")
    nodes.vessels["vessel"] = vessel = Vessel("vessel")
    nodes.power_systems["ps"] = power_system = PowerSystem("ps")
    nodes.converters["conv"] = converter = Converter("conv")
    nodes.tanks["tank"] = tank = Tank("tank")
    nodes.routes["route"] = route = Route("route")
    nodes.ports["port"] = port = Port("port")

    fleet.assets = [vessel]
    vessel.power_system = power_system
    vessel.tanks = [tank]
    vessel.route = route
    power_system.propulsion = converter
    route.ports = [port]

    return nodes


class TestFindUnreachable:
    # input:    | a registry holding one root node, e.g. Fleet "x", and nothing else
    # expected: -> nothing is unreachable
    @pytest.mark.parametrize("node_type", ROOT_TYPES)
    def test_a_lone_root_node_is_reachable(self, node_type):
        nodes = Nodes()
        node_group(nodes, node_type)["x"] = define_new_node(node_type, "x")

        assert find_unreachable(nodes, _general_nodes(), [], {}) == []

    # input:    | a registry holding one non-root node, e.g. Vessel "x", and
    #           | nothing else
    # expected: -> exactly that node is unreachable
    @pytest.mark.parametrize("node_type", NON_ROOT_TYPES)
    def test_a_lone_non_root_node_is_unreachable(self, node_type):
        nodes = Nodes()
        node_group(nodes, node_type)["x"] = define_new_node(node_type, "x")

        assert find_unreachable(nodes, _general_nodes(), [], {}) == [(node_type, "x")]

    # input:    | fleet holds vessel, vessel sails route, route visits port
    #           | orphan_vessel sails orphan_route, which visits port and orphan_port
    # expected: -> orphan_port, orphan_route and orphan_vessel are unreachable;
    #              the shared port is kept
    def test_an_orphan_chain_is_unreachable_and_a_shared_node_is_kept(self):
        nodes = _fleet_chain()
        nodes.vessels["orphan_vessel"] = orphan_vessel = Vessel("orphan_vessel")
        nodes.routes["orphan_route"] = orphan_route = Route("orphan_route")
        nodes.ports["orphan_port"] = orphan_port = Port("orphan_port")
        orphan_vessel.route = orphan_route
        orphan_route.ports = [nodes.ports["port"], orphan_port]

        assert find_unreachable(nodes, _general_nodes(), [], {}) == [
            ("Port", "orphan_port"),
            ("Route", "orphan_route"),
            ("Vessel", "orphan_vessel"),
        ]

    # input:    | producer owns plant, plant runs process a; a and b feed each other
    #           | c and d feed each other, and nothing reaches them
    # expected: -> processes c and d are unreachable, and the walk ends
    def test_reference_cycles_terminate(self):
        nodes = Nodes()
        nodes.producers["producer"] = producer = Producer("producer")
        nodes.plants["plant"] = plant = Plant("plant")
        processes = {name: Process(name) for name in "abcd"}
        nodes.processes.update(processes)
        producer.assets = [plant]
        plant.process = processes["a"]
        processes["a"].feeds = [processes["b"]]
        processes["b"].feeds = [processes["a"]]
        processes["c"].feeds = [processes["d"]]
        processes["d"].feeds = [processes["c"]]

        assert find_unreachable(nodes, _general_nodes(), [], {}) == [
            ("Process", "c"),
            ("Process", "d"),
        ]

    # input:    | EVENTS: Vessel "ghost" { PropulsionLoad = Curve("curve") }
    #           | ghost is in no fleet
    # expected: -> curve and ghost are unreachable; aimed at the fleet's vessel
    #              instead, nothing is unreachable
    @pytest.mark.parametrize(
        ("target", "expected"),
        [("vessel", []), ("ghost", [("Curve", "curve"), ("Vessel", "ghost")])],
        ids=["reachable_target", "unreachable_target"],
    )
    def test_an_events_reference_counts_only_from_a_reachable_target(
        self, target, expected
    ):
        nodes = _fleet_chain()
        nodes.curves["curve"] = Curve("curve")
        nodes.vessels["ghost"] = Vessel("ghost")
        if target == "vessel":
            del nodes.vessels["ghost"]
        events = _events(
            VESSEL, target, "PropulsionLoad", NodeReference(CURVE, "curve")
        )

        assert find_unreachable(nodes, _general_nodes(), events, {}) == expected

    # input:    | Fleet "fleet" { set_initial_technology_share("*", Curve("tc")) }
    #           | the command is queued and has not run yet
    # expected: -> nothing is unreachable, so Curve "tc" is kept
    def test_a_queued_command_input_keeps_its_reference(self):
        nodes = _fleet_chain()
        nodes.curves["tc"] = Curve("tc")
        command_queue = {
            nodes.fleets["fleet"]: [
                CommandReference(
                    "set_initial_technology_share",
                    ["*", NodeReference(CURVE, "tc")],
                    SourceLocation(),
                )
            ]
        }

        assert find_unreachable(nodes, _general_nodes(), [], command_queue) == []

    # input:    | Levy "levy" { Jurisdiction = [Port("port"), Port("other")] }
    #           | only port is on a route; also tried via an expression and via EVENTS
    # expected: -> Port "other" is unreachable
    @pytest.mark.parametrize(
        "reference_kind", ["jurisdiction", "expression", "events_jurisdiction"]
    )
    def test_only_a_route_activates_a_port(self, reference_kind):
        nodes = _fleet_chain()
        nodes.levies["levy"] = levy = Levy("levy")
        nodes.ports["other"] = other = Port("other")
        events = []
        if reference_kind == "jurisdiction":
            levy.jurisdiction = [nodes.ports["port"], other]
        elif reference_kind == "expression":
            nodes.vessels["vessel"].propulsion_load = Expression('0.5 * Port("other")')
        else:
            events = _events(
                LEVY, "levy", "Jurisdiction", [NodeReference(PORT, "other")]
            )

        assert find_unreachable(nodes, _general_nodes(), events, {}) == [
            ("Port", "other")
        ]


GHOST_VESSEL = """
Vessel "ghost" {
    PowerSystem = PowerSystem("ps")
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
    def read(extra="", events=None, parser=None):
        return read_deck(FLEET + FUEL + CO2 + extra, events=events, parser=parser)

    return read


class TestPrune:
    # input:    | Vessel "ghost" { PowerSystem = PowerSystem("ps") ... }
    #           | ghost is in no fleet and has no Route
    # expected: -> one "Removed ..." warning naming Vessel("ghost"), only vessel
    #              is left, and no missing-Route error
    def test_an_unreachable_node_is_removed_with_one_warning(
        self, read_fleet_deck, caplog
    ):
        # the ghost has no Route, so a successful read also pins that a pruned
        # node's required attributes are never checked
        with caplog.at_level(logging.WARNING):
            parser = read_fleet_deck(GHOST_VESSEL)

        warnings = [record for record in caplog.records if "Removed" in record.message]
        assert len(warnings) == 1
        assert 'Vessel("ghost")' in warnings[0].message
        assert set(parser.nodes.vessels) == {"vessel"}

    # input:    | Vessel "ghost" { ... }   in no fleet
    #           | read by a Parser whose vessels dict was saved beforehand
    # expected: -> the saved dict is the same object and holds only vessel
    def test_the_registry_is_pruned_in_place(self, read_fleet_deck):
        # SimulationManager aliases parser.nodes before it reads the deck
        parser = Parser()
        vessels = parser.nodes.vessels

        read_fleet_deck(GHOST_VESSEL, parser=parser)

        assert parser.nodes.vessels is vessels
        assert set(vessels) == {"vessel"}

    # input:    | Vessel "ghost" { ... }   in no fleet
    #           | Levy "levy" { ... set_include_vessel("*", TRUE) }
    # expected: -> the levy's include_vessel keys are only vessel, no ghost
    def test_dependency_dicts_hold_no_pruned_node(self, read_fleet_deck):
        parser = read_fleet_deck(
            GHOST_VESSEL + _levy(extra='set_include_vessel("*", TRUE)')
        )

        assert set(parser.nodes.levies["levy"].include_vessel) == {"vessel"}

    # input:    | Start
    #           | Vessel "ghost" { PropulsionLoad = 12 }   ghost is pruned
    #           | Vessel "*" { PropulsionLoad = 11 }
    #           | End
    # expected: -> only the "*" statement stays queued, and the warning says
    #              1 queued EVENTS statement(s) targeting only removed nodes
    @pytest.mark.parametrize("dated", [True, False], ids=["dated", "start"])
    def test_an_events_statement_on_a_pruned_node_is_dropped(
        self, read_fleet_deck, caplog, dated
    ):
        # the Start statements are held apart until the start date is known,
        # which is after the prune
        timing = 'Date "01-01-2027"\n' if dated else ""
        events = (
            f"Start\n{timing}"
            'Vessel "ghost" { PropulsionLoad = 12 }\n'
            'Vessel "*" { PropulsionLoad = 11 }\n'
            "End\n"
        )

        with caplog.at_level(logging.WARNING):
            parser = read_fleet_deck(GHOST_VESSEL, events=events)

        targets = [
            statement.name
            for events in parser._event_queue.values()
            for event in events
            for statement in event.statements
        ]
        assert targets == ["*"]
        assert (
            "1 queued EVENTS statement(s) targeting only removed nodes" in caplog.text
        )

    # input:    | Vessel "ghost" { ... }   pruned
    #           | Levy "levy" { ... set_include_vessel("ghost", TRUE) }
    # expected: -> CommandError "'set_include_vessel' attempts to reference
    #              non-existing name(s) 'ghost'. Note: 'ghost' removed because
    #              unreachable from any top-level node."
    def test_a_command_naming_a_pruned_node_hints_at_the_prune(self, read_fleet_deck):
        define = GHOST_VESSEL + _levy(extra='set_include_vessel("ghost", TRUE)')

        with pytest.raises(
            CommandError,
            match=(
                r"'set_include_vessel' attempts to reference non-existing name\(s\) "
                r"'ghost'\. Note: 'ghost' removed because unreachable from any "
                r"top-level node\.$"
            ),
        ):
            read_fleet_deck(define)

    # input:    | Levy "levy" { Jurisdiction = [Port("port"), Port("other")] }
    #           | Levy "levy_two" { same Jurisdiction }
    #           | Port "other" { }   on no route
    # expected: -> only port is left, both jurisdictions hold only port, and each
    #              levy warns 'Levy("...") Jurisdiction: Port("other")'
    def test_an_unrouted_jurisdiction_port_is_scrubbed_from_every_policy(
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


class TestActivationEdges:
    # input:    | every entry of ACTIVATION_EDGES, e.g. Route.ports activating a Port
    # expected: -> the attribute is a list on the node, and its DSL name (Ports)
    #              is DEFINE-only in NODE_ATTRIBUTE_SECTIONS
    def test_each_edge_is_a_define_only_list_attribute(self):
        # the reachability pass relies on no activation edge being assignable
        # inside a queued EVENTS body
        for target_type, edges in ACTIVATION_EDGES.items():
            assert target_type in NODE_GROUP

            for owner_type, attribute_name in edges:
                owner = define_new_node(owner_type, "pin")
                assert isinstance(getattr(owner, attribute_name), list)

                dsl_names = [
                    key
                    for key in NODE_ATTRIBUTE_SECTIONS[owner_type]
                    if attribute_to_instance_name(key) == attribute_name
                ]
                assert len(dsl_names) == 1
                assert (
                    NODE_ATTRIBUTE_SECTIONS[owner_type][dsl_names[0]] == SECTION_DEFINE
                )

    # input:    | every assign_reference call with PORT in navigate/core/nodes and
    #           | navigate/core/general_nodes
    # expected: -> the sites found are exactly Route ports and policy jurisdiction
    def test_every_port_reference_site_is_classified(self):
        # a new Port-typed reference site must be declared an activation edge or
        # added to the classified set, so no reference kind activates a port
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
