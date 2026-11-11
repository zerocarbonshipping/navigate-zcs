# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Check every import inside `navigate/` against the layering of ARCHITECTURE.md.

This script is the arbiter of the layering, and the table in ARCHITECTURE.md
its readable summary; a change to the layering changes both together. It parses
the source with `ast` and never imports `navigate`, so it runs in any
environment. `make lint` runs it:

    python tools/check_layering.py
"""

from __future__ import annotations

import ast
import sys
from itertools import combinations, product
from pathlib import Path
from typing import TYPE_CHECKING, TypeGuard

if TYPE_CHECKING:
    from collections.abc import Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]

# the table of ARCHITECTURE.md, row for row: each unit on the left imports
# itself and the units on the right, nothing else from navigate, type-only
# imports included
LAYERING = {
    ("util", "__init__", "simulation"): (),
    ("exceptions",): ("util",),
    ("core",): ("foundation",),
    ("simulation.economics",): ("core", "foundation"),
    ("simulation.cohort",): ("core", "foundation"),
    ("simulation.fleet", "simulation.fuel"): (
        "simulation.economics",
        "simulation.cohort",
        "core",
        "foundation",
    ),
    ("simulation.bunker", "simulation.policy"): ("core", "foundation"),
    ("parser", "output"): ("core", "foundation"),
    ("app",): ("driver", "foundation"),
    ("simulation.time_stepping",): ("domains", "core", "foundation"),
    ("driver",): (
        "simulation.time_stepping",
        "domains",
        "parser",
        "output",
        "core",
        "foundation",
    ),
    ("__main__",): ("app",),
}

# the names the table gives groups of units
GROUPS = {
    "foundation": ("util", "exceptions"),
    "domains": (
        "simulation.fleet",
        "simulation.fuel",
        "simulation.economics",
        "simulation.bunker",
        "simulation.policy",
    ),
}

# `simulation` is simulation/__init__.py alone, so a new module or package
# directly under simulation/ falls in no unit; every other unit holds all
# below it
INIT_ONLY_UNIT = "simulation"

# what ARCHITECTURE.md forbids the table itself: no row may link two of the
# first units, nor a unit on one side of a pair to a unit on the other, nor
# the last units to a simulation unit
UNLINKED_UNITS = (
    "simulation.bunker",
    "simulation.fleet",
    "simulation.fuel",
    "simulation.policy",
)
UNLINKED_SIDES = (
    (
        ("simulation.economics", "simulation.cohort"),
        ("simulation.bunker", "simulation.policy"),
    ),
    (("parser",), ("output",)),
)
UNLINKED_FROM_SIMULATION = ("parser", "output")

# inside core, runtime imports run one way: each part imports itself and the
# parts on the right; type-only imports are free
CORE_LAYERING = {
    "nodes/": ("expectations/", "results/", "flat modules"),
    "expectations/": ("flat modules",),
    "results/": ("flat modules",),
    "general_nodes/": ("flat modules",),
    "flat modules": (),
}

# the registries read the node classes off their annotations at runtime
CORE_EXCEPTIONS = {"core.node_registry": ("nodes/", "general_nodes/")}


def main() -> int:
    """Print every break of the layering and return the exit status."""
    rows = _rows()
    files = sorted((REPO_ROOT / "navigate").rglob("*.py"))
    modules = {_module(path) for path in files}

    problems = list(_check_links(rows))
    for path in files:
        problems.extend(_check_file(path, rows, modules))

    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


def _rows() -> dict[str, tuple[str, ...]]:
    """Return the units each unit may import besides itself, groups expanded."""
    rows = {}
    for units, names in LAYERING.items():
        imports = tuple(unit for name in names for unit in GROUPS.get(name, (name,)))
        rows.update(dict.fromkeys(units, imports))
    return rows


def _check_links(rows: dict[str, tuple[str, ...]]) -> Iterator[str]:
    """Yield a problem for each row that links two units ARCHITECTURE.md keeps apart."""
    simulation_units = [unit for unit in rows if unit.split(".")[0] == "simulation"]

    pairs = list(combinations(UNLINKED_UNITS, 2))
    for side, other_side in UNLINKED_SIDES:
        pairs.extend(product(side, other_side))
    pairs.extend(product(UNLINKED_FROM_SIMULATION, simulation_units))

    for unit, other in pairs:
        if other in rows[unit] or unit in rows[other]:
            yield (
                f"tools/check_layering.py: LAYERING links {unit} and {other}.\n"
                "  ARCHITECTURE.md (Layering) forbids any row to link these two"
                " units: restore the row, or change that rule in ARCHITECTURE.md"
                " and here together."
            )


def _check_file(
    path: Path, rows: dict[str, tuple[str, ...]], modules: set[str]
) -> Iterator[str]:
    """Yield a problem for a file outside every unit or each import it may not make."""
    location = path.relative_to(REPO_ROOT)
    name = _name(_module(path))
    unit = _unit(name, rows)

    if unit is None:
        yield (
            f"{location}: falls in no unit of the layering"
            " (ARCHITECTURE.md, Layering).\n"
            "  Move it into the unit it belongs to, or give its new unit a row in"
            " the table in ARCHITECTURE.md and in LAYERING in"
            " tools/check_layering.py: a new top-level module or package, or one"
            " directly under navigate/simulation/, needs one."
        )
        return

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=location)
    imports = list(_imports(tree, type_only=False))

    yield from _check_table(location, unit, imports, rows, modules)
    if unit == "core":
        yield from _check_core(location, name, imports, modules)


def _check_table(
    location: Path,
    unit: str,
    imports: list[tuple[ast.Import | ast.ImportFrom, bool]],
    rows: dict[str, tuple[str, ...]],
    modules: set[str],
) -> Iterator[str]:
    """Yield a problem for each import, type-only or not, outside the unit's row."""
    allowed = (unit, *rows[unit])

    for statement, _ in imports:
        for target in _targets(statement, modules):
            target_unit = _unit(target, rows)
            if target_unit in allowed:
                continue

            yield (
                f"{_header(location, statement)}\n"
                f"  {unit} may not import {target_unit or target}, type-only"
                " imports included (ARCHITECTURE.md, Layering).\n"
                f"  Allowed from {unit}: {', '.join(allowed)}.\n"
                "  Move what both need into a unit both may import, or have a unit"
                " that may import both pass it in. A change to the layering itself"
                " changes the table in ARCHITECTURE.md and LAYERING in"
                " tools/check_layering.py together."
            )


