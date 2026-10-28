# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Readers for the hand-written reference manual under docs/reference_manual.

Used by tests/unit/docs to hold the manual's DSL surface against the parser
registries and its results file page against the results classes; nothing
generates the manual, so the readers parse its markdown.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from helpers.simulation import REPO_ROOT
from navigate.util import attribute_to_instance_name

if TYPE_CHECKING:
    from pathlib import Path

MANUAL_DIR = REPO_ROOT / "docs" / "reference_manual"

# pages describing no node, so no node type may ever resolve to one
NON_NODE_PAGES = frozenset(
    {
        "index.md",
        "overview.md",
        "dsl_reference.md",
        "results_file.md",
        "appendix_ids.md",
    }
)

_DSL_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*")

RESULTS_PAGE = MANUAL_DIR / "results_file.md"

# a row of a results table opens with its series as `kind.attribute`, split by
# line breaks, and their unit, in backticks
_RESULT_ROW = re.compile(r"\| ((?:`[a-z]+\.[a-z0-9_]+`(?:<br>)?)+) \| `([^`]+)` \|")
_SERIES = re.compile(r"`([a-z]+)\.([a-z0-9_]+)`")
_CODE_SPAN = re.compile(r"`([^`]+)`")


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
        A node-type name as navigate.core.node_type spells it, e.g. ``ModelDefinition``.

    Returns
    -------
    Path :
        The page, e.g. ``docs/reference_manual/model_definition.md``. The page is not
        read, so a node type without one resolves to a path that does not exist.
    """
    return MANUAL_DIR / f"{attribute_to_instance_name(node_type)}.md"


def normalise_heading(heading: str) -> str | None:
    """
    Reduce a level-three heading to the DSL name it documents.

    Command headings escape every underscore, many attribute headings carry a
    trailing space, and three headings on vessel.md end in an escaped
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


def _section_lines(page: Path, section: str) -> list[str]:
    """
    Collect the lines of one level-two section of a page.

    Fenced code blocks are left out.

    Parameters
    ----------
    page : Path
        A manual page.
    section : str
        A level-two section title, e.g. ``Results``.

    Returns
    -------
    list[str] :
        The unfenced lines inside that section, in order.

    Raises
    ------
    ValueError
        If the page has no such section.
    """
    lines = page.read_text().splitlines()
    section_lines = []
    inside = False
    found = False

    for line, fenced in zip(lines, _fence_mask(lines), strict=True):
        if fenced:
            continue

        if line.startswith("## "):
            inside = line[3:].strip() == section
            found = found or inside

        elif inside:
            section_lines.append(line)

    if not found:
        raise ValueError(f"{page.name} has no '## {section}' section")

    return section_lines


def results_tables() -> dict[str, dict[str, str]]:
    """
    Read the results the results file page lists, with their units, by kind.

    The tables in the "## Results" section open each row with the series it
    describes, as ``kind.attribute`` in backticks, e.g. ``global.installed_power``,
    and their unit.

    Returns
    -------
    dict[str, dict[str, str]] :
        Unit per attribute, per kind.

    Raises
    ------
    ValueError
        If a series is listed twice, which would otherwise drop out unseen.
    """
    tables: dict[str, dict[str, str]] = {}

    for line in _section_lines(RESULTS_PAGE, "Results"):
        row = _RESULT_ROW.match(line)

        if row is None:
            continue

        series, unit = row.groups()

        for kind, attribute in _SERIES.findall(series):
            listed = tables.setdefault(kind, {})

            if attribute in listed:
                raise ValueError(f"'{kind}.{attribute}' is listed twice")

            listed[attribute] = unit

    return tables


def kind_column_values() -> set[str]:
    """
    Read the kinds the results file page gives for the ``kind`` column.

    Returns
    -------
    set[str] :
        The code spans in the content cell of the ``kind`` row under "## Table".

    Raises
    ------
    ValueError
        If the section has no ``kind`` row.
    """
    for line in _section_lines(RESULTS_PAGE, "Table"):
        if line.startswith("| `kind` |"):
            content = line.split("|")[3]

            return set(_CODE_SPAN.findall(content))

    raise ValueError(f"{RESULTS_PAGE.name} '## Table' has no `kind` row")
