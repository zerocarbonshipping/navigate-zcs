# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The deck surface of a node class: the setters and commands a deck may call.

A setter marked ``deck_attribute`` takes the deck attribute its name spells,
so ``set_initial_vessels`` is ``InitialVessels``; a method marked
``deck_command`` is the deck command of the same name. The mark says which
sections may use it and, for an attribute, whether every deck must assign
it. A node class collects the marks of its whole inheritance chain when it
is created, so the parser reads the surface off the class and a base class
marks a setter once for every subclass.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import FunctionType
from typing import TYPE_CHECKING

from navigate.core.enum_ import SectionID
from navigate.util import setter_to_attribute

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

type AllowedSections = tuple[SectionID, ...]

SECTION_DEFINE: AllowedSections = (SectionID.DEFINE,)
SECTION_BOTH: AllowedSections = (SectionID.DEFINE, SectionID.EVENTS)


@dataclass(frozen=True)
class DeckEntry:
    """What a deck may do with one attribute or command."""

    # the sections a deck may use it in
    sections: AllowedSections
    # whether every deck must assign it; always False for a command
    required: bool = False


# the marked functions, keyed by the function object itself
_ATTRIBUTE_MARKS: dict[object, DeckEntry] = {}
_COMMAND_MARKS: dict[object, DeckEntry] = {}


def deck_attribute[F: Callable[..., None]](
    sections: AllowedSections = SECTION_BOTH, *, required: bool = False
) -> Callable[[F], F]:
    """
    Mark a setter as taking a deck attribute.

    Parameters
    ----------
    sections
        The sections a deck may assign the attribute in; both by default.
    required
        Whether every deck must assign it.

    Returns
    -------
    Callable[[F], F]
        The decorator, which returns the setter unchanged.
    """

    def mark(setter: F) -> F:
        _ATTRIBUTE_MARKS[setter] = DeckEntry(sections, required)
        return setter

    return mark


def deck_command[F: Callable[..., None]](
    sections: AllowedSections = SECTION_BOTH,
) -> Callable[[F], F]:
    """
    Mark a method as a deck command.

    Parameters
    ----------
    sections
        The sections a deck may call the command in; both by default.

    Returns
    -------
    Callable[[F], F]
        The decorator, which returns the method unchanged.
    """

    def mark(command: F) -> F:
        _COMMAND_MARKS[command] = DeckEntry(sections)
        return command

    return mark


def required_attributes(entries: Mapping[str, DeckEntry]) -> tuple[str, ...]:
    """
    Return the attributes every deck must assign, in declaration order.

    Parameters
    ----------
    entries
        A class's ``deck_attributes``.
    """
    return tuple(name for name, entry in entries.items() if entry.required)


def collect_deck_entries(
    cls: type,
) -> tuple[dict[str, DeckEntry], dict[str, DeckEntry]]:
    """
    Gather the marked setters and commands of a class and its bases.

    Parameters
    ----------
    cls
        The node or general-node class.

    Returns
    -------
    dict[str, DeckEntry]
        The attributes, by deck name, in definition order from the base down.
    dict[str, DeckEntry]
        The commands, by name.
    """
    attributes: dict[str, DeckEntry] = {}
    commands: dict[str, DeckEntry] = {}

    for base in reversed(cls.__mro__):
        for name, member in vars(base).items():
            if not isinstance(member, FunctionType):
                continue

            entry = _ATTRIBUTE_MARKS.get(member)
            if entry is not None:
                attributes[setter_to_attribute(name)] = entry
                continue

            entry = _COMMAND_MARKS.get(member)
            if entry is not None:
                commands[name] = entry

    return attributes, commands
