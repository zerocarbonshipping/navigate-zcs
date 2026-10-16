# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Every DSL-shaped method on a node class is registered, and every entry resolves.

The parser reaches an attribute through its `set_*` setter and a command through
the method of the same name, so the node classes, not the registries, are where a
new DSL entry starts. A setter left out of _attributes.py or _commands.py is
unreachable from a deck and, since test_node_pages.py checks the manual against
the registries, also undocumented. This closes the chain: method -> registry ->
manual heading, in both directions.
"""

from __future__ import annotations

import pytest

from navigate.parser._attributes import (
    GENERAL_NODE_ATTRIBUTE_SECTIONS,
    NODE_ATTRIBUTE_SECTIONS,
)
from navigate.parser._commands import NODE_COMMAND_SECTIONS
from navigate.parser._keywords import GENERAL_NODE_CLASS, NODE_CLASS
from navigate.util import attribute_to_setter

CLASSES = NODE_CLASS | GENERAL_NODE_CLASS
ATTRIBUTES = NODE_ATTRIBUTE_SECTIONS | GENERAL_NODE_ATTRIBUTE_SECTIONS

# a deck sets an attribute through set_* and calls commands named set_* or add_*;
# any public method with one of these prefixes is presumed to be DSL surface
DSL_PREFIXES = ("set_", "add_")

# methods with a DSL prefix that the simulation, not a deck, calls
INTERNAL_SETTERS = {
    # the attribute that holds a calculator narrows its bounds at assignment
    "set_internal_bounds",
    # the simulation loop advances a Timetable's clock each step
    "set_current_time",
    # a Producer claims its Plants while the supply chain initializes
    "set_producer_assignment",
}

NODE_TYPES = sorted(CLASSES)


def _registered_methods(node_type: str) -> dict[str, str]:
    """Map each registered method of a node type to the DSL name a deck writes."""
    methods = {attribute_to_setter(name): name for name in ATTRIBUTES[node_type]}
    methods |= {name: name for name in NODE_COMMAND_SECTIONS.get(node_type, {})}
    return methods


# lists every public set_*/add_* method on each node class and checks that each
# is registered for the deck (or is a known internal setter).
# catches: a new setter written on the node but never registered, so no deck can
# use it and the manual never mentions it.
@pytest.mark.parametrize("node_type", NODE_TYPES)
def test_every_dsl_method_is_registered(node_type):
    cls = CLASSES[node_type]
    dsl_methods = {
        name
        for name in dir(cls)
        if name.startswith(DSL_PREFIXES) and callable(getattr(cls, name))
    }

    unregistered = dsl_methods - set(_registered_methods(node_type)) - INTERNAL_SETTERS

    assert not unregistered, (
        f"{cls.__name__} methods no deck can reach: {sorted(unregistered)}; register"
        " them in navigate/parser/_attributes.py or _commands.py and document them,"
        " or list them in INTERNAL_SETTERS if the simulation calls them"
    )


# checks every registered attribute and command maps to a method on the node
# class, and that the method has a docstring.
# catches: a setter renamed without updating the registry, so a deck using it
# fails at run time with a missing method.
@pytest.mark.parametrize("node_type", NODE_TYPES)
def test_every_registry_entry_resolves_to_a_documented_method(node_type):
    cls = CLASSES[node_type]
    missing = []
    undocumented = []

    for method, dsl_name in _registered_methods(node_type).items():
        member = getattr(cls, method, None)
        if not callable(member):
            missing.append(f"{dsl_name} -> {method}")
        elif not (member.__doc__ or "").strip():
            undocumented.append(method)

    assert not missing, f"{cls.__name__} has no method for {missing}"
    assert not undocumented, (
        f"{cls.__name__} methods without a docstring: {undocumented}"
    )


# checks every name on the internal-setter allowlist is still a method on some
# node class.
# catches: a stale allowlist entry that would quietly hide a future DSL method
# with the same name.
def test_internal_setters_exist():
    # a stale allowlist entry would hide the next method that takes its name
    defined = {
        name
        for cls in CLASSES.values()
        for name in dir(cls)
        if name in INTERNAL_SETTERS
    }

    assert defined == INTERNAL_SETTERS
