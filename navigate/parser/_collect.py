# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The collect phase: a deck's files read into declarations and events.

A declaration is one node's body items in read order, merged from every
block that names it; last read wins once the body is applied. A Copy
snapshots the source's items. The events are the EVENTS blocks with the date
each applies at. Every body item is checked against the attribute and
command registries as it is read, so a wrong name or section is reported at
its line in read order. Nothing is resolved here: a reference is still a
type and a name, and a wildcard declaration matches the names declared so far.

Once the deck's own files are read, every concrete reference to an undeclared
name pulls that name's file from the default library, repeated until nothing
more is pulled, as a pulled file may declare or extend further nodes. The
pull is best-effort: a name the library does not hold stays undeclared, and
the resolve phase raises for it only if a node the simulation holds
references it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from fnmatch import fnmatchcase
from typing import TYPE_CHECKING

from navigate.core.enum_ import SectionID
from navigate.core.node_registry import GENERAL_NODE_CLASS, NODE_CLASS
from navigate.parser._params import Params
from navigate.parser._syntax import (
    Assignment,
    Command,
    CopyStatement,
    DateStatement,
    EndTimeline,
    GeneralNodeDeclaration,
    ImportStatement,
    IncludeDirective,
    NodeDeclaration,
    SourceLocation,
    StartTimeline,
    item_references,
    parse_deck_content,
    parse_include_content,
)
from navigate.util import name_contains_wildcards

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from pathlib import Path

    import numpy as np

    from navigate.core.dsl import DeckEntry
    from navigate.parser._library import Library
    from navigate.parser._syntax import BodyItem, Directive, Statement

logger = logging.getLogger(__name__)

# a node declared by name: its type and name
type Key = tuple[str, str]

# the date a Start or Date keyword opens: None for Start, resolved once the start
# date is known
type StepDate = np.datetime64 | None


def matching(keys: Collection[Key], node_type: str, pattern: str) -> list[Key]:
    """Return the keys of a node type whose name the pattern matches, in order."""
    if not name_contains_wildcards(pattern):
        key = (node_type, pattern)
        return [key] if key in keys else []

    return [key for key in keys if key[0] == node_type and fnmatchcase(key[1], pattern)]


class Origin(Enum):
    """Where a declaration came from: the deck's own files, or a pulled library file."""

    DECK = auto()
    LIBRARY = auto()


@dataclass
class Declaration:
    """One node as the deck declares it: every body item naming it, in read order."""

    node_type: str
    name: str
    body: list[BodyItem]
    origin: Origin
    source: SourceLocation
    # whether a Copy took the node as its source
    copied: bool = False

    @property
    def key(self) -> Key:
        """The (type, name) the declaration is filed under."""
        return (self.node_type, self.name)

    def __repr__(self) -> str:
        return f'{self.node_type}("{self.name}")'

    def effective_body(self) -> list[BodyItem]:
        """
        Return the body items that act once the declaration is applied.

        Returns
        -------
        list[BodyItem]
            The last assignment of each attribute and every command, in read order.
        """
        last: dict[str, int] = {}
        for index, item in enumerate(self.body):
            if isinstance(item, Assignment):
                last[item.attribute] = index

        effective: list[BodyItem] = []
        for index, item in enumerate(self.body):
            superseded = isinstance(item, Assignment) and last[item.attribute] > index
            if not superseded:
                effective.append(item)

        return effective


@dataclass
class EventBlock:
    """A node block under EVENTS, applied at its date to the nodes its name matches."""

    date: StepDate
    node_type: str
    pattern: str
    body: list[BodyItem]
    source: SourceLocation


