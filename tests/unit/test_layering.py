# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Mechanical layering checks on `core` and the foundation modules.

`core` may import only itself, `util` and `exceptions` at runtime; `exceptions`
and `logging_` may import only `util`, type-only imports included.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "navigate"
CORE = PACKAGE / "core"
CORE_ALLOWED = ("navigate.core", "navigate.util", "navigate.exceptions")
FOUNDATION_MODULES = (PACKAGE / "exceptions.py", PACKAGE / "logging_.py")
FOUNDATION_ALLOWED = ("navigate.util",)


def _is_forbidden(module, allowed):
    if module != "navigate" and not module.startswith("navigate."):
        return False
    return not any(
        module == package or module.startswith(package + ".") for package in allowed
    )


def _offending_imports(nodes, allowed):
    offenders = []
    for node in nodes:
        if isinstance(node, ast.Import):
            offenders += [
                alias.name for alias in node.names if _is_forbidden(alias.name, allowed)
            ]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                offenders.append(
                    f"relative import (level {node.level}) — use absolute imports"
                )
            elif node.module and _is_forbidden(node.module, allowed):
                offenders.append(node.module)
    return offenders


def _is_type_checking_guard(test):
    return "TYPE_CHECKING" in (getattr(test, "id", ""), getattr(test, "attr", ""))


def _runtime_nodes(node):
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.If) and _is_type_checking_guard(child.test):
            for branch in child.orelse:
                yield from _runtime_nodes(branch)
            continue
        yield child
        yield from _runtime_nodes(child)


@pytest.mark.parametrize("path", sorted(CORE.rglob("*.py")), ids=lambda p: p.name)
def test_core_imports_only_core_util_and_exceptions_at_runtime(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = _offending_imports(_runtime_nodes(tree), CORE_ALLOWED)
    assert not offenders, (
        f"navigate/core/{path.relative_to(CORE)} imports {offenders} at runtime"
    )


@pytest.mark.parametrize("path", FOUNDATION_MODULES, ids=lambda p: p.name)
def test_foundation_modules_import_only_util(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = _offending_imports(ast.walk(tree), FOUNDATION_ALLOWED)
    assert not offenders, f"navigate/{path.name} imports {offenders}"
