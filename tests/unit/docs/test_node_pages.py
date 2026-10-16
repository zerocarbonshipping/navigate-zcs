# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The reference manual documents exactly the registered DSL surface.

docs/reference_manual is hand-written with no autodoc, so nothing but this test
keeps it from drifting from the parser registries in _attributes.py and
_commands.py. One page per node type, named by the repository's own camel-to-snake
conversion; inside it, the "## Attributes" and "## Commands" sections carry one
"###" heading per registered name, and a node type whose registry is empty carries
no section at all. test_setters_registered.py closes the chain from the node
classes to the registries.
"""

from __future__ import annotations

import pytest

from helpers.reference_manual import (
    MANUAL_DIR,
    NON_NODE_PAGES,
    page_for,
    section_headings,
)
from navigate.parser._attributes import (
    GENERAL_NODE_ATTRIBUTE_SECTIONS,
    NODE_ATTRIBUTE_SECTIONS,
)
from navigate.parser._commands import NODE_COMMAND_SECTIONS
from navigate.parser._keywords import GENERAL_NODE_CLASS, NODE_CLASS

_ATTRIBUTE_SECTIONS = NODE_ATTRIBUTE_SECTIONS | GENERAL_NODE_ATTRIBUTE_SECTIONS

# the parser rejects a command in a general node's body, so a general node's
# command registry is empty by construction rather than by omission
_COMMAND_SECTIONS = NODE_COMMAND_SECTIONS | {
    node: {} for node in GENERAL_NODE_ATTRIBUTE_SECTIONS
}

# the keyword tables, not the registries, decide which node types a deck can
# declare, so a type missing from a registry still needs a page
NODE_TYPES = sorted(NODE_CLASS | GENERAL_NODE_CLASS)

REGISTERED = {
    **{(node, "Attributes"): set(names) for node, names in _ATTRIBUTE_SECTIONS.items()},
    **{(node, "Commands"): set(names) for node, names in _COMMAND_SECTIONS.items()},
}


# checks that the node types a deck can declare, the attribute registry and the
# command registry all list the same types.
# catches: a new node keyword added without registry entries, so it would get no
# page check at all.
def test_every_declarable_node_type_is_registered():
    assert set(NODE_TYPES) == set(_ATTRIBUTE_SECTIONS) == set(_COMMAND_SECTIONS)


# checks each node type has a page in docs/reference_manual, named by the
# camel-to-snake rule and spelling back to the type.
# catches: a new node type with no manual page, or a page named power-system.md
# that does not match PowerSystem.
@pytest.mark.parametrize("node_type", NODE_TYPES)
def test_node_type_has_a_page(node_type):
    page = page_for(node_type)
    spelled_back = "".join(part.capitalize() for part in page.stem.split("_"))

    assert spelled_back == node_type, (
        f"'{node_type}' maps to '{page.name}', which spells back as '{spelled_back}'"
    )
    assert page.is_file(), f"'{node_type}' has no page at {page}"


# checks every page in the reference manual belongs to a node type or is one of
# the known extra pages (index, overview, DSL reference, ID appendix).
# catches: a page left behind after a node type is renamed or removed.
def test_every_page_is_a_node_page_or_a_known_extra():
    node_pages = {page_for(node_type).name for node_type in NODE_TYPES}
    non_node = node_pages & NON_NODE_PAGES

    assert not non_node, f"a node type resolves to a non-node page: {sorted(non_node)}"

    pages = {page.name for page in MANUAL_DIR.glob("*.md")}
    assert pages == node_pages | NON_NODE_PAGES, (
        "a page under docs/reference_manual is neither a node page nor one of the "
        f"known extras: {sorted(pages - node_pages - NON_NODE_PAGES)}"
    )


# compares the ### headings under "## Attributes" and "## Commands" on each node
# page with the registered names, in both directions.
# catches: a new attribute added to the parser but not to the manual, or a
# heading left for an attribute that no longer exists.
@pytest.mark.parametrize("section", ["Attributes", "Commands"])
@pytest.mark.parametrize("node_type", NODE_TYPES)
def test_section_documents_the_registry(node_type, section):
    documented = section_headings(node_type, section)
    registered = REGISTERED[(node_type, section)]

    assert documented == registered, (
        f"{page_for(node_type).name} '## {section}' has drifted: "
        f"registered but undocumented {sorted(registered - documented)}; "
        f"documented but unregistered {sorted(documented - registered)}"
    )
