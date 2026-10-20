# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The prune: which declarations the simulation holds, and the events to apply.

A node takes part in the simulation only when a chain of references connects
it to a top-level node, one of the node types nothing assigns (ROOT_TYPES).
The walk starts there and follows every reference of a reached node's
effective body and of the events targeting it. A reference under a
NON_ACTIVATING attribute keeps nothing alive: a Levy's or Regulation's
Jurisdiction selects among routed ports and must not make an unrouted port
part of the fuel supply. The build phase constructs the kept declarations
only, so a node the simulation does not hold never exists: it receives no
value, enters no dependency dictionary and runs no command.

The prune is self-contained, as pruning may go: without it, every
declaration is kept and every bound event applies as bound.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from navigate.core.node_type import (
    EMISSION,
    FLEET,
    FUEL,
    LEVY,
    PLOT,
    PRODUCER,
    REGULATION,
    REPORT,
)
from navigate.parser._collect import Origin, matching
from navigate.parser._lark_parser import Assignment, item_references

if TYPE_CHECKING:
    from navigate.parser._collect import Collector, EventBlock, Key
    from navigate.parser._lark_parser import BodyItem
    from navigate.parser._resolve import BoundEvent

logger = logging.getLogger(__name__)

ROOT_TYPES = (EMISSION, FLEET, FUEL, LEVY, PLOT, PRODUCER, REGULATION, REPORT)

# the (node type, deck attribute) pairs whose references keep nothing alive
NON_ACTIVATING: frozenset[tuple[str, str]] = frozenset(
    {(LEVY, "Jurisdiction"), (REGULATION, "Jurisdiction")}
)


@dataclass
class Pruning:
    """What the prune left: the nodes the simulation holds and the events to apply."""

    # the kept declarations, in declaration order
    kept: list[Key]
    # each kept event with the kept declarations its name matches
    events: list[BoundEvent]


def is_activating(node_type: str, item: BodyItem) -> bool:
    """
    Whether the references an item holds make their targets part of the simulation.

    Parameters
    ----------
    node_type
        The type of the node the item is written on.
    item
        The assignment or command.

    Returns
    -------
    bool
        False only for an assignment to a NON_ACTIVATING attribute.
    """
    if isinstance(item, Assignment):
        return (node_type, item.attribute) not in NON_ACTIVATING

    return True


def prune(collector: Collector, events: list[BoundEvent]) -> Pruning:
    """
    Keep the declarations a top-level node reaches, and the events targeting them.

    Parameters
    ----------
    collector
        The deck as collected, every default pulled.
    events
        The events bound to the declarations they target.

    Returns
    -------
    Pruning
        The kept declarations, in declaration order, and the kept events,
        each with the kept declarations its name matches.

    Raises
    ------
    DeckError
        If a reached node references a name the deck and the library lack.
    """
    reached = _reach(collector, events)

    unreached = [key for key in collector.declarations if key not in reached]
    _warn_unused(collector, unreached)

    kept = [key for key in collector.declarations if key in reached]
    return Pruning(kept, _keep_events(events, reached))


def _reach(collector: Collector, events: list[BoundEvent]) -> set[Key]:
    """Walk the references from the top-level nodes; return the declarations reached."""
    events_of: dict[Key, list[EventBlock]] = {}
    for block, targets in events:
        for key in targets:
            events_of.setdefault(key, []).append(block)

    reached: set[Key] = {key for key in collector.declarations if key[0] in ROOT_TYPES}
    frontier = list(reached)

    while frontier:
        key = frontier.pop()
        declaration = collector.declarations[key]

        items = [(key[0], item) for item in declaration.effective_body()]
        for block in events_of.get(key, []):
            items.extend((block.node_type, item) for item in block.body)

        for node_type, item in items:
            if not is_activating(node_type, item):
                continue

            for reference, _ in item_references(item):
                targets = matching(
                    collector.declarations, reference.type, reference.name
                )
                if not targets and not reference.is_wildcard:
                    raise collector.library.missing_default(
                        reference.type, reference.name, item.source
                    )

                for target in targets:
                    if target not in reached:
                        reached.add(target)
                        frontier.append(target)

    return reached


def _warn_unused(collector: Collector, unreached: list[Key]) -> None:
    unused = [
        collector.declarations[key]
        for key in unreached
        if collector.declarations[key].origin is Origin.DECK
        and not collector.declarations[key].copied
    ]

    if not unused:
        return

    logger.warning(
        "%s node(s) declared but not used, as no top-level node (%s) references "
        "them, so they take no part in the simulation:%s\nAssign them to a parent "
        "node or remove them from the deck.",
        len(unused),
        ", ".join(ROOT_TYPES),
        "".join(f"\n\t- {declaration}" for declaration in unused),
    )


def _keep_events(events: list[BoundEvent], reached: set[Key]) -> list[BoundEvent]:
    kept: list[BoundEvent] = []
    dropped: list[EventBlock] = []

    for block, targets in events:
        kept_targets = [key for key in targets if key in reached]
        if kept_targets:
            kept.append((block, kept_targets))
        else:
            dropped.append(block)

    if dropped:
        logger.warning(
            "Dropped %s EVENTS statement(s) targeting only unused node(s):%s",
            len(dropped),
            "".join(
                f'\n\t- {block.node_type}("{block.pattern}") at {block.source.prefix()}'
                for block in dropped
            ),
        )

    return kept
