# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Readers for the hand-written reference manual under docs/reference_manual.

Used by tests/attribute to hold the manual's DSL surface against the parser
registries; nothing generates the manual, so the readers parse its markdown.
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
    {"index.md", "overview.md", "dsl_reference.md", "appendix_ids.md"}
)

_DSL_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


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
    manual spells a node type whose registry is empty.

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
    """
    headings = set()
    current_section = None

    for line in page_for(node_type).read_text().splitlines():
        if line.startswith("## "):
            current_section = line[3:].strip()

        elif line.startswith("### ") and current_section == section:
            name = normalise_heading(line[4:])

            if name is not None:
                headings.add(name)

    return headings
