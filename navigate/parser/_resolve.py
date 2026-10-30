# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The resolve phase: the EVENTS blocks against the declarations.

Each block is bound to the declarations its name matches: a wildcard to every
declaration of its type the pattern matches, a name to that declaration;
either must match something, as the EVENTS section cannot define new nodes.
Whether the targets take part in the simulation is not decided here;
`_prune.py` decides that next. Once it has, an event changing a calculator a
kept node's DEFINE-only input holds is refused: the calculator is fixed with
its holder.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import SECTION_DEFINE
from navigate.core.enum_ import SectionID
from navigate.core.node_type import CALCULATOR_TYPES
from navigate.parser._collect import (
    check_no_self_reference,
    deck_entry,
    matching,
    unmatched_wildcard_error,
)
from navigate.parser._syntax import Assignment, item_references
from navigate.util import name_contains_wildcards

if TYPE_CHECKING:
    from navigate.exceptions import DeckError
    from navigate.parser._collect import Collector, Declaration, EventBlock, Key

# an EVENTS block with the declarations its name matches
type BoundEvent = tuple[EventBlock, list[Key]]


def resolve(collector: Collector) -> list[BoundEvent]:
    """
    Bind every EVENTS block to the declarations its name matches.

    Parameters
    ----------
    collector
        The deck as collected, every default pulled.

    Returns
    -------
    list[BoundEvent]
        The EVENTS blocks in read order, each with the declarations it targets.

    Raises
    ------
    DeckError
        If a block names no declaration: a wildcard matching nothing, or a
        name the deck never declared.
    """
    bound: list[BoundEvent] = []

    for block in collector.events:
        targets = matching(collector.declarations, block.node_type, block.pattern)
        if not targets:
            raise _unmatched_error(block)

        for key in targets:
            check_no_self_reference(key, block.body)
        bound.append((block, targets))

    return bound


def _unmatched_error(block: EventBlock) -> DeckError:
    """Build the error for a block whose name matches no declaration."""
    if name_contains_wildcards(block.pattern):
        return unmatched_wildcard_error(block.node_type, block.pattern, block.source)

    return block.source.error(
        f"{block} is not defined; the EVENTS section cannot define new nodes."
    )


def check_pinned_calculators(
    collector: Collector, kept: list[Key], events: list[BoundEvent]
) -> None:
    """
    Raise for the first EVENTS assignment to a calculator a DEFINE-only input holds.

    A calculator held by a DEFINE-only attribute or command, directly, in a
    list, or through an expression, is fixed with it: changing it in EVENTS
    would change a nominally fixed input over time.

    Parameters
    ----------
    collector
        The deck as collected.
    kept
        The declarations the simulation holds, after the prune.
    events
        The events the prune kept, each with its kept targets.

    Raises
    ------
    DeckError
        If an event assigns an attribute of a calculator a DEFINE-only input
        holds.
    """
    pinned = _pinned_calculators(collector, kept)

    for block, targets in events:
        assignments = [item for item in block.body if isinstance(item, Assignment)]
        pinned_targets = [target for target in targets if target in pinned]
        if not assignments or not pinned_targets:
            continue

        assignment = assignments[0]
        target = pinned_targets[0]
        calculator = collector.declarations[target]
        holder, held_in = pinned[target]
        raise assignment.source.error(
            f"{calculator} does not allow setting attribute '{assignment.attribute}' "
            f"in 'EVENTS', as {holder} holds it in '{held_in}', which is DEFINE-only."
        )


def _pinned_calculators(
    collector: Collector, kept: list[Key]
) -> dict[Key, tuple[Declaration, str]]:
    """Map each calculator a kept DEFINE-only input holds to its holder and input."""
    pinned: dict[Key, tuple[Declaration, str]] = {}
    kept_keys = set(kept)

    for key in kept:
        declaration = collector.declarations[key]

        for item in declaration.effective_body():
            entry = deck_entry(declaration.node_type, item, SectionID.DEFINE)
            if entry.sections != SECTION_DEFINE:
                continue

            for reference, _ in item_references(item):
                if reference.type not in CALCULATOR_TYPES:
                    continue

                for target in matching(kept_keys, reference.type, reference.name):
                    pinned.setdefault(target, (declaration, item.name))

    return pinned