class Collector:
    """
    Read a deck and its files into declarations and events.

    Parameters
    ----------
    library
        The default library the deck's Import, Copy and Load statements and its
        references draw on.
    params
        Value of each %NAME% placeholder of the files, as text; None gives none.
    """

    def __init__(
        self, library: Library, params: Mapping[str, str] | None = None
    ) -> None:
        self.library: Library = library
        self.declarations: dict[Key, Declaration] = {}
        # each general node's body items, in read order
        self.general: dict[str, list[BodyItem]] = {}
        self.events: list[EventBlock] = []
        # every Start (None) and Date read, each a time step of the simulation
        self.timeline: list[StepDate] = []

        self._params: Params = Params(params or {})
        # names are unique across node types
        self._names: set[str] = set()
        self._origin: Origin = Origin.DECK
        # the nodes whose default files are being read, outermost first; a pull
        # of one of them again is a cycle between default files
        self._pulling: list[Key] = []

    # deck -----------------------------------------------------------------------------

    def read_deck(self, path: Path) -> None:
        """
        Read a deck file and every file it includes or loads.

        Parameters
        ----------
        path
            The resolved path of the .nav file.
        """
        try:
            content = path.read_text(encoding="utf8")
        except FileNotFoundError:
            raise FileNotFoundError(f"Unable to locate {path}.") from None

        content = self._params.fill(content, str(path), deck_line=0)
        deck = parse_deck_content(content, file=str(path))

        for directive in deck.define:
            self._read_directive(directive, path.parent, SectionID.DEFINE)

        for directive in deck.events:
            self._read_directive(directive, path.parent, SectionID.EVENTS)

        self._pull_references()

        for name in self._params.unused():
            logger.warning(
                "--set %s is unused: no file of the deck has '%%%s%%'.", name, name
            )

    def _read_directive(
        self, directive: Directive, directory: Path, section: SectionID
    ) -> None:
        deck_line = directive.source.line

        if isinstance(directive, IncludeDirective):
            path = directory / directive.path
            logger.debug("[%s] Include %s", section.name, path)
            self._read_file(path, deck_line, section)
            return

        location = SourceLocation(deck_line=deck_line)
        path = self.library.module_file(directive.name)
        if path is None:
            raise self.library.missing_module(directive.name, location)

        logger.debug("[%s] Load %s from %s", section.name, directive.name, path)
        self._read_file(path, deck_line, section)

    def _read_file(self, path: Path, deck_line: int, section: SectionID) -> None:
        try:
            content = path.read_text(encoding="utf8")
        except FileNotFoundError:
            raise SourceLocation(deck_line=deck_line).error(
                f"Include file '{path}' not found."
            ) from None

        content = self._params.fill(content, str(path), deck_line)
        statements = parse_include_content(content, file=str(path), deck_line=deck_line)

        if section is SectionID.DEFINE:
            self._walk_define(statements)
        else:
            self._walk_events(statements)

    # DEFINE ---------------------------------------------------------------------------

    def _walk_define(self, statements: list[Statement]) -> None:
        for statement in statements:
            if isinstance(statement, NodeDeclaration):
                self._declare(statement)
            elif isinstance(statement, GeneralNodeDeclaration):
                self._declare_general(statement)
            elif isinstance(statement, ImportStatement):
                self._import(statement)
            elif isinstance(statement, CopyStatement):
                self._copy(statement)
            else:
                raise statement.source.error(
                    f"'{statement.keyword}' is not allowed in the DEFINE section."
                )

    def _declare(self, statement: NodeDeclaration) -> None:
        node_type, name, source = statement.node_type, statement.name, statement.source

        _check_node_type(node_type, source)
        for item in statement.body:
            _validate_item(node_type, item, SectionID.DEFINE)

        targets = matching(self.declarations, node_type, name)
        if not targets:
            if name_contains_wildcards(name):
                raise source.error(
                    f"No node of type '{node_type}' matches the wildcard expression "
                    f"'{name}'."
                )

            targets = [self._new_declaration((node_type, name), source).key]

        for key in targets:
            check_no_self_reference(key, statement.body)
            self.declarations[key].body.extend(statement.body)

    def _declare_general(self, statement: GeneralNodeDeclaration) -> None:
        node_type = statement.node_type

        _check_general_node_type(node_type, statement.source)
        for item in statement.body:
            deck_entry(node_type, item, SectionID.DEFINE)

        self.general.setdefault(node_type, []).extend(statement.body)

    def _import(self, statement: ImportStatement) -> None:
        node_type, name, source = statement.node_type, statement.name, statement.source

        _check_node_type(node_type, source)

        if name_contains_wildcards(name):
            raise source.error(f"Import names one node; '{name}' is a wildcard.")

        key = (node_type, name)
        self._check_name_free(key, source)
        self._pull_required(key, source)
        self.declarations[key].origin = self._origin

    def _copy(self, statement: CopyStatement) -> None:
        node_type, source = statement.node_type, statement.source
        original_key = (node_type, statement.copy_from)
        copy_key = (node_type, statement.copy_to)

        if node_type in GENERAL_NODE_CLASS:
            raise source.error(f"'{node_type}' cannot be copied.")

        _check_node_type(node_type, source)
        self._check_name_free(copy_key, source)

        pulled = original_key not in self.declarations
        if pulled:
            self._pull_required(original_key, source)

        original = self.declarations[original_key]
        copy = self._new_declaration(copy_key, source)
        copy.body.extend(original.body)
        original.copied = True

        # a source pulled for the copy alone is not part of the deck: only the
        # copy remains, and a later reference pulls the source afresh
        if pulled:
            del self.declarations[original_key]
            self._names.remove(original.name)

    # EVENTS ---------------------------------------------------------------------------

    def _walk_events(self, statements: list[Statement]) -> None:
        # the date the blocks apply at: None for Start, once a date is read
        date: StepDate = None
        dated = False

        for statement in statements:
            if isinstance(statement, StartTimeline):
                date, dated = None, True
                self.timeline.append(None)
            elif isinstance(statement, DateStatement):
                date, dated = statement.date, True
                self.timeline.append(statement.date)
            elif isinstance(statement, EndTimeline):
                continue
            elif isinstance(statement, NodeDeclaration):
                if not dated:
                    raise statement.source.error(
                        "A node block under EVENTS must follow a Start or Date keyword."
                    )

                self._add_event(statement, date)
            else:
                raise statement.source.error(
                    f"'{statement.keyword}' is not allowed in the EVENTS section."
                )

    def _add_event(self, statement: NodeDeclaration, date: StepDate) -> None:
        node_type, source = statement.node_type, statement.source

        _check_node_type(node_type, source)
        for item in statement.body:
            _validate_item(node_type, item, SectionID.EVENTS)

        block = EventBlock(date, node_type, statement.name, statement.body, source)
        self.events.append(block)

    # library --------------------------------------------------------------------------

    def _pull_references(self) -> None:
        """Pull the file of every undeclared name a body references, to a fixpoint."""
        # a pulled file may declare new nodes, or append to declared ones through
        # a wildcard declaration, so the walk repeats until it pulls nothing
        pulled = True
        while pulled:
            pulled = False
            for item in self._body_items():
                for reference, _ in item_references(item):
                    if reference.is_wildcard or reference.key in self.declarations:
                        continue

                    pulled |= self._pull_default(reference.key, item.source)

    def _body_items(self) -> list[BodyItem]:
        """Every item of the declarations' effective bodies and of the events."""
        items: list[BodyItem] = []
        for declaration in self.declarations.values():
            items.extend(declaration.effective_body())
        for block in self.events:
            items.extend(block.body)

        return items

    def _pull_default(self, key: Key, source: SourceLocation) -> bool:
        """
        Read the library file declaring a default node.

        Parameters
        ----------
        key
            The node to read the file of.
        source
            Where the node is asked for, named in the errors the read file raises.

        Returns
        -------
        bool
            Whether the library holds a file for the node.
        """
        node_type, name = key

        # re-entering a file being read would read it without end
        if key in self._pulling:
            raise source.error(
                f'{node_type}("{name}") is pulled from the default library while '
                "its own default file is being read. Default files cannot import or "
                "copy each other in a cycle."
            )

        path = self.library.default_file(node_type, name)
        if path is None:
            return False

        self._read_default_file(path, key, source)

        if key not in self.declarations:
            raise source.error(
                f"A file with name '{name}' was found, but not containing a node "
                f"with type '{node_type}' and similar name."
            )

        logger.debug('%s("%s") was retrieved from the defaults.', node_type, name)
        return True

    def _pull_required(self, key: Key, source: SourceLocation) -> None:
        """Pull a default node a statement names outright, raising if there is none."""
        if not self._pull_default(key, source):
            node_type, name = key
            raise self.library.missing_default(node_type, name, source)

    def _read_default_file(self, path: Path, key: Key, source: SourceLocation) -> None:
        origin = self._origin
        self._origin = Origin.LIBRARY
        self._pulling.append(key)
        try:
            self._read_file(path, source.deck_line, SectionID.DEFINE)
        finally:
            self._pulling.pop()
            self._origin = origin

    # helpers --------------------------------------------------------------------------

    def _new_declaration(self, key: Key, source: SourceLocation) -> Declaration:
        node_type, name = key

        self._check_name_free(key, source)
        declaration = Declaration(node_type, name, [], self._origin, source)
        self.declarations[key] = declaration
        self._names.add(name)
        return declaration

    def _check_name_free(self, key: Key, source: SourceLocation) -> None:
        node_type, name = key
        if name in self._names:
            raise source.error(
                f'Unable to add {node_type}("{name}"), the name is already in use by '
                "a different node."
            )


