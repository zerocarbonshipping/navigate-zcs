# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
How a node or general-node declaration maps onto the parser's registry.

A first declaration creates the node and registers it before its body is read;
a later declaration of the same name re-opens it; a wildcard name targets every
declared match. Names are unique across node types, general nodes carry no
name and no commands, and no node is created outside DEFINE.
"""

from __future__ import annotations

import numpy as np
import pytest

from helpers.parser_decks import emission_holding, variable
from navigate.core.enum_ import SimulationSectionID
from navigate.core.general_nodes.bunker_options import BunkerOptions
from navigate.core.node_type import PROCESS
from navigate.core.nodes.variable import Variable
from navigate.exceptions import CommandError, DeckFormatError, DeckKeywordError
from navigate.parser._lark_parser import Assignment, NodeDeclaration
from navigate.parser._node_reference import NodeReference
from navigate.parser.parser import Parser

NAMED_GENERAL_NODE = 'ModelDefinition "x" {\n}\n'


# input:    | Variable "v" { Value = 1.5 }
# expected: -> a Variable named "v" in the registry, reading 1.5
def test_a_first_declaration_creates_and_registers_the_node(read_deck):
    parser = read_deck(emission_holding('Variable("v")') + variable(Value=1.5))
    node = parser.nodes.variables["v"]

    assert isinstance(node, Variable)
    assert node.name == "v"
    assert node.get() == 1.5


# input:    | Variable "v" { Value = 1.5 }
#           | Variable "v" { Multiplier = 2.0 }
# expected: -> one Variable "v" reading 2.0 * 1.5 = 3.0
def test_a_second_declaration_reopens_the_same_node(read_deck):
    # the second block adds to the first: 2.0 * 1.5
    define = (
        emission_holding('Variable("v")')
        + variable(Value=1.5)
        + variable(Multiplier=2.0)
    )

    parser = read_deck(define)

    assert parser.nodes.variables["v"].get() == 3.0


# input:    | Process "p" { Feeds = [Process("p")] }
# expected: -> the process feeds on itself: process.feeds == [process]
def test_a_body_reference_to_its_own_node_binds_to_it():
    # a Process may feed on itself; the reference must bind to the node being
    # declared, not to a second one no declaration fills
    parser = Parser()
    parser._current_section = SimulationSectionID.DEFINE
    body = [Assignment("Feeds", [NodeReference(PROCESS, "p")])]

    parser._process_node_declaration(NodeDeclaration(PROCESS, "p", body))

    process = parser.nodes.processes["p"]
    assert process.feeds == [process]


# input:    | Variable "a1" { Value = 1.0 }  (also "a2" = 2.0, "b" = 3.0)
#           | Variable "a*" { Multiplier = 10.0 }
# expected: -> a1 = 10.0, a2 = 20.0, b = 3.0 (b is untouched)
def test_a_wildcard_name_targets_every_declared_match(read_deck):
    define = (
        emission_holding('Variable("a1")', name="e1")
        + emission_holding('Variable("a2")', name="e2")
        + emission_holding('Variable("b")', name="e3")
        + variable("a1", Value=1.0)
        + variable("a2", Value=2.0)
        + variable("b", Value=3.0)
        + variable("a*", Multiplier=10.0)
    )

    parser = read_deck(define)
    values = {name: node.get() for name, node in parser.nodes.variables.items()}

    assert values == {"a1": 10.0, "a2": 20.0, "b": 3.0}


# input:    | Variable "z*" { Value = 1.0 }   (no Variable name starts with z)
# expected: -> DeckKeywordError "No node of type 'Variable' matches the
#              wildcard expression 'z*'."
def test_a_wildcard_name_without_a_match_is_rejected(read_deck):
    with pytest.raises(
        DeckKeywordError,
        match=(
            r"define\.inc', line 5: No node of type 'Variable' matches the "
            r"wildcard expression 'z\*'\.$"
        ),
    ):
        read_deck(variable("z*", Value=1.0))


# input:    | Variable "x" { Value = 1.0 }
#           | Curve "x" { }
# expected: -> DeckKeywordError "Unable to add Curve("x"), the name is already
#              in use by a different node."
def test_a_name_in_use_by_another_node_type_is_rejected(read_deck):
    with pytest.raises(
        DeckKeywordError,
        match=(
            r"define\.inc', line 8: Unable to add Curve\(\"x\"\), the name is "
            r"already in use by a different node\.$"
        ),
    ):
        read_deck(variable("x", Value=1.0) + 'Curve "x" {\n}\n')


# input:    | ModelDefinition "x" { }   (in DEFINE or in EVENTS)
# expected: -> DeckKeywordError "'ModelDefinition' is a general node and is
#              declared without a name."
@pytest.mark.parametrize(
    ("define", "events", "location"),
    [
        (
            "",
            'Start\nDate "01-01-2027"\n' + NAMED_GENERAL_NODE + "End\n",
            r"line 2, include file '.*events\.inc', line 3",
        ),
        (NAMED_GENERAL_NODE, None, r"line 1, include file '.*define\.inc', line 5"),
    ],
    ids=["events", "define"],
)
def test_a_named_general_node_is_rejected(read_deck, define, events, location):
    with pytest.raises(
        DeckKeywordError,
        match=(
            rf"^Error in deck file, {location}: "
            r"'ModelDefinition' is a general node and is declared without a name\.$"
        ),
    ):
        read_deck(define, events=events)


# input:    | BunkerOptions { set_threads(2) }
# expected: -> CommandError "'BunkerOptions' does not support commands."
def test_a_command_on_a_general_node_is_rejected(read_deck):
    with pytest.raises(
        CommandError,
        match=r"define\.inc', line 6: 'BunkerOptions' does not support commands\.$",
    ):
        read_deck("BunkerOptions {\n    set_threads(2)\n}\n")


# input:    | ModelDefinition { StartDate = "01-01-2026" }
#           | ModelDefinition { EmissionsLifetime = 20 }
# expected: -> one ModelDefinition with start date 2026-01-01 and lifetime 20
def test_a_general_node_declared_twice_is_one_node(read_deck):
    define_base = (
        'ModelDefinition {\n    StartDate = "01-01-2026"\n}\n'
        "ModelDefinition {\n    EmissionsLifetime = 20\n}\n"
    )

    parser = read_deck(define_base=define_base)
    model_definition = parser.general_nodes.model_definition

    assert model_definition.start_date == np.datetime64("2026-01-01")
    assert model_definition.emissions_lifetime == 20


# input:    | ModelDefinition { StartDate = "01-01-2026" }   (no BunkerOptions)
# expected: -> a BunkerOptions node with its defaults is still created
def test_an_undeclared_bunker_options_falls_back_to_the_defaults(read_deck):
    parser = read_deck()

    assert isinstance(parser.general_nodes.bunker_options, BunkerOptions)


# input:    | DEFINE { Include "define.inc" }   (define.inc is empty)
# expected: -> DeckFormatError "Error in simulation: 'ModelDefinition' must be
#              defined."
def test_a_deck_without_a_model_definition_is_rejected(read_deck):
    with pytest.raises(
        DeckFormatError,
        match=r"^Error in simulation: 'ModelDefinition' must be defined\.$",
    ):
        read_deck(define_base="")


# input:    | EVENTS: Start
#           | Variable "new" { Value = 2.0 }
#           | End
# expected: -> DeckKeywordError "Unable to define new nodes outside DEFINE."
def test_a_new_node_in_events_is_rejected(read_deck):
    # the declaration is queued and only read when its date comes up
    parser = read_deck(events="Start\n" + variable("new", Value=2.0) + "End\n")

    with pytest.raises(
        DeckKeywordError,
        match=(r"events\.inc', line 2: Unable to define new nodes outside DEFINE\.$"),
    ):
        parser.progress_timeline()