def _check_core(
    location: Path,
    name: str,
    imports: list[tuple[ast.Import | ast.ImportFrom, bool]],
    modules: set[str],
) -> Iterator[str]:
    """Yield a problem for each runtime import against the one-way rule of core."""
    part = _core_part(name)

    if part is None:
        yield (
            f"{location}: falls in no part of the one-way rule inside core"
            " (ARCHITECTURE.md, Layering).\n"
            "  A new subpackage of core needs its place in that rule, there and"
            " in CORE_LAYERING in tools/check_layering.py."
        )
        return

    allowed = (part, *CORE_LAYERING[part], *CORE_EXCEPTIONS.get(name, ()))
    runtime = [statement for statement, type_only in imports if not type_only]

    for statement in runtime:
        for target in _targets(statement, modules):
            target_part = _core_part(target)
            if not _contains("core", target) or target_part in allowed:
                continue

            yield (
                f"{_header(location, statement)}\n"
                f"  Inside core, {part} may not import {target_part or target} at"
                " runtime (ARCHITECTURE.md, Layering).\n"
                f"  Allowed at runtime from {part}: {', '.join(allowed)}.\n"
                "  Import it under `if TYPE_CHECKING:` where only annotations need"
                " it; otherwise move the code into a part that may import it."
            )


def _header(location: Path, statement: ast.Import | ast.ImportFrom) -> str:
    """Return the line that names an import and where it is."""
    return f"{location}:{statement.lineno}: {ast.unparse(statement)}"


def _module(path: Path) -> str:
    """Return the dotted module name of a file."""
    parts = path.relative_to(REPO_ROOT).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _name(module: str) -> str:
    """Return a navigate module's name as ARCHITECTURE.md writes it."""
    if module == "navigate":
        return "__init__"
    return module.removeprefix("navigate.")


def _unit(name: str, rows: dict[str, tuple[str, ...]]) -> str | None:
    """Return the longest unit that contains the named module, if any."""
    containing = [unit for unit in rows if _contains(unit, name)]
    return max(containing, key=len, default=None)


def _contains(unit: str, name: str) -> bool:
    """Tell whether a unit contains the named module."""
    if unit == INIT_ONLY_UNIT:
        return name == unit
    return name == unit or name.startswith(f"{unit}.")


def _core_part(name: str) -> str | None:
    """Return the part of core the named module falls in, if any."""
    _, _, below_core = name.partition(".")
    subpackage, dot, _ = below_core.partition(".")
    if f"{subpackage}/" in CORE_LAYERING:
        return f"{subpackage}/"
    return None if dot else "flat modules"


def _imports(
    node: ast.AST, type_only: bool
) -> Iterator[tuple[ast.Import | ast.ImportFrom, bool]]:
    """Yield every import statement in a tree, and whether it is type-only."""
    if isinstance(node, ast.Import | ast.ImportFrom):
        yield node, type_only

    elif _is_type_checking(node):
        for statement in node.body:
            yield from _imports(statement, type_only=True)
        for statement in node.orelse:
            yield from _imports(statement, type_only)

    else:
        for child in ast.iter_child_nodes(node):
            yield from _imports(child, type_only)


def _is_type_checking(node: ast.AST) -> TypeGuard[ast.If]:
    """Tell whether a node is an `if TYPE_CHECKING:` block."""
    return isinstance(node, ast.If) and ast.unparse(node.test) == "TYPE_CHECKING"


def _targets(statement: ast.Import | ast.ImportFrom, modules: set[str]) -> list[str]:
    """Return the names of the navigate modules an import statement imports."""
    if isinstance(statement, ast.Import):
        imported = [alias.name for alias in statement.names]
    else:
        imported = _imported_from(statement, modules)

    in_navigate = [module for module in imported if module.split(".")[0] == "navigate"]
    return [_name(module) for module in dict.fromkeys(in_navigate)]


def _imported_from(statement: ast.ImportFrom, modules: set[str]) -> list[str]:
    """Return what a from-import imports: each name's submodule, else its module."""
    # a relative import is ruff's to reject (TID252), so only absolute ones count
    if statement.level > 0 or statement.module is None:
        return []

    imported = []
    for alias in statement.names:
        submodule = f"{statement.module}.{alias.name}"
        imported.append(submodule if submodule in modules else statement.module)
    return imported


if __name__ == "__main__":
    sys.exit(main())
