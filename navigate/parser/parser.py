# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import copy
import logging
import os
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import ClassVar

import numpy as np

from navigate.core import Expression
from navigate.core.enum_ import SimulationSectionID
from navigate.core.general_nodes.bunker_options import BunkerOptions
from navigate.core.node import Node
from navigate.core.node_registry import GeneralNodes, Nodes
from navigate.core.node_type import is_calculator
from navigate.exceptions import (
    AttributeAssignmentError,
    CommandError,
    DeckFormatError,
    DeckKeywordError,
)
from navigate.logging_ import log_time_step_breaker, print_preamble
from navigate.parser._attributes import (
    check_general_node_attribute_is_allowed,
    check_node_attribute_is_allowed,
    instance_to_dsl_name,
)
from navigate.parser._commands import CommandReference, check_node_command_is_allowed
from navigate.parser._event import Event
from navigate.parser._keywords import (
    DATE,
    END,
    GENERAL_NODE_GROUP,
    KEYWORD_SECTIONS,
    NODE_ALLOW_COPY,
    NODE_GROUP,
    SECTION_NAME,
    START,
    define_new_general_node,
    define_new_node,
)
from navigate.parser._lark_parser import (
    Assignment,
    Command,
    CopyStatement,
    DateStatement,
    DefineBlock,
    EndTimeline,
    EventsBlock,
    GeneralNodeDeclaration,
    ImportStatement,
    IncludeDirective,
    LoadModuleDirective,
    NodeDeclaration,
    SourceLocation,
    StartTimeline,
    parse_deck_content,
    parse_include_content,
    string_to_date,
)
from navigate.parser._node_reference import NodeReference, WildcardNodeReference
from navigate.parser._reachability import ROOT_TYPES, find_unreachable
from navigate.parser._scan import (
    REFERENCE_SCAN_EXCLUDE,
    get_attributes,
    parse_node_reference,
)
from navigate.util import (
    attribute_to_instance_name,
    attribute_to_setter,
    matching_keys,
    name_contains_wildcards,
    retrieve_keys,
    timedelta_to_days,
    wildcard_to_regex,
)

logger = logging.getLogger(__name__)


@dataclass
class _Deferred:
    """A node a reference named before any declaration provided it."""

    node: Node
    # the error prefix of the referencing line, for when neither a declaration
    # nor a default file turns up
    location: str


@dataclass(frozen=True)
class _PendingAssignment:
    """An assignment held back until its wildcard can be expanded."""

    node: Node
    attribute: str
    value: object
    source: SourceLocation
    deck_line: int


