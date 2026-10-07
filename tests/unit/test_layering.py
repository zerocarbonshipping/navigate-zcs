# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Mechanical layering checks on every module and package of `navigate`.

`LAYERS` mirrors the Layering section of ARCHITECTURE.md. Its keys are units,
modules or packages named by their dotted path under `navigate`; a file belongs
to the longest key that contains it, and imports only its own unit and the units
in its row, type-only imports included. Every file belongs to a unit, every key
exists on disk and the table is acyclic. `INDEPENDENT_PAIRS` states which units
never list one another, checked against the table itself. `CORE_ORDER` orders
the runtime imports between the subpackages of `core` and its flat modules.
"""

from __future__ import annotations

import ast
import graphlib
import itertools
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "navigate"
CORE = PACKAGE / "core"
SOURCES = sorted(PACKAGE.rglob("*.py"))
CORE_SOURCES = sorted(CORE.rglob("*.py"))

FOUNDATION = frozenset({"util", "exceptions"})
DOMAINS = frozenset({"economics", "policy", "fleet", "fuel", "bunker"})

# unit -> the other units it may import; a unit may always import itself, and
# `__init__` is navigate/__init__.py, the unit of a bare `navigate` import
LAYERS = {
    "util": frozenset(),
    "__init__": frozenset(),
    "exceptions": frozenset({"util"}),
    "core": FOUNDATION,
    "economics": frozenset({"core"}) | FOUNDATION,
    "policy": frozenset({"core"}) | FOUNDATION,
    "fleet": frozenset({"economics", "core"}) | FOUNDATION,
    "fuel": frozenset({"economics", "core"}) | FOUNDATION,
    "bunker": frozenset({"policy", "core"}) | FOUNDATION,
    "parser": frozenset({"core"}) | FOUNDATION,
    "output": frozenset({"core"}) | FOUNDATION,
    "app": frozenset({"driver"}) | FOUNDATION,
    "simulation": DOMAINS | {"core"} | FOUNDATION,
    "driver": frozenset({"simulation", "parser", "output", "core"}) | FOUNDATION,
    "__main__": frozenset({"app"}),
}

# the simulation is the simulation package and the domains it steps through
SIMULATION = DOMAINS | {"simulation"}
# neither unit of a pair may list the other
INDEPENDENT_PAIRS = (
    ("fleet", "fuel"),
    ("parser", "output"),
    *itertools.product(("parser", "output"), sorted(SIMULATION)),
)

# core group -> the other groups it may import at runtime; a group may always
# import itself, and FLAT is every module directly in core/, __init__.py included
FLAT = "flat"
CORE_ORDER = {
    "nodes": frozenset({FLAT, "expectations", "profiles"}),
    "expectations": frozenset({FLAT}),
    "profiles": frozenset({FLAT}),
    "general_nodes": frozenset({FLAT}),
    FLAT: frozenset(),
}
# the directories directly in core/ that hold Python source at any depth,
# package or not; a deeper directory belongs to its top-level group
CORE_SUBPACKAGES = {
    path.relative_to(CORE).parts[0]
    for path in CORE_SOURCES
    if len(path.relative_to(CORE).parts) > 1
}


def _is_navigate(module):
    return module == "navigate" or module.startswith("navigate.")


def _parts_of_module(module):
    return tuple(module.split(".")[1:])


def _parts_of_path(path):
    parts = path.relative_to(PACKAGE).with_suffix("").parts
    return parts[:-1] if parts[-1] == "__init__" else parts


def _exists(parts):
    path = PACKAGE.joinpath(*parts)
    return path.with_suffix(".py").is_file() or path.is_dir()


def _imported_parts(node):
    """Return each `navigate` module an import reaches, as parts below `navigate`."""
    if isinstance(node, ast.Import):
        return [
            _parts_of_module(alias.name)
            for alias in node.names
            if _is_navigate(alias.name)
        ]
    if not _is_navigate(node.module):
        return []

    # `from package import name` imports the submodule `name` where one exists,
    # and otherwise a name the package's __init__.py defines
    package = _parts_of_module(node.module)
    return [
        (*package, alias.name) if _exists((*package, alias.name)) else package
        for alias in node.names
    ]


def _offending_imports(nodes, is_allowed):
    offenders = []
    for node in nodes:
        if isinstance(node, ast.ImportFrom) and node.level:
            offenders.append(
                f"relative import (level {node.level}) - use absolute imports"
            )
        elif isinstance(node, ast.Import | ast.ImportFrom):
            offenders += [
                ".".join(("navigate", *parts))
                for parts in _imported_parts(node)
                if not is_allowed(parts)
            ]
    return list(dict.fromkeys(offenders))


def _is_type_checking(test):
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    return (
        isinstance(test, ast.Attribute)
        and test.attr == "TYPE_CHECKING"
        and isinstance(test.value, ast.Name)
        and test.value.id == "typing"
    )


def _runtime_nodes(tree):
    pending = [tree]
    while pending:
        node = pending.pop()
        yield node
        if isinstance(node, ast.If) and _is_type_checking(node.test):
            pending += node.orelse
        else:
            pending += ast.iter_child_nodes(node)


def _unit_of(parts):
    parts = parts or ("__init__",)
    keys = (".".join(parts[:length]) for length in range(len(parts), 0, -1))
    return next((key for key in keys if key in LAYERS), None)


def _core_group(parts):
    return parts[0] if parts and parts[0] in CORE_SUBPACKAGES else FLAT


def _relative_id(path):
    return str(path.relative_to(PACKAGE))


def _unknown_names(table):
    return {
        name: sorted(row - set(table))
        for name, row in table.items()
        if row - set(table)
    }


def _assert_acyclic(table):
    sorter = graphlib.TopologicalSorter(
        {name: row - {name} for name, row in table.items()}
    )
    try:
        tuple(sorter.static_order())
    except graphlib.CycleError as error:
        pytest.fail(f"import cycle: {error.args[1]}")


@pytest.mark.parametrize("path", SOURCES, ids=_relative_id)
def test_each_unit_imports_only_its_row(path):
    unit = _unit_of(_parts_of_path(path))
    assert unit is not None, f"navigate/{_relative_id(path)} belongs to no unit"

    allowed = LAYERS[unit] | {unit}
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = _offending_imports(
        ast.walk(tree), lambda parts: _unit_of(parts) in allowed
    )
    assert not offenders, f"navigate/{_relative_id(path)} imports {offenders}"


def test_layers_name_existing_units_only():
    missing = sorted(key for key in LAYERS if not _exists(key.split(".")))
    assert not missing, f"keys naming no module or package: {missing}"

    unknown = _unknown_names(LAYERS)
    assert not unknown, f"rows list units that are not keys: {unknown}"

    named = {name for pair in INDEPENDENT_PAIRS for name in pair}
    stale = sorted(named - set(LAYERS))
    assert not stale, f"independence rules name units that are not keys: {stale}"


def test_layers_are_acyclic():
    _assert_acyclic(LAYERS)


@pytest.mark.parametrize(
    ("unit", "other"),
    [
        *INDEPENDENT_PAIRS,
        *((second, first) for first, second in INDEPENDENT_PAIRS),
    ],
)
def test_independent_units_do_not_list_each_other(unit, other):
    assert other not in LAYERS[unit], f"the {unit} row lists {other}"


def test_core_order_covers_exactly_the_core_subpackages():
    groups = set(CORE_ORDER) - {FLAT}
    assert groups == CORE_SUBPACKAGES, (
        f"subpackages without a row: {sorted(CORE_SUBPACKAGES - groups)}; "
        f"rows without a subpackage: {sorted(groups - CORE_SUBPACKAGES)}"
    )

    unknown = _unknown_names(CORE_ORDER)
    assert not unknown, f"rows list groups that do not exist: {unknown}"


def test_core_order_is_acyclic():
    _assert_acyclic(CORE_ORDER)


@pytest.mark.parametrize("path", CORE_SOURCES, ids=_relative_id)
def test_core_runtime_imports_follow_the_core_order(path):
    group = _core_group(path.relative_to(CORE).parts[:-1])
    assert group in CORE_ORDER, f"navigate/{_relative_id(path)}: {group} has no row"

    allowed = CORE_ORDER[group] | {group}
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = _offending_imports(
        _runtime_nodes(tree),
        lambda parts: parts[:1] != ("core",) or _core_group(parts[1:]) in allowed,
    )
    assert not offenders, f"navigate/{_relative_id(path)} ({group}) imports {offenders}"
