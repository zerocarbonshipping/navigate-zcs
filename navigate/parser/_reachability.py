# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Reachability analysis over the declared node graph.

A declared node participates in the simulation only when a chain of typed
node references connects it to a top-level node: the node types nothing
assigns (ROOT_TYPES) and the general nodes. Name-string keys in per-node
dicts parameterize a node but never activate it, so they do not count as
references. References live in resolved attributes, in queued commands, and
in queued EVENTS statements; an EVENTS reference keeps a node alive only
when the statement's target node is itself reachable.
"""

from navigate.core import Expression, NodeReference
from navigate.core.node import Node
from navigate.core.node_reference import WildcardNodeReference
from navigate.core.node_registry import GeneralNodes, Nodes
from navigate.core.node_type import EMISSION, FLEET, FUEL, LEVY, PLOT, PRODUCER, REGULATION, REPORT
from navigate.parser._commands import CommandReference
from navigate.parser._keywords import GENERAL_NODE_GROUP, NODE_GROUP
from navigate.parser._lark_parser import Assignment, Command, NodeDeclaration
from navigate.parser._scan import NODE_REFERENCE_PATTERN, REFERENCE_SCAN_EXCLUDE, get_attributes
from navigate.util import matching_keys

ROOT_TYPES = (EMISSION, FLEET, FUEL, LEVY, PLOT, PRODUCER, REGULATION, REPORT)
ROOT_GROUPS = tuple(NODE_GROUP[node_type] for node_type in ROOT_TYPES)


def find_unreachable(nodes: Nodes, general_nodes: GeneralNodes, event_queue: dict) -> list[tuple[str, str]]:
    """
    Find every declared node that no chain of references connects to a root.

    Parameters
    ----------
    nodes
        The registry of declared nodes.
    general_nodes
        The general nodes, whose references count as roots.
    event_queue
        The parser's queued EVENTS statements, keyed by date.

    Returns
    -------
    Sorted (node type, node name) pairs of the unreachable nodes; empty when
    every node is reachable.
    """

    event_edges = _collect_event_edges(event_queue, nodes)

    # frontier of (node type, node name) keys whose references are unexpanded
    pending = set()

    for group_name in ROOT_GROUPS:
        pending.update((node.type, node.name) for node in getattr(nodes, group_name).values())

    # general nodes can neither be referenced nor targeted by events, so
    # their references are collected once up front
    for field in GENERAL_NODE_GROUP.values():
        general_node = getattr(general_nodes, field)

        if general_node is None:
            continue

        for _, attribute in get_attributes(general_node, exclude=REFERENCE_SCAN_EXCLUDE):
            pending.update(_iter_references(attribute, nodes))

    reachable = set()

    while pending:
        node_type, name = pending.pop()

        if (node_type, name) in reachable:
            continue

        reachable.add((node_type, name))

        node = getattr(nodes, NODE_GROUP[node_type]).get(name)

        if node is None:
            continue

        for _, attribute in get_attributes(node, exclude=REFERENCE_SCAN_EXCLUDE):
            pending.update(_iter_references(attribute, nodes))

        pending.update(event_edges.get((node_type, name), ()))

    unreachable = []
    for node_type, group_name in NODE_GROUP.items():
        unreachable.extend((node_type, name) for name in getattr(nodes, group_name)
                           if (node_type, name) not in reachable)

    return sorted(unreachable)


def _iter_references(value, nodes: Nodes):
    """
    Yield the (node type, node name) of every node reference in a value,
    recursing containers the way the parser's reference resolution does.

    Kept in lockstep with Parser._replace_references_on_attribute: a value
    shape added there must be recognized here, or nodes referenced through
    that shape are wrongly pruned.

    Parameters
    ----------
    value
        Attribute value, command input, or queued EVENTS value.
    nodes
        The registry, used to expand wildcard references.
    """

    if isinstance(value, WildcardNodeReference):
        for name in matching_keys(value.pattern, getattr(nodes, NODE_GROUP[value.type])):
            yield value.type, name

    elif isinstance(value, (Node, NodeReference)):
        yield value.type, value.name

    elif isinstance(value, list):
        for element in value:
            yield from _iter_references(element, nodes)

    elif isinstance(value, dict):
        for element in value.values():
            yield from _iter_references(element, nodes)

    elif isinstance(value, Expression):
        for reference_string in value.reference_strings():
            match = NODE_REFERENCE_PATTERN.match(reference_string)
            if match is not None and match.group(1) in NODE_GROUP:
                yield match.group(1), match.group(3)

    elif isinstance(value, CommandReference):
        yield from _iter_references(value.inputs, nodes)


def _collect_event_edges(event_queue: dict, nodes: Nodes) -> dict:
    """
    Collect the node references inside queued EVENTS statements as edges from
    each statement's target node, so they keep a node alive only when the
    target is itself reachable.

    Parameters
    ----------
    event_queue
        The parser's queued EVENTS statements, keyed by date.
    nodes
        The registry, used to expand target names and wildcard references.

    Returns
    -------
    (target type, target name) mapped to the set of referenced
    (node type, node name) pairs. Target names absent from the registry are
    skipped; they resolve from the default library at event execution.
    """

    edges = {}

    for events in event_queue.values():
        for event in events:
            for statement in event.statements:

                if not isinstance(statement, NodeDeclaration):
                    continue

                target_names = matching_keys(statement.name, getattr(nodes, NODE_GROUP[statement.node_type]))

                if not target_names:
                    continue

                references = _statement_references(statement, nodes)

                if not references:
                    continue

                for target_name in target_names:
                    edges.setdefault((statement.node_type, target_name), set()).update(references)

    return edges


def _statement_references(statement: NodeDeclaration, nodes: Nodes) -> set:
    """
    Collect the node references in a queued statement's body.

    Parameters
    ----------
    statement
        A queued EVENTS re-assignment block.
    nodes
        The registry, used to expand wildcard references.

    Returns
    -------
    The referenced (node type, node name) pairs.
    """

    references = set()

    for body_statement in statement.body:
        if isinstance(body_statement, Assignment):
            references.update(_iter_references(body_statement.value, nodes))
        elif isinstance(body_statement, Command):
            references.update(_iter_references(body_statement.args, nodes))

    return references