class Parser:
    def __init__(self):
        """Read and process Navigate input decks (.nav and .inc files)."""
        # nodes
        self.nodes = Nodes()
        self.general_nodes = GeneralNodes()

        # event queue
        self.dates = []
        self._event_queue = {}
        self._idx_date = 0
        self._current_date = None
        self._current_event = None

        # paths
        self._exe_directory = None
        self._deck_path = None
        self.deck_directory = None
        self.deck_name = None
        self._user_default_directory = None
        self._user_module_directory = None
        self._installation_default_directory = None
        self._installation_module_directory = None

        # dynamic flags
        self._reading_events = False
        self._place_in_queue = False
        self._reading_default = False
        self._pruned_nodes = set()
        self._copy_source_names = set()
        self._user_default_name = None

        # nodes a reference named before their declaration, keyed by (type,
        # name); kept out of the registry until a declaration adopts them
        self._deferred: dict[tuple[str, str], _Deferred] = {}
        # (type, name) of the from_default Copy sources whose pulls are in
        # progress, one entry per pull: they leave the registry after the
        # copy, so nothing may bind to them
        self._provisional: list[tuple[str, str]] = []
        # assignments whose value carries a wildcard, held until the registry
        # holds every node the glob may match
        self._pending_assignments: list[_PendingAssignment] = []

        # section flags
        self._current_section = None
        self._finished_sections = []

        # source tracking — set per include-file processing pass
        self._current_deck_line = 0
        self._current_source = SourceLocation()

    # ══════════════════════════════════════════════════════════════════
    # Deck (.nav) reading — Lark-based
    # ══════════════════════════════════════════════════════════════════

    def read_deck(self, path: Path, data_dir: Path | None = None) -> None:
        """
        Read and process the main .nav deck file.

        Parameters
        ----------
        path
            Full or relative path to the input deck file.
        data_dir
            Assumptions data folder.
        """
        path = Path(path).resolve()

        try:
            with open(path, encoding="utf8") as f:
                content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Unable to locate {path}.") from None

        self._deck_path = path
        self.deck_directory = str(path.parent)
        self.deck_name = path.stem
        self._define_internal_directories(data_dir=data_dir)

        print_preamble()

        blocks = parse_deck_content(content, file=str(path))

        for block in blocks:
            self._process_deck_block(block)

        if len(self._finished_sections) < 2:
            raise DeckFormatError(
                "Both a DEFINE and an EVENTS block must be defined in the deck."
            )

        self._initialize_general_nodes()

        self._current_section = SimulationSectionID.DEFINE
        self._update_dependencies()

        self._replace_start_keyword()
        self._timeline_is_consistent()

        self._current_section = SimulationSectionID.EVENTS
        self._reading_events = True

    @classmethod
    def parse_plot_nodes(cls, path, data_dir=None):
        """
        Parse Plot nodes from a standalone include (.inc) file.

        Used by ``--replot`` to plot from Plot node definitions supplied in an
        include file instead of those captured in the plot data.

        Parameters
        ----------
        path : str or Path
            Path to the .inc file containing one or more Plot node declarations.
        data_dir : Path or None
            Assumptions data folder (only required if the include imports nodes).

        Returns
        -------
        dict[str, Plot]
            Parsed Plot nodes keyed by name.
        """
        parser = cls()
        parser._define_internal_directories(
            data_dir=data_dir
        )  # no-op if data_dir is None
        parser._current_section = SimulationSectionID.DEFINE
        parser._read_include_file(str(path))
        for node in parser.nodes.plots.values():
            parser._execute_node_commands(node)  # runs queued add_plot(...) commands
        return parser.nodes.plots

    def _process_deck_block(self, block):
        """Process a single Define or Events block from the deck AST."""
        if isinstance(block, DefineBlock):
            section = SimulationSectionID.DEFINE
        elif isinstance(block, EventsBlock):
            section = SimulationSectionID.EVENTS
        else:
            raise DeckFormatError(f"Unknown deck block type: {type(block).__name__}")

        self._begin_reading_section(section)

        for directive in block.directives:
            self._current_deck_line = directive.source.line

            if isinstance(directive, IncludeDirective):
                logger.debug(
                    '[%s] Include "%s"', self._current_section.name, directive.path
                )
                self._read_include_file(directive.path)

            elif isinstance(directive, LoadModuleDirective):
                logger.debug("[%s] Load %s", self._current_section.name, directive.name)
                self._load_module(directive)

        self._end_reading_section()

    def progress_timeline(self):
        """
        Progress the timeline to the next date and process events.

        Returns
        -------
        np.datetime64
            Date of the next event in the timeline.
        """
        self._reading_events = True

        date, events = self._next_event()

        if (self._idx_date > 1) and (date is not None):
            log_time_step_breaker(
                logger,
                self._idx_date - 1,
                date,
                timedelta_to_days(date - self.dates[0]),
            )

        self._current_date = date

        for event in events:
            self._read_event(event)

        self._update_dependencies()

        return date

    # ── error formatting ──────────────────────────────────────────────

    def _error_prefix(
        self, source: SourceLocation | None = None, deck_line: int | None = None
    ):
        """
        Build an error prefix string from source location.

        Parameters
        ----------
        source : SourceLocation, optional
            Include file location.  Falls back to ``self._current_source``.
        deck_line : int, optional
            Deck line.  Falls back to ``self._current_deck_line``.
        """
        source = source or self._current_source
        dl = deck_line if deck_line is not None else self._current_deck_line
        parts = []
        if dl:
            parts.append(f"Error in deck file, line {dl}")
        if source.file:
            parts.append(f"include file '{source.file}', line {source.line}")
        return ", ".join(parts) if parts else "Parser error"

    def _deck_error_prefix(self):
        return f"Error in deck file, line {self._current_deck_line}"

    # ── internal directories ──────────────────────────────────────────

    def _define_internal_directories(self, data_dir: Path | None = None) -> None:
        self._exe_directory = os.path.dirname(os.path.abspath(__file__))
        if data_dir:
            data_dir = Path(data_dir).resolve()
            self._user_default_directory = str(data_dir / "defaults/user")
            self._user_module_directory = str(data_dir / "modules/user")
            self._installation_default_directory = str(
                data_dir / "defaults/installation"
            )
            self._installation_module_directory = str(data_dir / "modules/installation")

    # ══════════════════════════════════════════════════════════════════
    # Include / Import
    # ══════════════════════════════════════════════════════════════════

    def _read_include_file(self, path):
        """
        Read, parse, and process an include file.

        Parameters
        ----------
        path : str
            Path of include file (relative to deck directory).
        """
        if not os.path.isabs(path):
            path = os.path.join(self.deck_directory or "", path)

        try:
            with open(path, encoding="utf8") as f:
                content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(
                self._deck_error_prefix() + f": Include file '{path}' not found."
            ) from None

        abs_path = os.path.abspath(path) if not os.path.isabs(path) else path

        statements = parse_include_content(content, file=abs_path)

        self._process_statements(statements)

    def _load_module(self, directive):
        """
        Load a module referenced in the deck file.

        Parameters
        ----------
        directive : LoadModuleDirective
            The parsed Load directive.
        """
        if not self._user_module_directory or not self._installation_module_directory:
            raise DeckFormatError(
                self._deck_error_prefix()
                + f": Module '{directive.name}' is requested but no assumptions "
                "directory is specified. Use the -d flag or ASSUMPTIONS_DATA_DIR."
            )

        file_name = attribute_to_instance_name(directive.name)

        found = self._read_default_folder(file_name, self._user_module_directory)
        if found:
            logger.debug(
                "Module '%s' was retrieved from the User Module folder.", directive.name
            )
            return

        found = self._read_default_folder(
            file_name, self._installation_module_directory
        )
        if found:
            logger.debug(
                "Module '%s' was retrieved from the Installation Module folder.",
                directive.name,
            )
        else:
            raise DeckKeywordError(f"No module with name '{directive.name}' was found.")

    # ══════════════════════════════════════════════════════════════════
    # AST statement processing
    # ══════════════════════════════════════════════════════════════════

    def _process_statements(self, statements):
        """Walk a list of AST statements from a parsed .inc file."""
        for statement in statements:
            self._current_source = getattr(statement, "source", self._current_source)

            if isinstance(statement, StartTimeline):
                self._start_timeline()

            elif isinstance(statement, EndTimeline):
                self._end_timeline()

            elif isinstance(statement, DateStatement):
                self._read_date(statement)

            elif self._place_in_queue:
                self._current_event.add_statement(statement)

            else:
                self._process_event_statement(statement)

    _EVENT_DISPATCH: ClassVar[dict[type, str]] = {
        GeneralNodeDeclaration: "_process_general_node_declaration",
        NodeDeclaration: "_process_node_declaration",
        ImportStatement: "_process_import_node",
        CopyStatement: "_process_copy_node",
    }

    def _process_event_statement(self, statement):
        """Process a single AST statement (node declaration, copy, import)."""
        handler_name = self._EVENT_DISPATCH.get(type(statement))
        if handler_name is None:
            raise DeckKeywordError(self._error_prefix() + ": Action not recognized.")
        getattr(self, handler_name)(statement)

    # ══════════════════════════════════════════════════════════════════
    # Event queue & timeline
    # ══════════════════════════════════════════════════════════════════

    def _next_event(self):
        if self._idx_date < len(self.dates):
            date = self.dates[self._idx_date]
        else:
            return None, []

        events = self._event_queue.get(date, [])
        self._idx_date += 1
        return date, events

    def _read_event(self, event):
        """Process stored AST statements from a queued event."""
        self._reading_events = True
        self._current_event = event
        self._current_deck_line = event.deck_line
        self._current_source = event.source

        for statement in event.statements:
            self._current_source = getattr(statement, "source", self._current_source)
            self._process_event_statement(statement)

        self._current_event = None
        self._reading_events = False

    def _begin_reading_section(self, section):
        self._check_section(section)
        self._current_section = section
        logger.debug("Reading section %s", self._current_section.name)

    def _check_section(self, section):
        if self._current_section is not None:
            raise DeckFormatError(
                self._deck_error_prefix()
                + (
                    f": Unable to begin {SECTION_NAME[section]} while reading "
                    f"{SECTION_NAME[self._current_section]}."
                )
            )

        if section in self._finished_sections:
            raise DeckFormatError(
                self._deck_error_prefix()
                + (
                    ": Each section can only be defined once and must be read in "
                    "the order {}."
                ).format(", ".join(SECTION_NAME.values()))
            )

        if (
            section == SimulationSectionID.DEFINE
            and SimulationSectionID.EVENTS in self._finished_sections
        ):
            raise DeckFormatError(
                self._deck_error_prefix()
                + (
                    ": Each section can only be defined once and must be read in "
                    "the order {}."
                ).format(", ".join(SECTION_NAME.values()))
            )

    def _end_reading_section(self):
        if self._current_section is not None:
            self._finished_sections.append(self._current_section)
            self._current_section = None
            self._reading_events = False
            self._place_in_queue = False
        else:
            raise DeckFormatError(
                self._deck_error_prefix()
                + ": Unable to end section, no section is defined."
            )

    def _check_timeline_change(self):
        if self._reading_default:
            raise DeckFormatError(
                f"Error while retrieving default, include file "
                f"'{self._current_source.file}', line {self._current_source.line}"
                + ": Unable to alter timeline while retrieving default nodes."
            )

    def _start_timeline(self):
        self._check_keyword(START)
        self._check_timeline_change()

        if self._current_date is not None:
            raise DeckFormatError(
                self._error_prefix()
                + ": Unable to start a new timeline while one is in progress."
            )

        self._reading_events = True
        self._place_in_queue = True
        self._assign_current_event(START)

    def _end_timeline(self):
        self._check_keyword(END)
        self._check_timeline_change()

        self._reading_events = False
        self._place_in_queue = False
        self._current_date = None

    def _read_date(self, statement):
        """Process a DateStatement AST node."""
        self._check_keyword(DATE)
        self._check_timeline_change()

        date = string_to_date(
            statement.date_string,
            msg="Error in date definition: Must be in format dd-mm-yyyy or dd/mm/yyyy.",
        )
        self._progress_is_chronological(date)
        self._assign_current_event(date)

    def _assign_current_event(self, date):
        if not self._place_in_queue:
            self._reading_events = False
            self._place_in_queue = True

        event = Event(source=self._current_source, deck_line=self._current_deck_line)

        if date not in self._event_queue:
            self.dates.append(date)
            self._event_queue[date] = [event]
        else:
            self._event_queue[date].append(event)

        self._current_date = date
        self._current_event = event

    def _progress_is_chronological(self, date):
        if (
            (self._current_date is not None)
            and (not isinstance(self._current_date, str))
            and date <= self._current_date
        ):
            raise DeckFormatError(
                self._error_prefix()
                + ": Dates must be ordered chronologically within individual "
                "include files."
            )

    def _replace_start_keyword(self):
        start_date = self.general_nodes.model_definition.start_date

        self.dates = np.array(
            [start_date if d == START else d for d in self.dates], dtype="datetime64[D]"
        )
        self.dates = np.unique(self.dates)

        if START in self._event_queue:
            if start_date not in self._event_queue:
                start_events = []
            else:
                start_events = self._event_queue.pop(start_date)

            self._event_queue[start_date] = [
                *self._event_queue.pop(START),
                *start_events,
            ]

        else:
            if start_date not in self.dates:
                self.dates = np.insert(self.dates, 0, start_date)
                self._event_queue[start_date] = []

    def _timeline_is_consistent(self):
        start_date = self.general_nodes.model_definition.start_date

        msg = ""
        for date in self.dates:
            if date < start_date:
                for event in self._event_queue.get(date, []):
                    msg += (
                        f"\t- NAV file, line {event.deck_line}, include file "
                        f"'{event.source.file}', line {event.source.line}: Date "
                        f"'{date}' is before start date '{start_date}'\n"
                    )

        if msg:
            msg = (
                f"Inconsistent timeline detected:\n{msg}All defined dates must be "
                f"later than the start date."
            )
            raise DeckFormatError(msg)

    # ══════════════════════════════════════════════════════════════════
    # Node body processing — shared helpers
    # ══════════════════════════════════════════════════════════════════

    def _apply_assignment(self, nodes, item, node_type, is_general=False):
        """
        Validate and apply an Assignment AST node to one or more nodes.

        Parameters
        ----------
        nodes : list[Node] or single node
            Target node(s).
        item : Assignment
            The assignment AST node.
        node_type : str
            Node type string for validation.
        is_general : bool
            Whether this is a general node (uses different validation).
        """
        self._current_source = item.source
        attribute = item.attribute

        try:
            if is_general:
                check_general_node_attribute_is_allowed(
                    node_type, attribute, self._current_section
                )
            else:
                check_node_attribute_is_allowed(
                    node_type, attribute, self._current_section
                )

        except DeckFormatError:
            raise DeckFormatError(
                self._error_prefix()
                + f": '{item.attribute}' is not a valid assignment."
            ) from None

        except AttributeAssignmentError as e:
            raise AttributeAssignmentError(self._error_prefix() + f": {e!s}.") from None

        value = self._materialize(item.value)
        deck_line = self._current_deck_line

        target_nodes = nodes if isinstance(nodes, list) else [nodes]

        # a glob matches against the finished registry, so the assignment waits
        if _contains_wildcard(value):
            self._pending_assignments += [
                _PendingAssignment(node, attribute, value, item.source, deck_line)
                for node in target_nodes
            ]
            return

        for node in target_nodes:
            self._call_setter(node, attribute, value, item.source, deck_line)

    def _call_setter(self, node, attribute, value, source, deck_line):
        """
        Hand a value to the setter of the deck attribute that names it.

        Parameters
        ----------
        node : Node
            Node the assignment targets.
        attribute : str
            Deck-facing attribute token.
        value
            The value to assign, with every reference already a node.
        source : SourceLocation
            Include-file location of the assignment.
        deck_line : int
            Deck line of the assignment.
        """
        try:
            getattr(node, attribute_to_setter(attribute))(value)

        except ValueError as e:
            raise AttributeAssignmentError(
                self._error_prefix(source, deck_line)
                + f": {node} attribute '{attribute}' {e}."
            ) from None

    def _queue_command(self, nodes, item, node_type):
        """
        Validate and queue a Command AST node on one or more nodes.

        Parameters
        ----------
        nodes : list[Node] or single node
            Target node(s).
        item : Command
            The command AST node.
        node_type : str
            Node type string for validation.
        """
        self._current_source = item.source
        command = item.name

        try:
            check_node_command_is_allowed(node_type, command, self._current_section)

        except CommandError as e:
            raise CommandError(self._error_prefix() + f": {e!s}.") from None

        inputs = self._materialize(item.args)

        if _contains_wildcard(inputs):
            raise CommandError(
                self._error_prefix()
                + f": '{command}' does not accept a wildcard node reference as an "
                "argument."
            )

        ref = CommandReference(
            command, inputs, source=item.source, deck_line=self._current_deck_line
        )

        target_nodes = nodes if isinstance(nodes, list) else [nodes]
        for node in target_nodes:
            node.add_command_reference(ref)

    # ══════════════════════════════════════════════════════════════════
    # Node declaration processing
    # ══════════════════════════════════════════════════════════════════

    def _process_node_declaration(self, declaration):
        """Process a NodeDeclaration AST node."""
        self._check_keyword(declaration.node_type, name=declaration.name)
        nodes = self._retrieve_nodes(declaration.node_type, declaration.name)

        for item in declaration.body:
            item_type = type(item)
            if item_type is Command:
                self._queue_command(nodes, item, declaration.node_type)
            elif item_type is Assignment:
                self._apply_assignment(nodes, item, declaration.node_type)
            else:
                raise DeckKeywordError(
                    self._error_prefix(item.source)
                    + f": '{type(item).__name__}' is not a valid keyword."
                )

    def _process_general_node_declaration(self, declaration):
        """Process a GeneralNodeDeclaration AST node."""
        self._check_keyword(declaration.node_type)
        general_node = self._retrieve_general_node(declaration.node_type)

        for item in declaration.body:
            item_type = type(item)
            if item_type is Command:
                raise CommandError(
                    self._error_prefix(item.source)
                    + f": '{declaration.node_type}' does not support commands."
                )
            elif item_type is Assignment:
                self._apply_assignment(
                    general_node, item, declaration.node_type, is_general=True
                )
            else:
                raise DeckKeywordError(
                    self._error_prefix(item.source)
                    + f": '{type(item).__name__}' is not a valid keyword."
                )

        setattr(
            self.general_nodes, GENERAL_NODE_GROUP[declaration.node_type], general_node
        )

    def _process_copy_node(self, statement):
        """Process a CopyStatement AST node."""
        self._check_allow_new_node("copy")
        self._check_keyword(statement.node_type)

        if not NODE_ALLOW_COPY[statement.node_type]:
            raise ValueError(
                self._error_prefix()
                + f": Unable to copy nodes of type '{statement.node_type}'."
            )

        self._check_node_name_is_available(statement.node_type, statement.copy_to)

        group = getattr(self.nodes, NODE_GROUP[statement.node_type])
        source_key = (statement.node_type, statement.copy_from)

        from_default = statement.copy_from not in group
        if from_default:
            # the source leaves the registry again after the copy, so nothing
            # read during its pull may bind to it: references defer instead,
            # and its declaration adopts no placeholder
            self._provisional.append(source_key)
            try:
                self._retrieve_node_from_default(
                    statement.node_type, statement.copy_from, self._error_prefix()
                )
            finally:
                self._provisional.remove(source_key)

        source = group[statement.copy_from]
        # the memo makes deepcopy return the registry node, or the deferred
        # placeholder, for everything the source reaches; the source must stay
        # out of it or deepcopy returns the source itself
        memo = {id(node): node for node in self.nodes.all_nodes()}
        memo.update((id(entry.node), entry.node) for entry in self._deferred.values())
        del memo[id(source)]
        new_node = copy.deepcopy(source, memo)
        new_node.name = statement.copy_to

        existing = self._adopt(statement.node_type, statement.copy_to)
        if existing is None:
            # a declaration inside the pulled file may have adopted the
            # placeholder and registered it under the target's name; the copy
            # takes that node over, as it replaced it in the registry before,
            # so every holder sees the copy
            existing = group.get(statement.copy_to)
        if existing is not None:
            new_node = _transplant(existing, new_node)

        # the parser holds a pending assignment, not the source, so deepcopy
        # leaves it behind and the copy needs an entry of its own
        self._pending_assignments += [
            replace(entry, node=new_node)
            for entry in self._pending_assignments
            if entry.node is source
        ]

        if from_default:
            del group[statement.copy_from]
        else:
            self._copy_source_names.add(source_key)

        group[statement.copy_to] = new_node

    def _process_import_node(self, statement):
        """Process an ImportStatement AST node."""
        self._check_allow_new_node("import")
        self._check_keyword(statement.node_type)

        if name_contains_wildcards(statement.name):
            self._read_import_node_wildcard(statement.node_type, statement.name)
        else:
            self._check_node_name_is_available(statement.node_type, statement.name)
            self._retrieve_node_from_default(
                statement.node_type, statement.name, self._error_prefix()
            )

    # ══════════════════════════════════════════════════════════════════
    # Node retrieval / creation
    # ══════════════════════════════════════════════════════════════════

    def _retrieve_nodes(self, node_type, name):
        group = getattr(self.nodes, NODE_GROUP[node_type])

        if name_contains_wildcards(name):
            regex = wildcard_to_regex(name)
            nodes = [node for key, node in group.items() if re.match(regex, key)]
            if not nodes:
                raise DeckKeywordError(
                    f"{self._error_prefix()}: No node of type '{node_type}' matches "
                    f"the wildcard expression '{name}'."
                )
            return nodes

        if name in group:
            return [group[name]]

        self._check_allow_new_node("define")
        self._check_node_name_is_available(node_type, name)
        node = self._adopt(node_type, name)
        if node is None:
            node = define_new_node(node_type, name)
        # registered before the body is read, so a reference in the body to
        # the node itself binds to it
        group[name] = node
        return [node]

    def _retrieve_general_node(self, type_: str):
        field = GENERAL_NODE_GROUP[type_]
        general_node = getattr(self.general_nodes, field)
        if general_node is None:
            general_node = define_new_general_node(type_)
            setattr(self.general_nodes, field, general_node)
        return general_node

    def _check_allow_new_node(self, action):
        if self._current_section != SimulationSectionID.DEFINE:
            raise DeckKeywordError(
                self._error_prefix() + f": Unable to {action} new nodes outside DEFINE."
            )

    def _check_keyword(self, keyword, name=None):
        if keyword in KEYWORD_SECTIONS:
            if self._current_section not in KEYWORD_SECTIONS[keyword]:
                if self._reading_default:
                    raise DeckKeywordError(
                        f'Unable to reference {keyword}("{name}") as it is not '
                        f"previously defined."
                    )
                else:
                    raise DeckKeywordError(
                        self._error_prefix()
                        + f": '{keyword}' is not an allowed keyword in section "
                        f"{SECTION_NAME[self._current_section]}."
                    )
        else:
            raise DeckKeywordError(
                self._error_prefix() + f": \n'{keyword}' is not a recognized keyword. "
                "Check the attributes and commands for spelling"
            )

    def _check_node_name_is_available(self, node_type, name):
        if name in self._get_all_node_names():
            raise ValueError(
                self._error_prefix()
                + f': Unable to add {node_type}("{name}"), the name is already in use '
                f"by a different node."
            )

    def _read_import_node_wildcard(self, node_type, name_pattern):
        if not self._user_default_directory or not self._installation_default_directory:
            raise DeckKeywordError(
                self._deck_error_prefix()
                + ": Wildcard Import is requested but default directories are not "
                "specified. Please specify the assumptions location with the -d flag "
                "or environment variable "
            )

        pattern = re.compile(wildcard_to_regex(name_pattern))

        user_dir = os.path.join(self._user_default_directory, node_type)
        install_dir = os.path.join(self._installation_default_directory, node_type)

        matched_names = {}

        for directory in (user_dir, install_dir):
            if not os.path.isdir(directory):
                continue
            for file_name in _get_files_in_directory(directory):
                basename = os.path.splitext(file_name)[0]
                if pattern.match(basename) and basename not in matched_names:
                    matched_names[basename] = directory

        if not matched_names:
            raise DeckKeywordError(
                f"{self._error_prefix()}: No {node_type} defaults matching "
                f"'{name_pattern}' found in user or installation folders."
            )

        for name in sorted(matched_names):
            self._check_node_name_is_available(node_type, name)
            self._retrieve_node_from_default(node_type, name, self._error_prefix())

    # ══════════════════════════════════════════════════════════════════
    # Collection helpers
    # ══════════════════════════════════════════════════════════════════

    def includes_necessary_information(self):
        checks = [
            (self.dates, "timeline"),
            (self.nodes.fleets, "Fleets"),
            (self.nodes.fuels, "Fuels"),
            (self.nodes.ports, "Ports"),
            (self.nodes.vessels, "Vessels"),
        ]
        missing = [label for collection, label in checks if len(collection) == 0]
        if missing:
            msg = "".join(
                f"\t- No {m} are defined.\n"
                if m != "timeline"
                else "\t- No timeline is defined.\n"
                for m in missing
            )
            raise DeckKeywordError(f"Unable to run a simulation:\n{msg}")

    def _get_all_nodes(self):
        return list(self.nodes.all_nodes())

    def _get_all_node_names(self):
        return list(self.nodes.all_names())

    # ══════════════════════════════════════════════════════════════════
    # Semantic passes
    # ══════════════════════════════════════════════════════════════════

    def _initialize_general_nodes(self):
        if self.general_nodes.model_definition is None:
            raise DeckFormatError(
                "Error in simulation: 'ModelDefinition' must be defined."
            )

        self.general_nodes.model_definition.check_requirements()

        if self.general_nodes.bunker_options is None:
            self.general_nodes.bunker_options = BunkerOptions()

        self.general_nodes.bunker_options.check_requirements()

    def _update_dependencies(self):
        """
        Replace references, execute commands, initialize nodes.

        The sequence is: expand held-back wildcards → replace refs → replace
        tables → prune unreachable nodes (DEFINE pass only) → init dicts →
        execute commands → replace refs again (commands may create new ones) →
        replace tables again → initialize nodes.
        """
        self._reading_events = True

        self._flush_pending_assignments()
        self._replace_references()
        self._replace_temporary_tables()

        # prune before the dependency dicts are seeded so no dict carries a
        # key for a node that is absent from the registry; the per-time-step
        # calls arrive under EVENTS, so the prune runs exactly once
        if self._current_section == SimulationSectionID.DEFINE:
            self._prune_unreachable_nodes()

        self._initialize_dependent_dicts()
        self._execute_commands()

        self._replace_references()
        self._replace_temporary_tables()

        self._initialize_nodes()

        self._reading_events = False

    def _prune_unreachable_nodes(self):
        """Remove every node no chain of references connects to a root."""
        unreachable = find_unreachable(
            self.nodes, self.general_nodes, self._event_queue
        )

        if not unreachable:
            return

        for node_type, name in unreachable:
            del getattr(self.nodes, NODE_GROUP[node_type])[name]

        self._pruned_nodes = set(unreachable)
        scrubbed = self._scrub_references_to_pruned()
        dropped_statements = self._drop_event_statements_targeting_pruned()

        # a node used only as a Copy source served its purpose at parse time
        # and is removed without a warning
        reported = [pair for pair in unreachable if pair not in self._copy_source_names]

        if reported:
            self._handle_unreachable(reported, dropped_statements)

        elif dropped_statements:
            logger.warning(
                "Dropped %s queued EVENTS statement(s) targeting node(s) removed after "
                "use as a Copy source; re-assign the copies instead.",
                dropped_statements,
            )

        # reported independently: a scrub changes a surviving node even when
        # the pruned target itself was a silently removed Copy source
        if scrubbed:
            self._warn_scrubbed_references(scrubbed)

    def _handle_unreachable(self, reported: list, dropped_statements: int) -> None:
        """
        Warn about the pruned nodes.

        Detection stays separate from this action so pruning can be made
        fatal by raising ``DeckInsufficientError`` here instead.

        Parameters
        ----------
        reported
            The pruned (node type, node name) pairs to warn about.
        dropped_statements
            Number of queued EVENTS statements dropped with them.
        """
        lines = "".join(f'\n\t- {node_type}("{name}")' for node_type, name in reported)

        dropped = ""
        if dropped_statements:
            dropped = (
                f"\nAlso dropped {dropped_statements} queued EVENTS statement(s) "
                f"targeting only removed nodes."
            )

        logger.warning(
            "Removed %s node(s) not reachable from any top-level node (%s) and "
            "consequently ignored during the simulation:%s%s\nAssign them to a parent "
            "node or remove them from the deck.",
            len(reported),
            ", ".join(ROOT_TYPES),
            lines,
            dropped,
        )

    def _scrub_references_to_pruned(self) -> list:
        """
        Remove pruned-node references from list-valued attributes on surviving nodes.

        This is the only shape holding references outside a restricted type's activation
        edges, pinned by the reference-site classification test. A surviving reference
        to a pruned node is by construction non-activating, so nothing load-bearing is
        removed, but left in place it would hand consumers a node that never ran
        initialize().

        Returns
        -------
        (node, instance-attribute name, removed nodes) records for every
        attribute that lost references.
        """

        def is_pruned(element):
            return (
                isinstance(element, Node)
                and (element.type, element.name) in self._pruned_nodes
            )

        records = []

        for node in self._get_all_nodes():
            for attribute_name, attribute in get_attributes(
                node, exclude=REFERENCE_SCAN_EXCLUDE
            ):
                if not isinstance(attribute, list):
                    continue

                kept, removed = [], []
                for element in attribute:
                    (removed if is_pruned(element) else kept).append(element)

                if removed:
                    setattr(node, attribute_name, kept)
                    records.append((node, attribute_name, removed))

        return records

    def _warn_scrubbed_references(self, scrubbed: list) -> None:
        """
        Warn about references to pruned nodes removed from surviving nodes.

        Parameters
        ----------
        scrubbed
            (node, instance-attribute name, removed nodes) records from
            ``_scrub_references_to_pruned``.
        """
        lines = [
            "\n\t- {} {}: {}".format(
                node,
                instance_to_dsl_name(node.type, attribute_name),
                ", ".join(map(str, removed)),
            )
            for node, attribute_name, removed in scrubbed
        ]

        logger.warning(
            "Removed the reference(s) to pruned node(s) from %s "
            "attribute(s):%s\nAssign the removed node(s) to a parent node to keep "
            "them, or drop the stale reference(s) from the deck.",
            len(scrubbed),
            "".join(lines),
        )

    def _drop_event_statements_targeting_pruned(self) -> int:
        """
        Remove queued EVENTS statements that only target pruned nodes.

        Executing such a statement would recreate the node from the default
        library or fail; a target name matching any surviving node keeps the
        statement.

        Returns
        -------
        Number of statements dropped.
        """
        pruned_names_by_type = {}
        for node_type, name in self._pruned_nodes:
            pruned_names_by_type.setdefault(node_type, set()).add(name)

        dropped = 0

        for events in self._event_queue.values():
            for event in events:
                kept = [
                    statement
                    for statement in event.statements
                    if not self._targets_only_pruned(statement, pruned_names_by_type)
                ]
                dropped += len(event.statements) - len(kept)
                event.statements = kept

        return dropped

    def _targets_only_pruned(self, statement, pruned_names_by_type: dict) -> bool:
        """
        Whether a queued statement's target names only pruned nodes.

        Parameters
        ----------
        statement
            A queued EVENTS AST statement.
        pruned_names_by_type
            Pruned node names grouped by node type.
        """
        if not isinstance(statement, NodeDeclaration):
            return False

        pruned_names = pruned_names_by_type.get(statement.node_type, ())

        if not matching_keys(statement.name, pruned_names):
            return False

        return not matching_keys(
            statement.name, getattr(self.nodes, NODE_GROUP[statement.node_type])
        )

    def _execute_commands(self):
        for node in self._get_all_nodes():
            self._execute_node_commands(node)

    def _execute_node_commands(self, node):
        for cmd_ref in node.command_references:
            self._current_deck_line = cmd_ref.deck_line
            self._current_source = cmd_ref.source

            try:
                cmd_ref.execute(node)

            except CommandError as e:
                raise CommandError(self._error_prefix() + f": {e!s}.") from None

            except TypeError as e:
                raise CommandError(self._error_prefix() + f": {e!s}.") from None

            except KeyError as e:
                hint = ""
                key = e.args[0] if e.args else None
                pruned = (
                    matching_keys(key, {name for _, name in self._pruned_nodes})
                    if isinstance(key, str)
                    else []
                )
                if pruned:
                    hint = (
                        " Note: {} removed because unreachable from any top-level node."
                    ).format(", ".join(f"'{name}'" for name in sorted(pruned)))

                raise CommandError(
                    self._error_prefix()
                    + f": '{cmd_ref.command}' attempts to reference non-existing "
                    f"name(s) {e!s}.{hint}"
                ) from None

            except ValueError as e:
                raise CommandError(
                    self._error_prefix() + f": '{cmd_ref.command}' {e!s}"
                ) from None

        node.clear_command_references()

    def _replace_temporary_tables(self):
        start_date = self.general_nodes.model_definition.start_date

        for node in (*self.nodes.forecasts.values(), *self.nodes.timetables.values()):
            try:
                node.replace_reference_table(start_date)
            except ValueError as e:
                raise AttributeAssignmentError(f"{node}: {e!s}") from None

    def _initialize_nodes(self):
        for node in self._get_all_nodes():
            node.initialize()

    def _initialize_dependent_dicts(self):
        for converter in self.nodes.converters.values():
            converter.initialize_dependencies(self.nodes.emissions)

        for fleet in self.nodes.fleets.values():
            fleet.initialize_dependencies()

        for fuel in self.nodes.fuels.values():
            fuel.initialize_dependencies(self.nodes.emissions)

        for levy in self.nodes.levies.values():
            levy.initialize_dependencies(self.nodes.vessels)

        for plant in self.nodes.plants.values():
            plant.initialize_dependencies(
                self.nodes.feedstocks, self.nodes.ports, self.nodes.processes
            )

        for port in self.nodes.ports.values():
            port.initialize_dependencies(self.nodes.emissions, self.nodes.fuels)

        for producer in self.nodes.producers.values():
            producer.initialize_dependencies(
                self.nodes.feedstocks, self.nodes.ports, self.nodes.processes
            )

        for region in self.nodes.regions.values():
            region.initialize_dependencies(
                self.nodes.emissions,
                self.nodes.feedstocks,
                self.nodes.processes,
                self.nodes.sources,
                self.nodes.transports,
            )

        for regulation in self.nodes.regulations.values():
            regulation.initialize_dependencies(self.nodes.vessels)

        for route in self.nodes.routes.values():
            route.initialize_dependencies()

    def _replace_references(self):
        for node in self._get_all_nodes():
            self._replace_references_on_node(node)

    def _replace_references_on_node(self, node):
        for _, attribute in get_attributes(node, exclude=REFERENCE_SCAN_EXCLUDE):
            self._replace_references_on_attribute(node, attribute)

    def _replace_references_on_attribute(self, node, attribute):
        # the container shapes stay in lockstep with
        # _reachability._iter_references, which states how the two walks differ
        if isinstance(attribute, Node):
            entry = self._deferred.get((attribute.type, attribute.name))
            if entry is not None:
                self._pull_deferred(entry)

        elif isinstance(attribute, list):
            for element in attribute:
                self._replace_references_on_attribute(node, element)

        elif isinstance(attribute, dict):
            for element in attribute.values():
                self._replace_references_on_attribute(node, element)

        elif isinstance(attribute, Expression):
            if not attribute.is_initialized():
                attribute.initialize(node)
                attribute.node_references = [
                    self._read_node_reference(reference, attribute.reference_location)
                    for reference in attribute.reference_strings
                ]
                attribute.check_consistency()

            self._replace_references_on_attribute(node, attribute.node_references)

    def _flush_pending_assignments(self):
        """Expand the wildcards of the held-back assignments and apply them."""
        while self._pending_assignments:
            pending = self._pending_assignments
            self._pending_assignments = []

            for entry in pending:
                location = self._error_prefix(entry.source, entry.deck_line)
                value = self._expand_wildcards(entry.value, location)
                self._call_setter(
                    entry.node, entry.attribute, value, entry.source, entry.deck_line
                )

    def _expand_wildcards(self, value, location):
        """
        Replace every wildcard in a materialized value with the nodes it matches.

        Parameters
        ----------
        value
            A materialized assignment value.
        location : str
            Error prefix of the line the value was read at.

        Returns
        -------
        The value with nodes in place of wildcards: a bare wildcard becomes the
        list of its matches, and one inside a list is spliced into that list.
        """
        if isinstance(value, WildcardNodeReference):
            return self._expand_wildcard_node_reference(value, location)

        if not isinstance(value, list):
            return value

        # the recursion mirrors _materialize's, so no wildcard the grammar can
        # nest reaches a setter
        expanded = []
        for element in value:
            if isinstance(element, WildcardNodeReference):
                expanded += self._expand_wildcard_node_reference(element, location)
            else:
                expanded.append(self._expand_wildcards(element, location))

        return expanded

    def _expand_wildcard_node_reference(
        self, wildcard_ref: WildcardNodeReference, location: str
    ) -> list[Node]:
        """
        Expand a wildcard node reference into matching nodes.

        Parameters
        ----------
        wildcard_ref
            Reference containing a glob pattern.
        location
            Error prefix of the line the reference was read at.

        Returns
        -------
        Matched nodes from the registry.
        """
        node_type = wildcard_ref.type
        pattern = wildcard_ref.name
        group = getattr(self.nodes, NODE_GROUP[node_type])

        try:
            matched_names = retrieve_keys(pattern, group)
        except KeyError:
            raise DeckFormatError(
                f"{location}: Wildcard '{pattern}' did not match any {node_type} nodes."
            ) from None

        return [group[name] for name in matched_names]

    def _retrieve_node_from_default(self, node_type, name, location):
        if not self._user_default_directory or not self._installation_default_directory:
            raise DeckKeywordError(
                self._deck_error_prefix()
                + f": User or Installation Default '{name}' is requested but not "
                "specified. Please specify the assumptions location with the -d flag "
                "or environment variable "
            )

        # a default file can pull another default of its own, through an Import
        # or a Copy whose source is not yet registered, and when that inner read
        # returns the outer one still owns the state it set
        reading_default = self._reading_default
        self._reading_default = True
        try:
            found_in = None
            user_default_name = self._user_default_name

            if user_default_name != name:
                self._user_default_name = name
                try:
                    if self._read_default_folder(
                        name, os.path.join(self._user_default_directory, node_type)
                    ):
                        found_in = "User"
                finally:
                    self._user_default_name = user_default_name

            if found_in is None and self._read_default_folder(
                name, os.path.join(self._installation_default_directory, node_type)
            ):
                found_in = "Installation"

            if found_in is None:
                raise DeckKeywordError(
                    f'{location}: {node_type}("{name}") is referenced but not found in'
                    f" either the deck or the default location of {node_type}."
                )

            logger.debug(
                '%s("%s") was retrieved from the %s Default folder.',
                node_type,
                name,
                found_in,
            )

            group = getattr(self.nodes, NODE_GROUP[node_type])
            if name not in group:
                raise DeckKeywordError(
                    f"{location}: A file with name '{name}' was found, but not"
                    f" containing a node with type '{node_type}' and similar name."
                )
        finally:
            self._reading_default = reading_default

    def _read_default_folder(self, name, directory):
        file_names = _get_files_in_directory(directory)

        for file_name in file_names:
            basename = os.path.splitext(file_name)[0]
            if name == basename:
                self._read_include_file(os.path.join(directory, file_name))
                return True

        return False

    # ── node references ───────────────────────────────────────────────

    def _node(self, node_type, name, location):
        """
        Return the node a ``Type("name")`` reference names.

        A declared node is the registry object. An undeclared one is
        constructed here and kept in ``_deferred`` — outside the registry, so
        declaration order, pruning and wildcard matching see declared nodes
        only — until its declaration adopts it or the reference walk pulls it
        from the default library.

        Parameters
        ----------
        node_type : str
            The reference's node type.
        name : str
            The referenced node name.
        location : str
            Error prefix of the referencing line, reported if neither a
            declaration nor a default file provides the node.
        """
        if node_type not in NODE_GROUP:
            raise DeckKeywordError(
                f"{location}: '{node_type}' is not a recognized node type."
            )

        key = (node_type, name)

        if key not in self._provisional:
            node = getattr(self.nodes, NODE_GROUP[node_type]).get(name)
            if node is not None:
                return node

        entry = self._deferred.get(key)
        if entry is None:
            entry = _Deferred(define_new_node(node_type, name), location)
            self._deferred[key] = entry

        return entry.node

    def _adopt(self, node_type, name):
        """
        Return the deferred node a declaration of ``(node_type, name)`` fills.

        ``None`` when no reference preceded the declaration, when a declaration
        adopted it already, or while the name is provisional.
        """
        key = (node_type, name)

        if key in self._provisional:
            return None

        entry = self._deferred.pop(key, None)
        return None if entry is None else entry.node

    def _materialize(self, value):
        """
        Replace every node reference in a parsed value with the node it names.

        Parameters
        ----------
        value
            A parsed assignment value or command argument, read at the current
            source location.

        Returns
        -------
        The value with nodes in place of references.
        """
        if isinstance(value, NodeReference):
            return self._node(value.type, value.name, self._error_prefix())

        if isinstance(value, list):
            return [self._materialize(element) for element in value]

        if isinstance(value, Expression):
            # its references materialize when the walk initializes it, so the
            # location travels with the expression
            value.reference_location = self._error_prefix()

        return value

    def _pull_deferred(self, entry):
        """
        Fill a node no declaration provided from the default library.

        Parameters
        ----------
        entry : _Deferred
            The deferred node and the location of the line that referenced it.
        """
        node = entry.node
        self._retrieve_node_from_default(node.type, node.name, entry.location)
        # the pulled file declares nodes of its own, and may glob over them
        self._flush_pending_assignments()
        self._replace_references_on_node(node)

    def _read_node_reference(self, reference_string, location):
        """
        Return the node an Expression's canonical reference string names.

        Parameters
        ----------
        reference_string : str
            A reference in canonical form, e.g. ``Forecast("name")``.
        location : str
            Error prefix of the expression's line.
        """
        reference = parse_node_reference(reference_string)
        if reference is None:
            raise DeckFormatError(f"{location}: Error in node reference assignment.")

        node_type, name = reference
        if name_contains_wildcards(name):
            raise DeckFormatError(
                f"{location}: Error in node reference: Must not contain wildcards."
            )

        return self._node(node_type, name, location)


