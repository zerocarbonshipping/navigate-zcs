# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Reachability analysis and unreachable-node pruning: find_unreachable over
synthetic registries, and the parser's prune-and-warn pass over inline decks.
"""

import logging
import re
import sys
from pathlib import Path

import pytest

import navigate.core.nodes
from helpers.simulation import default_assumptions_dir
from navigate.__main__ import main
from navigate.core import Expression, NodeReference
from navigate.core.node_reference import WildcardNodeReference
from navigate.core.node_registry import GeneralNodes, Nodes
from navigate.core.node_type import CURVE, LEVY, PORT, VESSEL
from navigate.core.nodes.converter import Converter
from navigate.core.nodes.curve import Curve
from navigate.core.nodes.fleet import Fleet
from navigate.core.nodes.forecast import Forecast
from navigate.core.nodes.levy import Levy
from navigate.core.nodes.plant import Plant
from navigate.core.nodes.port import Port
from navigate.core.nodes.power_system import PowerSystem
from navigate.core.nodes.process import Process
from navigate.core.nodes.producer import Producer
from navigate.core.nodes.route import Route
from navigate.core.nodes.tank import Tank
from navigate.core.nodes.variable import Variable
from navigate.core.nodes.vessel import Vessel
from navigate.exceptions import CommandError
from navigate.parser._attributes import NODE_ATTRIBUTE_SECTIONS
from navigate.parser._commands import CommandReference
from navigate.parser._event import Event
from navigate.parser._keywords import NODE_GROUP, SECTION_DEFINE, define_new_node
from navigate.parser._lark_parser import Assignment, NodeDeclaration, SourceLocation
from navigate.parser._reachability import ACTIVATION_EDGES, find_unreachable
from navigate.parser.parser import Parser
from navigate.util import attribute_to_instance_name


def _event_with(statements):
    event = Event(source=SourceLocation())
    for statement in statements:
        event.add_statement(statement)
    return event


def _reassignment(node_type, name, attribute, value):
    return NodeDeclaration(node_type=node_type, name=name,
                           body=[Assignment(attribute=attribute, value=value)])


class TestFindUnreachable:

    def _fleet_chain(self):
        """Registry with a fully wired Fleet -> Vessel -> machinery chain."""

        nodes = Nodes()
        nodes.fleets['fleet'] = fleet = Fleet('fleet')
        nodes.vessels['vessel'] = vessel = Vessel('vessel')
        nodes.power_systems['ps'] = power_system = PowerSystem('ps')
        nodes.converters['conv'] = converter = Converter('conv')
        nodes.tanks['tank'] = tank = Tank('tank')
        nodes.routes['route'] = route = Route('route')
        nodes.ports['port'] = port = Port('port')

        fleet.assets = [vessel]
        vessel.power_system = power_system
        vessel.tanks = [tank]
        vessel.route = route
        power_system.propulsion = converter
        route.ports = [port]

        return nodes

    def test_full_chain_is_reachable(self):
        nodes = self._fleet_chain()

        assert find_unreachable(nodes, GeneralNodes(), {}) == []

    def test_orphan_chain_pruned_transitively_shared_node_kept(self):
        nodes = self._fleet_chain()
        nodes.vessels['orphan_vessel'] = orphan_vessel = Vessel('orphan_vessel')
        nodes.routes['orphan_route'] = orphan_route = Route('orphan_route')
        nodes.ports['orphan_port'] = orphan_port = Port('orphan_port')

        orphan_vessel.route = orphan_route
        orphan_route.ports = [nodes.ports['port'], orphan_port]

        unreachable = find_unreachable(nodes, GeneralNodes(), {})

        assert unreachable == [('Port', 'orphan_port'),
                               ('Route', 'orphan_route'),
                               ('Vessel', 'orphan_vessel')]

    def test_process_cycles_terminate(self):
        nodes = Nodes()
        nodes.producers['producer'] = producer = Producer('producer')
        nodes.plants['plant'] = plant = Plant('plant')
        nodes.processes['a'] = process_a = Process('a')
        nodes.processes['b'] = process_b = Process('b')
        nodes.processes['c'] = process_c = Process('c')
        nodes.processes['d'] = process_d = Process('d')

        producer.assets = [plant]
        plant.process = process_a
        process_a.feeds = [process_b]
        process_b.feeds = [process_a]
        process_c.feeds = [process_d]
        process_d.feeds = [process_c]

        assert find_unreachable(nodes, GeneralNodes(), {}) == [('Process', 'c'), ('Process', 'd')]

    def test_events_reference_kept_only_when_target_is_reachable(self):
        nodes = self._fleet_chain()
        nodes.curves['curve'] = Curve('curve')

        event_queue = {'d': [_event_with([
            _reassignment(VESSEL, 'vessel', 'PropulsionLoad', NodeReference(CURVE, 'curve')),
        ])]}

        assert find_unreachable(nodes, GeneralNodes(), event_queue) == []

        nodes.vessels['ghost'] = Vessel('ghost')
        event_queue = {'d': [_event_with([
            _reassignment(VESSEL, 'ghost', 'PropulsionLoad', NodeReference(CURVE, 'curve')),
        ])]}

        unreachable = find_unreachable(nodes, GeneralNodes(), event_queue)

        assert unreachable == [('Curve', 'curve'), ('Vessel', 'ghost')]

    def test_events_wildcard_value_keeps_all_matches(self):
        nodes = self._fleet_chain()
        nodes.curves['c1'] = Curve('c1')
        nodes.curves['c2'] = Curve('c2')

        event_queue = {'d': [_event_with([
            _reassignment(VESSEL, 'vessel', 'PropulsionLoad', [WildcardNodeReference(CURVE, 'c*')]),
        ])]}

        assert find_unreachable(nodes, GeneralNodes(), event_queue) == []

    def test_events_expression_references_found_by_probe(self):
        nodes = self._fleet_chain()
        nodes.forecasts['a'] = Forecast('a')
        nodes.forecasts['b'] = Forecast('b')

        expression = Expression('0.5 * Forecast("a") + Forecast("b")')
        event_queue = {'d': [_event_with([
            _reassignment(VESSEL, 'vessel', 'PropulsionLoad', expression),
        ])]}

        assert find_unreachable(nodes, GeneralNodes(), event_queue) == []
        assert not expression.is_initialized()

    def test_expression_on_attribute_keeps_reference(self):
        nodes = self._fleet_chain()
        nodes.variables['x'] = Variable('x')

        nodes.vessels['vessel'].propulsion_load = Expression('Variable("x")')

        assert find_unreachable(nodes, GeneralNodes(), {}) == []

    def test_queued_command_input_keeps_reference(self):
        nodes = self._fleet_chain()
        nodes.curves['tc'] = Curve('tc')

        nodes.fleets['fleet'].add_command_reference(
            CommandReference('set_initial_technology_share', ['*', NodeReference(CURVE, 'tc')],
                             SourceLocation()))

        assert find_unreachable(nodes, GeneralNodes(), {}) == []

    def test_jurisdiction_reference_does_not_activate_port(self):
        nodes = self._fleet_chain()
        nodes.levies['levy'] = levy = Levy('levy')
        nodes.ports['jur_port'] = jur_port = Port('jur_port')

        levy.jurisdiction = [jur_port]

        assert find_unreachable(nodes, GeneralNodes(), {}) == [('Port', 'jur_port')]

    def test_routed_port_in_jurisdiction_is_reachable(self):
        nodes = self._fleet_chain()
        nodes.levies['levy'] = levy = Levy('levy')

        levy.jurisdiction = [nodes.ports['port']]

        assert find_unreachable(nodes, GeneralNodes(), {}) == []

    def test_expression_reference_does_not_activate_port(self):
        nodes = self._fleet_chain()
        nodes.ports['expr_port'] = Port('expr_port')

        nodes.vessels['vessel'].propulsion_load = Expression('0.5 * Port("expr_port")')

        assert find_unreachable(nodes, GeneralNodes(), {}) == [('Port', 'expr_port')]

    def test_events_jurisdiction_assignment_creates_no_edge(self):
        nodes = self._fleet_chain()
        nodes.levies['levy'] = Levy('levy')
        nodes.ports['jur_port'] = Port('jur_port')

        event_queue = {'d': [_event_with([
            _reassignment(LEVY, 'levy', 'Jurisdiction', [NodeReference(PORT, 'jur_port')]),
        ])]}

        assert find_unreachable(nodes, GeneralNodes(), event_queue) == [('Port', 'jur_port')]


DEFINE_BASE = '''
ModelDefinition {
    StartDate = "01/01/2025"
}

Fleet "fleet" {
    Vessels = [Vessel("vessel")]
    InterFuelSensitivity = 0.5
    IntraFuelSensitivity = 0.5
    InitialVessels = 100
}

Vessel "vessel" {
    PowerSystem = PowerSystem("ps")
    Route = Route("route")
    NominalCapacity = 8000
    Tanks = [Tank("tank")]
    PropulsionLoad = 10
}

PowerSystem "ps" {
    Propulsion = Converter("conv")
    Electrical = Converter("conv_electrical")
    Heat = Converter("conv_heat")
}

Converter "conv" {
    PowerCapacity = 50
    MainFuelTypes = OIL
    Efficiency = 0.5
}

Converter "conv_electrical" {
    PowerCapacity = 10
    MainFuelTypes = OIL
    Efficiency = 0.5
}

Converter "conv_heat" {
    PowerCapacity = 5
    MainFuelTypes = OIL
    Efficiency = 0.5
}

Tank "tank" {
    FuelTypes = OIL
    Size = 9000
}

Route "route" {
    RouteType = REGIONAL_TRIP
    Ports = [Port("port")]
    TimeAtSea = 0.75
    ConditionDistribution = [1.0]
    Speeds = [10]
}

Port "port" {
    set_bunker_price_overwrite("oil", 250)
}

Fuel "oil" {
    FuelType = OIL
    LiquidMarket = TRUE
    LowerHeatingValue = 41.2
    MassDensity = 0.9

    set_ttw("co2", 3.114)
}

Emission "co2" {
    GlobalWarmingPotential = 1
}
'''

EVENTS_BASE = '''
Start
Date "01-01-2026"
Date "01-01-2027"
End
'''


def _write_deck(tmp_path, define_extra='', events_content=EVENTS_BASE):
    (tmp_path / 'define.inc').write_text(DEFINE_BASE + define_extra)
    (tmp_path / 'events.inc').write_text(events_content)

    deck = tmp_path / 'deck.nav'
    deck.write_text('DEFINE { Include "./define.inc" }\nEVENTS { Include "./events.inc" }\n')
    return deck


def _read_deck(tmp_path, define_extra='', events_content=EVENTS_BASE, parser=None):
    deck = _write_deck(tmp_path, define_extra, events_content)

    parser = parser or Parser()
    parser.read_deck(deck, data_dir=default_assumptions_dir())
    return parser


GHOST_VESSEL = '''
Vessel "ghost" {
    PowerSystem = PowerSystem("ps")
    NominalCapacity = 5000
    Tanks = [Tank("tank")]
}
'''


LEVY_DECK = '''
Levy "{name}" {{
    Scheme = BOTH
    Emissions = [Emission("co2")]
    Fuels = [Fuel("oil")]
    Jurisdiction = {jurisdiction}
    Level = 30
    {extra}
}}
'''

LEVY_STAR = LEVY_DECK.format(name='levy', jurisdiction='[Port("port")]',
                             extra='set_include_vessel("*", TRUE)')
LEVY_GHOST = LEVY_DECK.format(name='levy', jurisdiction='[Port("port")]',
                              extra='set_include_vessel("ghost", TRUE)')

JURISDICTION_PORT = '''
Port "jur_port" {
}
'''

GHOST_ROUTE = '''
Route "ghost_route" {
    RouteType = REGIONAL_TRIP
    Ports = [Port("ghost_port")]
    TimeAtSea = 0.5
    ConditionDistribution = [1.0]
    Speeds = [10]
}

Port "ghost_port" {
}
'''


class TestPruneUnreachableNodes:

    def test_no_ghosts_no_warning(self, tmp_path, caplog):
        with caplog.at_level(logging.WARNING):
            parser = _read_deck(tmp_path)

        assert 'Removed' not in caplog.text
        assert set(parser.nodes.vessels) == {'vessel'}

    def test_ghost_pruned_in_place_with_single_warning(self, tmp_path, caplog):
        # the ghost has no Route, so its initialize() would raise if it ran;
        # a successful read_deck pins that pruned nodes are never initialized
        with caplog.at_level(logging.WARNING):
            parser = _read_deck(tmp_path, define_extra=GHOST_VESSEL)

        warnings = [record for record in caplog.records if 'Removed' in record.message]

        assert len(warnings) == 1
        assert 'Vessel("ghost")' in warnings[0].message
        assert set(parser.nodes.vessels) == {'vessel'}

    def test_ghost_chain_pruned_and_dicts_seeded_without_ghosts(self, tmp_path, caplog):
        define_extra = GHOST_VESSEL + LEVY_STAR + GHOST_ROUTE
        with caplog.at_level(logging.WARNING):
            parser = _read_deck(tmp_path, define_extra=define_extra)

        assert set(parser.nodes.routes) == {'route'}
        assert set(parser.nodes.ports) == {'port'}

        # dependency dicts are seeded after the prune, so no ghost keys exist
        levy = parser.nodes.levies['levy']
        assert set(levy.include_vessel) == {'vessel'}

    def test_events_statement_targeting_ghost_dropped(self, tmp_path, caplog):
        events_content = '''
Start
Date "01-01-2026"
Vessel "ghost" {
    PropulsionLoad = 12
}
Vessel "*" {
    PropulsionLoad = 11
}
End
'''
        with caplog.at_level(logging.WARNING):
            parser = _read_deck(tmp_path, define_extra=GHOST_VESSEL,
                                events_content=events_content)

        statements = [statement
                      for events in parser._event_queue.values()
                      for event in events
                      for statement in event.statements]
        targets = [statement.name for statement in statements
                   if isinstance(statement, NodeDeclaration)]

        assert 'ghost' not in targets
        assert '*' in targets
        assert 'dropped 1 queued EVENTS statement(s)' in caplog.text

    def test_copy_source_pruned_silently(self, tmp_path, caplog):
        define_extra = '''
Tank "tank_template" {
    FuelTypes = OIL
    Size = 5000
}

Copy Tank "tank_template" "tank_copy"
'''
        with caplog.at_level(logging.WARNING):
            parser = _read_deck(tmp_path, define_extra=define_extra)

        assert 'tank_template' not in parser.nodes.tanks
        assert 'tank_copy' not in parser.nodes.tanks
        assert 'Tank("tank_copy")' in caplog.text
        assert 'tank_template' not in caplog.text

    def test_events_statement_on_copy_source_dropped_with_notice(self, tmp_path, caplog):
        define_extra = '''
Tank "tank_template" {
    FuelTypes = OIL
    Size = 5000
}

Copy Tank "tank_template" "tank_copy"

Vessel "vessel_copy_tank" {
    PowerSystem = PowerSystem("ps")
    Route = Route("route")
    NominalCapacity = 8000
    Tanks = [Tank("tank_copy")]
    PropulsionLoad = 10
}

Fleet "fleet_copy" {
    Vessels = [Vessel("vessel_copy_tank")]
    InterFuelSensitivity = 0.5
    IntraFuelSensitivity = 0.5
    InitialVessels = 10
}
'''
        events_content = '''
Start
Date "01-01-2026"
Tank "tank_template" {
    Size = 6000
}
End
'''
        with caplog.at_level(logging.WARNING):
            _read_deck(tmp_path, define_extra=define_extra, events_content=events_content)

        assert 'Removed' not in caplog.text
        assert 'Dropped 1 queued EVENTS statement(s)' in caplog.text

    def test_prune_runs_exactly_once(self, tmp_path, monkeypatch):
        calls = []
        original = Parser._prune_unreachable_nodes

        def counted(self):
            calls.append(1)
            original(self)

        monkeypatch.setattr(Parser, '_prune_unreachable_nodes', counted)

        parser = _read_deck(tmp_path)
        parser.progress_timeline()
        parser.progress_timeline()

        assert len(calls) == 1

    def test_registry_dicts_pruned_in_place(self, tmp_path):
        # SimulationManager aliases parser.nodes before read_deck runs, so
        # the prune must keep the dataclass and its dicts identical objects
        parser = Parser()
        vessels_group = parser.nodes.vessels

        _read_deck(tmp_path, define_extra=GHOST_VESSEL, parser=parser)

        assert parser.nodes.vessels is vessels_group
        assert 'ghost' not in vessels_group
        assert 'vessel' in vessels_group

    def test_warning_count_printed_to_console(self, tmp_path, capsys, monkeypatch):
        deck = _write_deck(tmp_path, define_extra=GHOST_VESSEL)

        monkeypatch.setattr(sys, 'argv', ['navigate', str(deck), '-s',
                                          '-d', str(default_assumptions_dir())])

        # main() attaches root-logger handlers via setup_logger; close them so
        # the file handler does not leak past this test
        try:
            assert main() == 0

            assert 'warning(s) logged' in capsys.readouterr().out
        finally:
            root = logging.getLogger()
            for handler in root.handlers[:]:
                handler.close()
                root.removeHandler(handler)

    def test_command_naming_pruned_node_errors_with_hint(self, tmp_path):
        define_extra = GHOST_VESSEL + LEVY_GHOST
        with pytest.raises(CommandError, match='unreachable from any top-level node'):
            _read_deck(tmp_path, define_extra=define_extra)

    def test_jurisdiction_only_port_pruned_and_scrubbed(self, tmp_path, caplog):
        define_extra = LEVY_DECK.format(
            name='levy', jurisdiction='[Port("port"), Port("jur_port")]',
            extra='') + JURISDICTION_PORT

        with caplog.at_level(logging.WARNING):
            parser = _read_deck(tmp_path, define_extra=define_extra)

        assert set(parser.nodes.ports) == {'port'}
        assert [port.name for port in parser.nodes.levies['levy'].jurisdiction] == ['port']
        assert 'Levy("levy") Jurisdiction: Port("jur_port")' in caplog.text

    def test_empty_jurisdiction_after_scrub_errors_at_initialize(self, tmp_path, caplog):
        define_extra = LEVY_DECK.format(
            name='levy', jurisdiction='[Port("jur_port")]', extra='') + JURISDICTION_PORT

        with caplog.at_level(logging.WARNING), \
                pytest.raises(ValueError, match="Attribute 'Jurisdiction' is unassigned"):
            _read_deck(tmp_path, define_extra=define_extra)

        assert 'Levy("levy") Jurisdiction: Port("jur_port")' in caplog.text

    def test_wildcard_jurisdiction_scrubbed_to_surviving_ports(self, tmp_path, caplog):
        # the wildcard expands before the prune, so the pruned ghost port
        # lands in the jurisdiction list and must be scrubbed back out
        define_extra = LEVY_DECK.format(name='levy', jurisdiction='Port("*")',
                                        extra='') + GHOST_ROUTE

        with caplog.at_level(logging.WARNING):
            parser = _read_deck(tmp_path, define_extra=define_extra)

        assert set(parser.nodes.ports) == {'port'}
        assert [port.name for port in parser.nodes.levies['levy'].jurisdiction] == ['port']

    def test_copy_source_port_scrub_still_warned(self, tmp_path, caplog):
        define_extra = LEVY_DECK.format(
            name='levy', jurisdiction='[Port("port"), Port("port_template")]', extra='') + '''
Port "port_template" {
}

Copy Port "port_template" "port_copy"

Route "route_copy" {
    RouteType = REGIONAL_TRIP
    Ports = [Port("port_copy")]
    TimeAtSea = 0.75
    ConditionDistribution = [1.0]
    Speeds = [10]
}

Vessel "vessel_copy" {
    PowerSystem = PowerSystem("ps")
    Route = Route("route_copy")
    NominalCapacity = 8000
    Tanks = [Tank("tank")]
    PropulsionLoad = 10
}

Fleet "fleet_copy" {
    Vessels = [Vessel("vessel_copy")]
    InterFuelSensitivity = 0.5
    IntraFuelSensitivity = 0.5
    InitialVessels = 10
}
'''
        with caplog.at_level(logging.WARNING):
            parser = _read_deck(tmp_path, define_extra=define_extra)

        assert 'port_template' not in parser.nodes.ports
        assert 'port_copy' in parser.nodes.ports
        assert 'not reachable' not in caplog.text
        assert 'Levy("levy") Jurisdiction: Port("port_template")' in caplog.text

    def test_shared_pruned_port_scrubbed_from_all_policies(self, tmp_path, caplog):
        jurisdiction = '[Port("port"), Port("jur_port")]'
        define_extra = (LEVY_DECK.format(name='levy', jurisdiction=jurisdiction, extra='')
                        + LEVY_DECK.format(name='levy_two', jurisdiction=jurisdiction, extra='')
                        + JURISDICTION_PORT)

        with caplog.at_level(logging.WARNING):
            parser = _read_deck(tmp_path, define_extra=define_extra)

        for name in ('levy', 'levy_two'):
            assert [port.name for port in parser.nodes.levies[name].jurisdiction] == ['port']


class TestActivationEdges:
    """Every declared activation edge must name a real DEFINE-only list
    attribute with one DSL name, and every reference site of a restricted
    type must be classified, so the edge map cannot drift from the node
    classes."""

    def test_edges_name_real_define_only_list_attributes(self):
        for target_type, edges in ACTIVATION_EDGES.items():
            assert target_type in NODE_GROUP

            for owner_type, attribute_name in edges:
                owner = define_new_node(owner_type, 'pin')
                assert isinstance(getattr(owner, attribute_name), list)

                dsl_names = [key for key in NODE_ATTRIBUTE_SECTIONS[owner_type]
                             if attribute_to_instance_name(key) == attribute_name]
                assert len(dsl_names) == 1

                # _statement_references relies on no activation edge being
                # assignable inside a queued EVENTS body
                assert NODE_ATTRIBUTE_SECTIONS[owner_type][dsl_names[0]] == SECTION_DEFINE

    def test_every_port_reference_site_is_classified(self):
        # a new Port-typed reference site must be declared an activation edge
        # or added to the classified set here before this test passes, so a
        # reference kind can never activate (or fail to activate) unclassified;
        # a site outside the scrubbed plain-list shape surfaces as its raw line
        classified = {('route.py', 'ports'), ('_policy.py', 'jurisdiction')}

        site = re.compile(r'.*type_=.*\bPORT\b.*')
        list_attribute = re.compile(r'\s*self\.(\w+)\s*=\s*assign_\w+\(')

        core = Path(navigate.core.nodes.__file__).parents[1]

        found = set()
        for path in list((core / 'nodes').glob('*.py')) + list((core / 'general_nodes').glob('*.py')):
            for line in site.findall(path.read_text()):
                match = list_attribute.match(line)
                found.add((path.name, match.group(1) if match else line.strip()))

        assert found == classified
