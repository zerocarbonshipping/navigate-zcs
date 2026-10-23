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

    sections: AllowedSections
    required: bool = False


type DeckEntries = dict[str, DeckEntry]

_ATTRIBUTE_MARKS: dict[Callable[..., None], DeckEntry] = {}
_COMMAND_MARKS: dict[Callable[..., None], DeckEntry] = {}


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


def collect_deck_entries(cls: type) -> tuple[DeckEntries, DeckEntries]:
    """
    Gather the marked setters and commands of a class and its bases.

    Parameters
    ----------
    cls
        The node or general-node class.

    Returns
    -------
    DeckEntries
        The attributes, by deck name, in definition order from the base down.
    DeckEntries
        The commands, by name.
    """
    attributes: DeckEntries = {}
    commands: DeckEntries = {}

    for base in reversed(cls.__mro__):
        for name, member in vars(base).items():
            if not isinstance(member, FunctionType):
                continue

            if member in _ATTRIBUTE_MARKS:
                attributes[setter_to_attribute(name)] = _ATTRIBUTE_MARKS[member]
            elif member in _COMMAND_MARKS:
                commands[name] = _COMMAND_MARKS[member]

    return attributes, commands