def _get_files_in_directory(directory):
    """
    List file names in the top level directory, excluding helper/placeholder files.

    For example, ``.gitkeep``.

    Parameters
    ----------
    directory : str
        Directory of where to look for files.

    Returns
    -------
    list[str] :
        List of file names.
    """
    ignored = frozenset({".gitkeep"})

    return [
        f
        for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f)) and f not in ignored
    ]


def _contains_wildcard(value):
    """Test whether a materialized value is, or holds, a wildcard reference."""
    if isinstance(value, list):
        return any(_contains_wildcard(element) for element in value)

    return isinstance(value, WildcardNodeReference)


def _transplant(node, copied):
    """
    Move a copy's state into the node already held under the copy's name.

    Every attribute is declared in ``__init__``, so the update replaces the
    node's whole state — a placeholder's, or the declaration a pulled file gave
    it. The bounds references imposed on the node are the one thing to keep:
    they are merged back after the update, which brought the source's.

    Parameters
    ----------
    node : Node
        The node earlier references, or the pulled file, put under the name.
    copied : Node
        The freshly copied node, discarded afterwards.

    Returns
    -------
    Node
        The node, now carrying the copy's state.
    """
    bounds = node.internal_bounds if is_calculator(node) else None

    node.__dict__.update(copied.__dict__)

    if bounds is not None:
        node.set_internal_bounds(*bounds)

    return node
