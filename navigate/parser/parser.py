# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import copy
import logging
import os
import re
from pathlib import Path

import numpy as np

from navigate.core import Expression, NodeReference
from navigate.core.enum_ import SimulationSectionID
from navigate.core.general_nodes.bunker_logistics import BunkerLogistics
from navigate.core.general_nodes.bunker_options import BunkerOptions
from navigate.core.node import Node
from navigate.core.node_reference import WildcardNodeReference
from navigate.core.node_registry import GeneralNodes, Nodes
from navigate.exceptions import AttributeAssignmentError, CommandError, DeckFormatError, DeckKeywordError
from navigate.logging_ import log_time_step_breaker, print_preamble
from navigate.parser._attributes import check_general_node_attribute_is_allowed, check_node_attribute_is_allowed
from navigate.parser._commands import (
    CommandReference,
    check_general_node_command_is_allowed,
    check_node_command_is_allowed,
)
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
from navigate.util import (
    attribute_to_setter,
    name_contains_wildcards,
    retrieve_keys,
    timedelta_to_days,
    wildcard_to_regex,
)

logger = logging.getLogger(__name__)

# node attributes that can never hold node references, skipped when the parser
# scans instance attributes to resolve references; every entry must name a real
# attribute (pinned by a unit test) so stale entries cannot accumulate silently
REFERENCE_SCAN_EXCLUDE = ('name', 'type', 'allow_dates_in_table', 'expectation', 'profile',
                          '_table', 'just_copied')


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
        self._user_default_name = None

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
        """Read and process the main .nav deck file.

        Parameters
        ----------
        path
            Full or relative path to the input deck file.
        data_dir
            Assumptions data folder.
        """
        path = Path(path).resolve()

        try:
            with open(path, mode='r', encoding='utf8') as f:
                content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError("Unable to locate {}.".format(path))

        self._deck_path = path
        self.deck_directory = str(path.parent)
        self.deck_name = path.stem
        self._define_internal_directories(data_dir=data_dir)

        print_preamble()

        blocks = parse_deck_content(content, file=str(path))

        for block in blocks:
            self._process_deck_block(block)

        if len(self._finished_sections) < 2:
            raise DeckFormatError("Both a DEFINE and an EVENTS block must be defined in the deck.")

        self._initialize_general_nodes()

        self._current_section = SimulationSectionID.DEFINE
        self._update_dependencies()

        self._replace_start_keyword()
        self._timeline_is_consistent()

        self._current_section = SimulationSectionID.EVENTS
        self._reading_events = True

    @classmethod
    def parse_plot_nodes(cls, path, data_dir=None):
        """Parse Plot nodes from a standalone include (.inc) file.

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
        parser._define_internal_directories(data_dir=data_dir)   # no-op if data_dir is None
        parser._current_section = SimulationSectionID.DEFINE
        parser._read_include_file(str(path))
        for node in parser.nodes.plots.values():
            parser._execute_node_commands(node)                  # runs queued add_plot(...) commands
        return parser.nodes.plots

    def _process_deck_block(self, block):
        """Process a single Define or Events block from the deck AST."""
        if isinstance(block, DefineBlock):
            section = SimulationSectionID.DEFINE
        elif isinstance(block, EventsBlock):
            section = SimulationSectionID.EVENTS
        else:
            raise DeckFormatError("Unknown deck block type: {}".format(type(block).__name__))

        self._begin_reading_section(section)

        for directive in block.directives:
            self._current_deck_line = directive.source.line

            if isinstance(directive, IncludeDirective):
                logger.debug(f"[{self._current_section.name}] Include \"{directive.path}\"")
                self._read_include_file(directive.path)

            elif isinstance(directive, LoadModuleDirective):
                logger.debug(f"[{self._current_section.name}] Load {directive.name}")
                self._load_module(directive)

        self._end_reading_section()

    def progress_timeline(self):
        """Progress the timeline to the next date and process events.

        Returns
        -------
        np.datetime64
            Date of the next event in the timeline.
        """
        self._reading_events = True

        date, events = self._next_event()

        if (self._idx_date > 1) and (date is not None):
            log_time_step_breaker(logger, self._idx_date - 1, date,
                                  timedelta_to_days(date - self.dates[0]))

        self._current_date = date

        for event in events:
            self._read_event(event)

        self._update_dependencies()

        return date

    # ── error formatting ──────────────────────────────────────────────

    def _error_prefix(self, source: SourceLocation = None, deck_line: int = None):
        """Build an error prefix string from source location.

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
            parts.append("Error in deck file, line {}".format(dl))
        if source.file:
            parts.append("include file '{}', line {}".format(source.file, source.line))
        return ', '.join(parts) if parts else "Parser error"

    def _deck_error_prefix(self):
        return "Error in deck file, line {}".format(self._current_deck_line)

    # ── internal directories ──────────────────────────────────────────

    def _define_internal_directories(self, data_dir: Path | None = None) -> None:
        self._exe_directory = os.path.dirname(os.path.abspath(__file__))
        if data_dir:
            data_dir = Path(data_dir).resolve()
            self._user_default_directory = str(data_dir / 'defaults/user')
            self._user_module_directory = str(data_dir / 'modules/user')
            self._installation_default_directory = str(data_dir / 'defaults/installation')
            self._installation_module_directory = str(data_dir / 'modules/installation')

    # ══════════════════════════════════════════════════════════════════
    # Include / Import
    # ══════════════════════════════════════════════════════════════════

    def _read_include_file(self, path):
        """Read, parse, and process an include file.

        Parameters
        ----------
        path : str
            Path of include file (relative to deck directory).
        """
        if not os.path.isabs(path):
            path = os.path.join(self.deck_directory or '', path)

        try:
            with open(path, mode='r', encoding='utf8') as f:
                content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(self._deck_error_prefix()
                                    + ": Include file '{}' not found.".format(path))

        abs_path = os.path.abspath(path) if not os.path.isabs(path) else path

        statements = parse_include_content(content, file=abs_path)

        self._process_statements(statements)

    def _load_module(self, directive):
        """Load a module referenced in the deck file.

        Parameters
        ----------
        directive : LoadModuleDirective
            The parsed Load directive.
        """
        if not self._user_module_directory or not self._installation_module_directory:
            raise DeckFormatError(self._deck_error_prefix()
                                  + f": Module '{directive.name}' is requested but no assumptions "
                                  "directory is specified. Use the -d flag or ASSUMPTIONS_DATA_DIR.")

        file_name = attribute_to_setter(directive.name, method='')[1:]

        found = self._read_default_folder(file_name, self._user_module_directory)
        if found:
            logger.debug("Module '{}' was retrieved from the User Module folder.".format(directive.name))
            return

        found = self._read_default_folder(file_name, self._installation_module_directory)
        if found:
            logger.debug("Module '{}' was retrieved from the Installation Module folder.".format(directive.name))
        else:
            raise DeckKeywordError("No module with name '{}' was found.".format(directive.name))

    # ══════════════════════════════════════════════════════════════════
    # AST statement processing
    # ══════════════════════════════════════════════════════════════════

    def _process_statements(self, statements):
        """Walk a list of AST statements from a parsed .inc file."""
        for statement in statements:
            self._current_source = getattr(statement, 'source', self._current_source)

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

    _EVENT_DISPATCH = {
        GeneralNodeDeclaration: '_process_general_node_declaration',
        NodeDeclaration: '_process_node_declaration',
        ImportStatement: '_process_import_node',
        CopyStatement: '_process_copy_node',
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
            self._current_source = getattr(statement, 'source', self._current_source)
            self._process_event_statement(statement)

        self._current_event = None
        self._reading_events = False

    def _begin_reading_section(self, section):
        self._check_section(section)
        self._current_section = section
        logger.debug(f"Reading section {self._current_section.name}")

    def _check_section(self, section):
        if self._current_section is not None:
            raise DeckFormatError(self._deck_error_prefix() + ": Unable to begin {} while reading {}."
                                  .format(SECTION_NAME[section], SECTION_NAME[self._current_section]))

        if section in self._finished_sections:
            raise DeckFormatError(self._deck_error_prefix()
                                  + ": Each section can only be defined once and must be read in the order {}."
                                  .format(', '.join(SECTION_NAME.values())))

        if section == SimulationSectionID.DEFINE and SimulationSectionID.EVENTS in self._finished_sections:
            raise DeckFormatError(self._deck_error_prefix()
                                  + ": Each section can only be defined once and must be read in the order {}."
                                  .format(', '.join(SECTION_NAME.values())))

    def _end_reading_section(self):
        if self._current_section is not None:
            self._finished_sections.append(self._current_section)
            self._current_section = None
            self._reading_events = False
            self._place_in_queue = False
        else:
            raise DeckFormatError(self._deck_error_prefix() + ": Unable to end section, no section is defined.")

    def _check_timeline_change(self):
        if self._reading_default:
            raise DeckFormatError("Error while retrieving default, include file '{}', line {}"
                                  .format(self._current_source.file, self._current_source.line)
                                  + ": Unable to alter timeline while retrieving default nodes.")

    def _start_timeline(self):
        self._check_keyword(START)
        self._check_timeline_change()

        if self._current_date is not None:
            raise DeckFormatError(self._error_prefix()
                                  + ": Unable to start a new timeline while one is in progress.")

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

        date = string_to_date(statement.date_string,
                              msg="Error in date definition: Must be in format dd-mm-yyyy or dd/mm/yyyy.")
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
        if (self._current_date is not None) and (not isinstance(self._current_date, str)):
            if date <= self._current_date:
                raise DeckFormatError(self._error_prefix()
                                      + ": Dates must be ordered chronologically within individual include files.")

    def _replace_start_keyword(self):
        start_date = self.general_nodes.model_definition.start_date

        self.dates = np.array([start_date if d == START else d for d in self.dates], dtype='datetime64[D]')
        self.dates = np.unique(self.dates)

        if START in self._event_queue:
            if start_date not in self._event_queue:
                start_events = []
            else:
                start_events = self._event_queue.pop(start_date)

            self._event_queue[start_date] = [*self._event_queue.pop(START), *start_events]

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
                    msg += "\t- NAV file, line {}, include file '{}', line {}: Date '{}' is before start date '{}'\n"\
                        .format(event.deck_line,
                                event.source.file,
                                event.source.line,
                                date,
                                start_date)

        if msg:
            msg = "Inconsistent timeline detected:\n{}All defined dates must be later than the start date.".format(msg)
            raise DeckFormatError(msg)

    # ══════════════════════════════════════════════════════════════════
    # Node body processing — shared helpers
    # ══════════════════════════════════════════════════════════════════

    def _apply_assignment(self, nodes, item, node_type, is_general=False):
        """Validate and apply an Assignment AST node to one or more nodes.

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

        try:
            attribute = item.attribute
            value = item.value
            if is_general:
                check_general_node_attribute_is_allowed(node_type, attribute, self._current_section)
            else:
                check_node_attribute_is_allowed(node_type, attribute, self._current_section)
            self._assign_node_reference_location(value)

        except DeckFormatError:
            raise DeckFormatError(self._error_prefix()
                                  + ": '{}' is not a valid assignment.".format(item.attribute))

        except AttributeAssignmentError as e:
            raise AttributeAssignmentError(self._error_prefix() + ": {}.".format(str(e)))

        target_nodes = nodes if isinstance(nodes, list) else [nodes]
        for node in target_nodes:
            try:
                getattr(node, attribute_to_setter(attribute))(value)

            except ValueError as e:
                raise ValueError(self._error_prefix() + ": {} attribute '{}' {}."
                                 .format(node, attribute, e))

    def _queue_command(self, nodes, item, node_type, is_general=False):
        """Validate and queue a Command AST node on one or more nodes.

        Parameters
        ----------
        nodes : list[Node] or single node
            Target node(s).
        item : Command
            The command AST node.
        node_type : str
            Node type string for validation.
        is_general : bool
            Whether this is a general node.
        """
        self._current_source = item.source

        try:
            command = item.name
            inputs = item.args
            if is_general:
                check_general_node_command_is_allowed(node_type, command, self._current_section)
            else:
                check_node_command_is_allowed(node_type, command, self._current_section)
            self._assign_node_reference_location(inputs)

        except CommandError as e:
            raise CommandError(self._error_prefix() + ": {}.".format(str(e)))

        ref = CommandReference(command, inputs,
                               source=item.source,
                               deck_line=self._current_deck_line)

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
                raise DeckKeywordError(self._error_prefix(item.source)
                                       + ": '{}' is not a valid keyword.".format(type(item).__name__))

        for node in nodes:
            self._set_node(declaration.node_type, node)

    def _process_general_node_declaration(self, declaration):
        """Process a GeneralNodeDeclaration AST node."""
        self._check_keyword(declaration.node_type)
        general_node = self._retrieve_general_node(declaration.node_type)

        for item in declaration.body:
            item_type = type(item)
            if item_type is Command:
                self._queue_command(general_node, item, declaration.node_type, is_general=True)
            elif item_type is Assignment:
                self._apply_assignment(general_node, item, declaration.node_type, is_general=True)
            else:
                raise DeckKeywordError(self._error_prefix(item.source)
                                       + ": '{}' is not a valid keyword.".format(type(item).__name__))

        setattr(self.general_nodes, GENERAL_NODE_GROUP[declaration.node_type], general_node)

    def _process_copy_node(self, statement):
        """Process a CopyStatement AST node."""
        self._check_allow_new_node('copy')
        self._check_keyword(statement.node_type)

        if not NODE_ALLOW_COPY[statement.node_type]:
            raise ValueError(self._error_prefix()
                             + ": Unable to copy nodes of type '{}'.".format(statement.node_type))

        self._check_node_name_is_available(statement.node_type, statement.copy_to)

        group = getattr(self.nodes, NODE_GROUP[statement.node_type])

        from_default = False
        if statement.copy_from not in group:
            self._retrieve_node_from_default(statement.copy_from, statement.node_type,
                                             reference_location=self._error_prefix())
            from_default = True

        copy_node = group[statement.copy_from]
        new_node = copy.deepcopy(copy_node)
        new_node.name = statement.copy_to
        new_node.just_copied = True

        if from_default:
            del group[statement.copy_from]

        group[statement.copy_to] = new_node

    def _process_import_node(self, statement):
        """Process an ImportStatement AST node."""
        self._check_allow_new_node('import')
        self._check_keyword(statement.node_type)

        if name_contains_wildcards(statement.name):
            self._read_import_node_wildcard(statement.node_type, statement.name)
        else:
            self._check_node_name_is_available(statement.node_type, statement.name)
            self._retrieve_node_from_default(statement.name, statement.node_type, reference_location=self._error_prefix())

    # ══════════════════════════════════════════════════════════════════
    # Node retrieval / creation
    # ══════════════════════════════════════════════════════════════════

    def _retrieve_nodes(self, node_type, name):
        group = getattr(self.nodes, NODE_GROUP[node_type])

        if name_contains_wildcards(name):
            regex = wildcard_to_regex(name)
            nodes = [node for key, node in group.items() if re.match(regex, key)]
            if not nodes:
                raise DeckKeywordError("{}: No node of type '{}' matches the wildcard expression '{}'."
                                       .format(self._error_prefix(), node_type, name))
            return nodes

        if name in group:
            return [group[name]]

        self._check_allow_new_node('define')
        self._check_node_name_is_available(node_type, name)
        return [define_new_node(node_type, name)]

    def _retrieve_general_node(self, type_: str):
        field = GENERAL_NODE_GROUP[type_]
        general_node = getattr(self.general_nodes, field)
        if general_node is None:
            general_node = define_new_general_node(type_)
            setattr(self.general_nodes, field, general_node)
        return general_node

    def _check_allow_new_node(self, action):
        if self._current_section != SimulationSectionID.DEFINE:
            raise DeckKeywordError(self._error_prefix()
                                   + ": Unable to {} new nodes outside DEFINE.".format(action))

    def _set_node(self, node_type, node):
        getattr(self.nodes, NODE_GROUP[node_type])[node.name] = node

    def _check_keyword(self, keyword, name=None):
        if keyword in KEYWORD_SECTIONS:
            if self._current_section not in KEYWORD_SECTIONS[keyword]:
                if self._reading_default:
                    raise DeckKeywordError("Unable to reference {}(\"{}\") as it is not previously defined."
                                           .format(keyword, name))
                else:
                    raise DeckKeywordError(self._error_prefix()
                                           + ": '{}' is not an allowed keyword in section {}."
                                           .format(keyword, SECTION_NAME[self._current_section]))
        else:
            raise DeckKeywordError(self._error_prefix()
                                   + ": \n'{}' is not a recognized keyword. "
                                     "Check the attributes and commands for spelling".format(keyword))

    def _check_node_name_is_available(self, node_type, name):
        if name in self._get_all_node_names():
            raise ValueError(self._error_prefix()
                             + ": Unable to add {}(\"{}\"), the name is already in use by a different node."
                             .format(node_type, name))

    def _read_import_node_wildcard(self, node_type, name_pattern):
        if not self._user_default_directory or not self._installation_default_directory:
            raise DeckKeywordError(self._deck_error_prefix()
                                   + ": Wildcard Import is requested but default directories are not specified. "
                                   "Please specify the assumptions location with the -d flag or environment variable ")

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
            raise DeckKeywordError("{}: No {} defaults matching '{}' found in user or installation folders."
                                   .format(self._error_prefix(), node_type, name_pattern))

        for name in sorted(matched_names):
            self._check_node_name_is_available(node_type, name)
            self._retrieve_node_from_default(name, node_type, reference_location=self._error_prefix())

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
            msg = "".join("\t- No {} are defined.\n".format(m) if m != "timeline"
                          else "\t- No timeline is defined.\n" for m in missing)
            raise DeckKeywordError("Unable to run a simulation:\n{}".format(msg))

    def _get_all_nodes(self):
        return list(self.nodes.all_nodes())

    def _get_all_general_nodes(self):
        return [self.general_nodes.bunker_logistics,
                self.general_nodes.bunker_options,
                self.general_nodes.model_definition]

    def _get_all_node_names(self):
        return list(self.nodes.all_names())

    # ══════════════════════════════════════════════════════════════════
    # Semantic passes
    # ══════════════════════════════════════════════════════════════════

    def _initialize_general_nodes(self):
        if self.general_nodes.model_definition is None:
            raise DeckFormatError("Error in simulation: 'ModelDefinition' must be defined.")

        self.general_nodes.model_definition.initialize()

        if self.general_nodes.bunker_options is None:
            self.general_nodes.bunker_options = BunkerOptions()

        self.general_nodes.bunker_options.initialize()

        if self.general_nodes.bunker_logistics is None:
            self.general_nodes.bunker_logistics = BunkerLogistics()

    def _update_dependencies(self):
        """Replace references, execute commands, initialize nodes.

        The sequence is: replace refs → replace tables → init dicts →
        execute commands → replace refs again (commands may create new
        ones) → replace tables again → initialize nodes.
        """
        self._reading_events = True

        self._replace_references()
        self._replace_temporary_tables()

        self._initialize_dependent_dicts()
        self._execute_commands()

        self._replace_references()
        self._replace_temporary_tables()

        self._initialize_nodes()

        for node in self._get_all_nodes():
            node.just_copied = False

        self._reading_events = False

    def _execute_commands(self):
        all_nodes = [*self._get_all_nodes(), *self._get_all_general_nodes()]
        for node in all_nodes:
            self._execute_node_commands(node)

    def _execute_node_commands(self, node):
        for cmd_ref in node.command_references:
            self._current_deck_line = cmd_ref.deck_line
            self._current_source = cmd_ref.source

            try:
                cmd_ref.execute(node)

            except CommandError as e:
                raise CommandError(self._error_prefix() + ": {}.".format(str(e)))

            except TypeError as e:
                raise CommandError(self._error_prefix() + ": {}.".format(str(e)))

            except KeyError as e:
                raise CommandError(self._error_prefix()
                                   + ": '{}' attempts to reference non-existing name(s) {}."
                                   .format(cmd_ref.command, str(e)))

            except ValueError as e:
                raise ValueError(self._error_prefix() + ": '{}' {}"
                                 .format(cmd_ref.command, str(e)))

        node.clear_command_references()

    def _replace_temporary_tables(self):
        start_date = self.general_nodes.model_definition.start_date

        for node in (*self.nodes.forecasts.values(), *self.nodes.timetables.values()):
            try:
                node.replace_reference_table(start_date)
            except ValueError as e:
                raise ValueError("{}: {}".format(node, str(e)))

    def _initialize_nodes(self):
        self.general_nodes.bunker_logistics.initialize()

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
            plant.initialize_dependencies(self.nodes.feedstocks, self.nodes.processes)

        for port in self.nodes.ports.values():
            port.initialize_dependencies(self.nodes.emissions, self.nodes.fuels)

        for producer in self.nodes.producers.values():
            producer.initialize_dependencies(self.nodes.feedstocks, self.nodes.ports, self.nodes.processes,
                                             self.nodes.routes)

        for region in self.nodes.regions.values():
            region.initialize_dependencies(self.nodes.emissions,
                                           self.nodes.feedstocks,
                                           self.nodes.processes,
                                           self.nodes.sources,
                                           self.nodes.transports)

        for regulation in self.nodes.regulations.values():
            regulation.initialize_dependencies(self.nodes.vessels)

        for route in self.nodes.routes.values():
            route.initialize_dependencies()

        self.general_nodes.bunker_logistics.initialize_dependencies(self.nodes.emissions,
                                                                    self.nodes.fuels,
                                                                    self.nodes.ports,
                                                                    self.nodes.regions)

    def _replace_references(self):
        for node in self._get_all_nodes():
            self._replace_references_on_node(node)

        for general_node in self._get_all_general_nodes():
            self._replace_references_on_node(general_node)

    def _replace_references_on_node(self, node):
        attributes = _get_attributes(node, exclude=REFERENCE_SCAN_EXCLUDE)

        for attribute_name, attribute in attributes:
            self._replace_references_on_attribute(node, attribute, attribute_name=attribute_name)

    def _replace_references_on_attribute(self, node, attribute, attribute_name=None, container=None, index_or_key=None):

        if isinstance(attribute, WildcardNodeReference):

            if not isinstance(container, list):
                raise DeckFormatError("Wildcard node references may only appear inside lists: {}"
                                      .format(attribute))

            matched = self._expand_wildcard_node_reference(attribute)
            # splice matched nodes into the list, replacing the wildcard entry
            container[index_or_key:index_or_key + 1] = matched
            return

        elif isinstance(attribute, NodeReference):
            actual_node, default = self._get_node_from_reference(attribute)

        elif isinstance(attribute, Node) and isinstance(node, Node) and node.just_copied:
            actual_node = getattr(self.nodes, NODE_GROUP[attribute.type])[attribute.name]
            default = False
            del attribute

        elif isinstance(attribute, list):
            # iterate by index because wildcard expansion can grow the list
            i = 0
            while i < len(attribute):
                element = attribute[i]
                old_len = len(attribute)
                self._replace_references_on_attribute(node, element, container=attribute, index_or_key=i)
                # if the list grew (wildcard splice), advance past the inserted items
                i += 1 + (len(attribute) - old_len)
            return

        elif isinstance(attribute, dict):
            for key, element in attribute.items():
                self._replace_references_on_attribute(node, element, container=attribute, index_or_key=key)
            return

        elif isinstance(attribute, Expression):
            if not attribute.is_initialized():
                attribute.initialize(node)
                reference_strings = attribute.node_references
                attribute.node_references = [self._read_node_reference(ref) for ref in reference_strings]
                self._assign_node_reference_location(attribute.node_references,
                                                     location=attribute.reference_location)
                attribute.check_consistency()

            self._replace_references_on_attribute(node, attribute.node_references)
            return

        else:
            return

        if attribute_name is not None:
            setattr(node, attribute_name, actual_node)
        elif index_or_key is not None:
            container[index_or_key] = actual_node

        if default:
            self._replace_references_on_node(actual_node)

    def _get_node_from_reference(self, reference):
        name = reference.name
        node_type = reference.type

        group = getattr(self.nodes, NODE_GROUP[node_type])

        if name in group:
            node = group[name]
            default = False
        else:
            self._retrieve_node_from_default(name, node_type, reference_location=reference.reference_location)
            node = group[name]
            default = True

        if node.is_calculator():
            node.transfer_internal_bounds(reference)

        return node, default

    def _expand_wildcard_node_reference(self, wildcard_ref: WildcardNodeReference) -> list[Node]:
        """Expand a wildcard node reference into matching nodes.

        Parameters
        ----------
        wildcard_ref
            Reference containing a glob pattern.

        Returns
        -------
        Matched nodes from the registry.
        """

        node_type = wildcard_ref.type
        pattern = wildcard_ref.pattern
        group = getattr(self.nodes, NODE_GROUP[node_type])

        try:
            matched_names = retrieve_keys(pattern, group)
        except KeyError:
            raise DeckFormatError("Wildcard '{}' did not match any {} nodes.".format(pattern, node_type))

        return [group[name] for name in matched_names]

    def _retrieve_node_from_default(self, name, node_type, reference_location=''):
        if not self._user_default_directory or not self._installation_default_directory:
            raise DeckKeywordError(self._deck_error_prefix()
                                   + f": User or Installation Default '{name}' is requested but not specified. "
                                   "Please specify the assumptions location with the -d flag or environment variable ")

        self._reading_default = True
        try:
            found = False
            _user_default_name = self._user_default_name

            if _user_default_name != name:
                self._user_default_name = name
                found = self._read_default_folder(name, os.path.join(self._user_default_directory, node_type))
                self._user_default_name = None

            if found:
                logger.debug("{}(\"{}\") was retrieved from the User Default folder.".format(node_type, name))
                return

            found = self._read_default_folder(name, os.path.join(self._installation_default_directory, node_type))

            if found:
                logger.debug("{}(\"{}\") was retrieved from the Installation Default folder.".format(node_type, name))
            else:
                raise DeckKeywordError("{0}: {1}(\"{2}\") is referenced but not found in"
                                       " either the deck or the default location of {1}."
                                       .format(reference_location, node_type, name))

            group = getattr(self.nodes, NODE_GROUP[node_type])
            if name not in group:
                raise DeckKeywordError("Error in import: A file with name '{}' was found, but not containing"
                                       " a node with type '{}' and similar name.".format(name, node_type))
        finally:
            self._reading_default = False

    def _read_default_folder(self, name, directory):
        file_names = _get_files_in_directory(directory)

        for file_name in file_names:
            basename = os.path.splitext(file_name)[0]
            if name == basename:
                self._read_include_file(os.path.join(directory, file_name))
                return True

        return False

    # ── reference location helpers ────────────────────────────────────

    @staticmethod
    def _read_node_reference(assignment_str):
        """Parse a node reference string like ``Vessel("name")``.

        Parameters
        ----------
        assignment_str : str
            Raw reference string from an Expression.

        Returns
        -------
        NodeReference
        """
        match = re.match(r'^\s*(([A-Z][a-z]+)+)\(\s*"([^"]+)"\s*\)\s*$', assignment_str)
        if match:
            node_type = match.group(1)
            name = match.group(3)
            if name_contains_wildcards(name):
                raise DeckFormatError("Error in node reference: Must not contain wildcards.")
            return NodeReference(node_type, name)
        else:
            raise DeckFormatError("Error in node reference assignment.")

    @staticmethod
    def _assign_node_reference_location(value, location=None):
        """Tag NodeReferences in *value* with a source location string.

        Parameters
        ----------
        value : NodeReference | list | Expression | Any
            The parsed value that may contain node references.
        location : str, optional
            Override location string.  When ``None`` the caller's
            ``_error_prefix()`` is used (not available here as static).
        """
        if isinstance(value, (NodeReference, WildcardNodeReference)):
            if location is not None:
                value.reference_location = location
        elif isinstance(value, list):
            for element in value:
                Parser._assign_node_reference_location(element, location)
        elif isinstance(value, Expression):
            if location is not None:
                value.reference_location = location


def _get_attributes(class_, exclude=()):
    """
    Extracts all attributes from the supplied class except built-in attributes and attributes listed in 'exclude'.

    Parameters
    ----------
    class_ : class
        Class from which to extract attributes.
    exclude : tuple[str]
        Tuple of strings with attributes to exclude from the list.

    Returns
    -------
    generator :
        Generator of (name, attribute) pairs.
    """

    attributes = list(class_.__dict__.items())
    return ((name, attribute) for name, attribute in attributes
            if not (name.startswith('__') and name.endswith('__')) and name not in exclude)


def _get_files_in_directory(directory):
    """
    Extract a list of all file names in the top level directory, excluding known
    helper/placeholder files (e.g. ``.gitkeep``).

    Parameters
    ----------
    directory : str
        Directory of where to look for files.

    Returns
    -------
    list[str] :
        List of file names.
    """

    ignored = frozenset({'.gitkeep'})

    return [
        f for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f)) and f not in ignored
    ]
