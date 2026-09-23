# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Readers for the hand-written reference manual under docs/reference_manual.

Used by tests/attribute to hold the manual's DSL surface against the parser
registries and its report-property appendix against the profile getters; nothing
generates the manual, so the readers parse its markdown.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, NamedTuple

from helpers.report_properties import PROFILE_CLASSES
from helpers.simulation import REPO_ROOT
from navigate.util import attribute_to_instance_name

if TYPE_CHECKING:
    from pathlib import Path

MANUAL_DIR = REPO_ROOT / "docs" / "reference_manual"

# pages describing no node, so no node type may ever resolve to one
NON_NODE_PAGES = frozenset(
    {"index.md", "overview.md", "dsl_reference.md", "appendix_ids.md"}
)

REPORT_PAGE = MANUAL_DIR / "report.md"

_DSL_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*")

# the appendix tables carry no heading, so the lead-in sentence is the anchor
_TABLE_ANCHOR = "The properties are applicable for the following commands:"
_TABLE_HEADER = ("**Property name**", "**Unit**", "**Description**")
_COMMAND_BULLET = re.compile(r"\* `(\w+)`")

# the dash counts differ from table to table and one middle cell is empty, which
# a zero-or-more dash run accepts while nothing else on the page passes
_SEPARATOR_CELL = re.compile(r":?-*:?")
_PROPERTY_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9]*")


def _fence_mask(lines: list[str]) -> list[bool]:
    """
    Mark the lines a fenced code block covers, its delimiters included.

    The manual's examples are DSL snippets, where a line may open with the
    comment character or carry a table pipe, so a reader that walks the markdown
    has to skip them.

    Parameters
    ----------
    lines : list[str]
        The lines of a manual page, in order.

    Returns
    -------
    list[bool] :
        One flag per line, True where the line is fenced.
    """
    mask = []
    in_fence = False

    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            mask.append(True)
        else:
            mask.append(in_fence)

    return mask


def page_for(node_type: str) -> Path:
    """
    Locate the manual page of a node type.

    Parameters
    ----------
    node_type : str
        A node-type name as navigate.core.node_type spells it, e.g. ``PowerSystem``.

    Returns
    -------
    Path :
        The page, e.g. ``docs/reference_manual/power_system.md``. The page is not
        read, so a node type without one resolves to a path that does not exist.
    """
    return MANUAL_DIR / f"{attribute_to_instance_name(node_type)}.md"


def normalise_heading(heading: str) -> str | None:
    """
    Reduce a level-three heading to the DSL name it documents.

    Command headings escape every underscore, many attribute headings carry a
    trailing space, and three headings on power_system.md end in an escaped
    asterisk footnote marker. A heading that is prose survives none of it.

    Parameters
    ----------
    heading : str
        The heading text, without its leading hashes.

    Returns
    -------
    str | None :
        The DSL name, or None when the heading names nothing a registry could
        hold.
    """
    name = heading.replace("\\", "").strip().removesuffix("*").strip()

    return name if _DSL_NAME.fullmatch(name) else None


def section_headings(node_type: str, section: str) -> set[str]:
    """
    Collect the DSL names a node page documents under one of its sections.

    A page that carries no such section contributes nothing, which is how the
    manual spells a node type whose registry is empty. Fenced code blocks are
    skipped: the manual's examples are DSL snippets, where a line may open with
    the comment character.

    Parameters
    ----------
    node_type : str
        A node-type name, e.g. ``Port``.
    section : str
        A level-two section title, ``Attributes`` or ``Commands``.

    Returns
    -------
    set[str] :
        The normalised level-three headings inside that section.

    Raises
    ------
    ValueError
        If the page opens the section more than once, or documents one name
        twice inside it. Either would otherwise vanish into the set.
    """
    page = page_for(node_type)
    headings: set[str] = set()
    current_section = None
    section_seen = False

    lines = page.read_text().splitlines()

    for line, fenced in zip(lines, _fence_mask(lines), strict=True):
        if fenced:
            continue

        if line.startswith("## "):
            current_section = line[3:].strip()

            if current_section == section:
                if section_seen:
                    raise ValueError(
                        f"{page.name} opens '## {section}' more than once, so its"
                        " headings read as one section"
                    )

                section_seen = True

        elif line.startswith("### ") and current_section == section:
            name = normalise_heading(line[4:])

            if name is None:
                continue

            if name in headings:
                raise ValueError(
                    f"{page.name} documents '{name}' twice under '## {section}'"
                )

            headings.add(name)

    return headings


class ReportPropertyRow(NamedTuple):
    """One data row of a report-property table in the report.md appendix."""

    line: int
    token: str


class ReportPropertyTable(NamedTuple):
    """One report-property table, with the report commands it is listed under."""

    commands: tuple[str, ...]
    rows: tuple[ReportPropertyRow, ...]


def _skip_blank(lines: list[str], index: int) -> int:
    """
    Advance past the blank lines starting at an index.

    Parameters
    ----------
    lines : list[str]
        The lines of the page, in order.
    index : int
        The index to start from.

    Returns
    -------
    int :
        The index of the first non-blank line, or the end of the page.
    """
    while index < len(lines) and not lines[index].strip():
        index += 1

    return index


def _cells(line: str) -> list[str]:
    """
    Split a markdown table row into its stripped cells.

    Parameters
    ----------
    line : str
        A line opening with a table pipe.

    Returns
    -------
    list[str] :
        The cells between the outer pipes.
    """
    return [cell.strip() for cell in line.split("|")[1:-1]]