# validation --------------------------------------------------------------------------


def _check_node_type(node_type: str, source: SourceLocation) -> None:
    """Raise at the source unless the keyword is a node type, declared with a name."""
    if node_type in GENERAL_NODE_CLASS:
        raise source.error(
            f"'{node_type}' is a general node and is declared without a name."
        )

    if node_type not in NODE_CLASS:
        raise source.error(f"'{node_type}' is not a recognized node type.")


def _check_general_node_type(node_type: str, source: SourceLocation) -> None:
    """Raise at the source unless the keyword is a general node, declared nameless."""
    if node_type in NODE_CLASS:
        raise source.error(f"'{node_type}' is a node type and is declared with a name.")

    if node_type not in GENERAL_NODE_CLASS:
        raise source.error(f"'{node_type}' is not a recognized node type.")


def deck_entry(node_type: str, item: BodyItem, section: SectionID) -> DeckEntry:
    """
    Look up the mark of an item's attribute or command on its node type.

    Parameters
    ----------
    node_type
        The node type or general node keyword the item is written on.
    item
        The assignment or command.
    section
        The section the item is written in.

    Returns
    -------
    DeckEntry
        The mark, allowing the item in the section.

    Raises
    ------
    DeckError
        At the item's line, where the node type has no such attribute or
        command, or does not allow it in the section.
    """
    if node_type in GENERAL_NODE_CLASS:
        if not isinstance(item, Assignment):
            raise item.source.error(f"'{node_type}' does not support commands.")

        subject = f"'{node_type}'"
        entries = GENERAL_NODE_CLASS[node_type].deck_attributes
        kind, verb = "attribute", "setting attribute"
    else:
        node_class = NODE_CLASS[node_type]
        subject = f"Nodes of type '{node_type}'"

        if isinstance(item, Assignment):
            entries = node_class.deck_attributes
            kind, verb = "attribute", "setting attribute"
        else:
            entries = node_class.deck_commands
            kind, verb = "command", "use of command"

    if item.name not in entries:
        raise item.source.error(f"{subject} has no {kind} '{item.name}'.")

    if section not in entries[item.name].sections:
        raise item.source.error(
            f"{subject} does not allow {verb} '{item.name}' in '{section.name}'."
        )

    return entries[item.name]


