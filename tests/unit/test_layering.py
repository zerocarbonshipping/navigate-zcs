# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Mechanical layering checks on `core`, `output` and the foundation modules.

`core` may import only itself, `util` and `exceptions`; `output` only itself, `core`,
`util`, `exceptions` and `logging_`; `exceptions` and `logging_` only `util`.
Type-only imports count.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "navigate"
CORE = PACKAGE / "core"
CORE_ALLOWED = ("navigate.core", "navigate.util", "navigate.exceptions")
OUTPUT = PACKAGE / "output"
OUTPUT_ALLOWED = (
    "navigate.output",
    "navigate.core",
    "navigate.util",
    "navigate.exceptions",
    "navigate.logging_",
)
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


@pytest.mark.parametrize("path", sorted(CORE.rglob("*.py")), ids=lambda p: p.name)
def test_core_imports_only_core_util_and_exceptions(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = _offending_imports(ast.walk(tree), CORE_ALLOWED)
    assert not offenders, f"navigate/core/{path.relative_to(CORE)} imports {offenders}"


@pytest.mark.parametrize(
    "path", sorted(OUTPUT.rglob("*.py")), ids=lambda p: str(p.relative_to(OUTPUT))
)
def test_output_imports_only_output_core_util_and_foundation(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = _offending_imports(ast.walk(tree), OUTPUT_ALLOWED)
    relative_path = path.relative_to(OUTPUT)
    assert not offenders, f"navigate/output/{relative_path} imports {offenders}"


@pytest.mark.parametrize("path", FOUNDATION_MODULES, ids=lambda p: p.name)
def test_foundation_modules_import_only_util(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = _offending_imports(ast.walk(tree), FOUNDATION_ALLOWED)
    assert not offenders, f"navigate/{path.name} imports {offenders}"
