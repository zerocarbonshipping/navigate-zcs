# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The deck surface the node classes declare, tabulated by node type for the tests.

Each table maps a node type to its attributes or commands and the sections
allowing each, read off the ``deck_attributes`` and ``deck_commands`` marks of
the class, so a mark added to a setter is covered here without a new entry.
"""

from __future__ import annotations

from navigate.core.dsl import required_attributes
from navigate.core.node_registry import GENERAL_NODE_CLASS, NODE_CLASS

NODE_ATTRIBUTE_SECTIONS = {
    node_type: {name: entry.sections for name, entry in cls.deck_attributes.items()}
    for node_type, cls in NODE_CLASS.items()
}

GENERAL_NODE_ATTRIBUTE_SECTIONS = {
    type_: {name: entry.sections for name, entry in cls.deck_attributes.items()}
    for type_, cls in GENERAL_NODE_CLASS.items()
}

NODE_COMMAND_SECTIONS = {
    node_type: {name: entry.sections for name, entry in cls.deck_commands.items()}
    for node_type, cls in NODE_CLASS.items()
}

# the node types with at least one attribute every deck must assign
NODE_REQUIRED_ATTRIBUTES = {
    node_type: required_attributes(cls.deck_attributes)
    for node_type, cls in NODE_CLASS.items()
    if required_attributes(cls.deck_attributes)
}

GENERAL_NODE_REQUIRED_ATTRIBUTES = {
    type_: required_attributes(cls.deck_attributes)
    for type_, cls in GENERAL_NODE_CLASS.items()
    if required_attributes(cls.deck_attributes)
}