def _read_commands(lines: list[str], index: int) -> tuple[tuple[str, ...], int]:
    """
    Read the report-command bullets a table is introduced by.

    Parameters
    ----------
    lines : list[str]
        The lines of report.md, in order.
    index : int
        The index of the line after the lead-in sentence.

    Returns
    -------
    tuple[tuple[str, ...], int] :
        The commands, and the index of the first line past the bullets.

    Raises
    ------
    ValueError
        If the lead-in introduces no bullet, or names something that is not a
        report command.
    """
    index = _skip_blank(lines, index)
    commands = []

    while index < len(lines):
        bullet = _COMMAND_BULLET.fullmatch(lines[index].strip())

        if bullet is None:
            break

        commands.append(bullet.group(1))
        index += 1

    if not commands:
        raise ValueError(
            f"{REPORT_PAGE.name} line {index + 1}: the lead-in sentence introduces no"
            " report-command bullet"
        )

    unregistered = [command for command in commands if command not in PROFILE_CLASSES]

    if unregistered:
        raise ValueError(
            f"{REPORT_PAGE.name} line {index}: {unregistered} is not a report command"
        )

    return tuple(commands), index


def _read_rows(
    lines: list[str], index: int
) -> tuple[tuple[ReportPropertyRow, ...], int]:
    """
    Read the table following the command bullets.

    The header is matched in full so that an inserted column kills the parse
    rather than silently shifting every cell index.

    Parameters
    ----------
    lines : list[str]
        The lines of report.md, in order.
    index : int
        The index of the first line past the command bullets.

    Returns
    -------
    tuple[tuple[ReportPropertyRow, ...], int] :
        The data rows, and the index of the first line past the table.

    Raises
    ------
    ValueError
        If the header, the separator or any data row is not the shape the reader
        takes the column meaning from.
    """
    index = _skip_blank(lines, index)

    if index >= len(lines):
        raise ValueError(
            f"{REPORT_PAGE.name}: a lead-in sentence is followed by no table"
        )

    header = tuple(_cells(lines[index]))

    if header != _TABLE_HEADER:
        raise ValueError(
            f"{REPORT_PAGE.name} line {index + 1}: the header is {list(header)}, not"
            f" {list(_TABLE_HEADER)}, so the columns no longer mean what the reader"
            " takes them to mean"
        )

    index += 1
    separator = _cells(lines[index])

    if len(separator) != len(_TABLE_HEADER) or not all(
        _SEPARATOR_CELL.fullmatch(cell) for cell in separator
    ):
        raise ValueError(
            f"{REPORT_PAGE.name} line {index + 1}: {separator} is not a table separator"
        )

    index += 1
    rows = []

    while index < len(lines) and lines[index].startswith("|"):
        cells = _cells(lines[index])

        if len(cells) != len(_TABLE_HEADER):
            raise ValueError(
                f"{REPORT_PAGE.name} line {index + 1}: the row has {len(cells)} cells,"
                f" not {len(_TABLE_HEADER)}"
            )

        if not _PROPERTY_TOKEN.fullmatch(cells[0]):
            raise ValueError(
                f"{REPORT_PAGE.name} line {index + 1}: '{cells[0]}' is not a property"
                " token"
            )

        rows.append(ReportPropertyRow(index + 1, cells[0]))
        index += 1

    if not rows:
        raise ValueError(f"{REPORT_PAGE.name} line {index + 1}: the table has no row")

    return tuple(rows), index


def report_property_tables() -> list[ReportPropertyTable]:
    """
    Read the property tables of the report.md appendix.

    The appendix carries no headings, so each table is found from the lead-in
    sentence naming the commands it applies to. A partial parse is worse than no
    parse - it reads as a clean page - so the reader ends by accounting for every
    table pipe on the page and for every report command.

    Returns
    -------
    list[ReportPropertyTable] :
        The tables, in page order.

    Raises
    ------
    ValueError
        If a lead-in produced no table, if a table pipe outside a fenced code
        block belongs to no parsed table, or if the tables do not between them
        cover every report command.
    """
    lines = REPORT_PAGE.read_text().splitlines()
    fenced = _fence_mask(lines)

    anchors = sum(
        1
        for line, in_fence in zip(lines, fenced, strict=True)
        if not in_fence and line.strip() == _TABLE_ANCHOR
    )

    tables = []
    index = 0

    while index < len(lines):
        if fenced[index] or lines[index].strip() != _TABLE_ANCHOR:
            index += 1
            continue

        commands, index = _read_commands(lines, index + 1)
        rows, index = _read_rows(lines, index)
        tables.append(ReportPropertyTable(commands, rows))

    if len(tables) != anchors:
        raise ValueError(
            f"{REPORT_PAGE.name}: {anchors} lead-in sentences produced"
            f" {len(tables)} tables"
        )

    # a header and a separator accompany the data rows of every parsed table
    parsed_pipes = sum(len(table.rows) + 2 for table in tables)
    page_pipes = sum(
        1
        for line, in_fence in zip(lines, fenced, strict=True)
        if not in_fence and line.startswith("|")
    )

    if parsed_pipes != page_pipes:
        raise ValueError(
            f"{REPORT_PAGE.name}: the parsed tables account for {parsed_pipes} of the"
            f" {page_pipes} table lines on the page, so a table is introduced by"
            " something other than the lead-in sentence the reader looks for"
        )

    covered = {command for table in tables for command in table.commands}

    if covered != set(PROFILE_CLASSES):
        raise ValueError(
            f"{REPORT_PAGE.name}: no table lists"
            f" {sorted(set(PROFILE_CLASSES) - covered)}"
        )

    return tables
