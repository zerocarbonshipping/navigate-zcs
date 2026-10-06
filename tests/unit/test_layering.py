# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Mechanical layering checks on every top-level module and package of `navigate`.

`LAYERS` mirrors the Layering section of ARCHITECTURE.md. Each unit, a package or
a module directly under `navigate/`, imports only itself and the units in its
row, type-only imports included, and the table names exactly the units on disk.
`INDEPENDENT_PAIRS` and `MODEL_FREE` state which units never list one another,
checked against the table itself. `CORE_ORDER` orders the runtime imports between
the subpackages of `core` and its flat modules.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "navigate"
CORE = PACKAGE / "core"

FOUNDATION = frozenset({"util", "exceptions"})
DOMAINS = frozenset({"economics", "policy", "fleet", "fuel", "bunker"})

# unit -> the other units it may import; a unit may always import itself, and
# `__init__` is navigate/__init__.py
LAYERS = {
    "util": frozenset(),
    "__init__": frozenset(),
    "exceptions": frozenset({"util"}),
    "logging_": frozenset({"util"}),
    "core": FOUNDATION,
    "economics": frozenset({"core"}) | FOUNDATION,
    "policy": frozenset({"core"}) | FOUNDATION,
    "fleet": frozenset({"economics", "core"}) | FOUNDATION,
    "fuel": frozenset({"economics", "core"}) | FOUNDATION,
    "bunker": frozenset({"policy", "logging_", "core"}) | FOUNDATION,
    "parser": frozenset({"core"}) | FOUNDATION,
    "output": frozenset({"core"}) | FOUNDATION,
    # every unit but __main__
    "simulation": DOMAINS
    | frozenset({"parser", "output", "logging_", "core", "__init__"})
    | FOUNDATION,
    "__main__": frozenset({"simulation", "logging_", "core"}) | FOUNDATION,
}

# neither unit of a pair may list the other
INDEPENDENT_PAIRS = (("fleet", "fuel"), ("parser", "output"))
# units that may list no part of the model
MODEL_FREE = frozenset({"parser", "output"})
MODEL = DOMAINS | {"simulation"}

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


def _packages_in(directory):
    return {
        path.name for path in directory.iterdir() if (path / "__init__.py").is_file()
    }


CORE_SUBPACKAGES = _packages_in(CORE)


def _is_module(dotted):
    path = PACKAGE.parent.joinpath(*dotted.split("."))
    return path.with_suffix(".py").is_file() or (path / "__init__.py").is_file()


def _imported_modules(node):
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]

    # `from package import name` imports the submodule `name` where one exists,
    # and otherwise a name the package's __init__.py defines
    return [
        f"{node.module}.{alias.name}"
        if _is_module(f"{node.module}.{alias.name}")
        else node.module
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
                module
                for module in _imported_modules(node)
                if (module == "navigate" or module.startswith("navigate."))
                and not is_allowed(module)
            ]
    return offenders


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


def _unit_of_module(module):
    parts = module.split(".")
    return parts[1] if len(parts) > 1 else "__init__"


def _unit_of_path(path):
    return path.relative_to(PACKAGE).parts[0].removesuffix(".py")


def _core_group(parts):
    return parts[0] if parts and parts[0] in CORE_SUBPACKAGES else FLAT


def _relative_id(path):
    return str(path.relative_to(PACKAGE))


@pytest.mark.parametrize("path", sorted(PACKAGE.rglob("*.py")), ids=_relative_id)
def test_imports_stay_in_the_units_row(path):
    unit = _unit_of_path(path)
    assert unit in LAYERS, f"navigate/{_relative_id(path)}: unit {unit} has no row"

    allowed = LAYERS[unit] | {unit}
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = _offending_imports(
        ast.walk(tree), lambda module: _unit_of_module(module) in allowed
    )
    assert not offenders, f"navigate/{_relative_id(path)} imports {offenders}"


def test_layers_cover_exactly_the_top_level_units():
    units = {path.stem for path in PACKAGE.glob("*.py")} | _packages_in(PACKAGE)
    rows = set(LAYERS)
    assert rows == units, (
        f"units without a row: {sorted(units - rows)}; "
        f"rows without a unit: {sorted(rows - units)}"
    )

    unknown = {unit: sorted(row - rows) for unit, row in LAYERS.items() if row - rows}
    assert not unknown, f"rows list units that do not exist: {unknown}"


@pytest.mark.parametrize(
    ("unit", "other"),
    [
        *INDEPENDENT_PAIRS,
        *((second, first) for first, second in INDEPENDENT_PAIRS),
        *((unit, model) for unit in sorted(MODEL_FREE) for model in sorted(MODEL)),
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

    unknown = {
        group: sorted(row - set(CORE_ORDER))
        for group, row in CORE_ORDER.items()
        if row - set(CORE_ORDER)
    }
    assert not unknown, f"rows list groups that do not exist: {unknown}"


@pytest.mark.parametrize("path", sorted(CORE.rglob("*.py")), ids=_relative_id)
def test_core_runtime_imports_follow_the_core_order(path):
    group = _core_group(path.relative_to(CORE).parts[:-1])
    assert group in CORE_ORDER, f"navigate/{_relative_id(path)}: {group} has no row"

    allowed = CORE_ORDER[group] | {group}
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = _offending_imports(
        _runtime_nodes(tree),
        lambda module: (
            _unit_of_module(module) != "core"
            or _core_group(module.split(".")[2:]) in allowed
        ),
    )
    assert not offenders, f"navigate/{_relative_id(path)} ({group}) imports {offenders}"