def check_no_self_reference(key: Key, body: list[BodyItem]) -> None:
    """
    Raise where a body item names the node it is written on.

    A node holding itself, directly, through a wildcard that matches its own
    name or inside an expression, would read its own value while computing
    it.

    Parameters
    ----------
    key
        The node the body applies to.
    body
        The items, each checked for a reference matching the key.
    """
    node_type, name = key

    for item in body:
        for reference, _ in item_references(item):
            if not matching({key}, reference.type, reference.name):
                continue

            through = (
                f" through the wildcard {reference}" if reference.is_wildcard else ""
            )
            raise item.source.error(
                f"{node_type}(\"{name}\") references itself in '{item.name}'{through}."
            )


def _validate_item(node_type: str, item: BodyItem, section: SectionID) -> None:
    """Check an item's attribute or command and its references, located."""
    deck_entry(node_type, item, section)

    for reference, in_expression in item_references(item):
        if reference.type not in NODE_CLASS:
            raise item.source.error(
                f"'{reference.type}' is not a recognized node type."
            )

        if not reference.is_wildcard:
            continue

        if in_expression:
            raise item.source.error(
                f"Expression references {reference}: a node reference in an "
                "expression must not contain wildcards."
            )

        if isinstance(item, Command):
            raise item.source.error(
                f"'{item.name}' does not accept a wildcard node reference as an "
                "argument."
            )
