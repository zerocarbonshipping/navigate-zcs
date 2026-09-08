# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Mechanical layering check: core must import only the foundation layers at runtime.

`logging_` is allow-listed by design: the table nodes' use of it and the
`logging_` -> `core.unit` edge are the known remainder of the layering cleanup.
"""
import ast
from pathlib import Path

import pytest

CORE = Path(__file__).resolve().parents[2] / 'navigate' / 'core'
FOUNDATION = ('navigate.core', 'navigate.util', 'navigate.exceptions', 'navigate.logging_')


def _is_forbidden(module):
    if module != 'navigate' and not module.startswith('navigate.'):
        return False
    return not any(module == package or module.startswith(package + '.') for package in FOUNDATION)


def _is_type_checking_guard(test):
    return 'TYPE_CHECKING' in (getattr(test, 'id', ''), getattr(test, 'attr', ''))


def _runtime_nodes(node):
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.If) and _is_type_checking_guard(child.test):
            for branch in child.orelse:
                yield from _runtime_nodes(branch)
            continue
        yield child
        yield from _runtime_nodes(child)


@pytest.mark.parametrize('path', sorted(CORE.rglob('*.py')), ids=lambda p: p.name)
def test_core_imports_only_foundation_layers_at_runtime(path):
    offenders = []
    for node in _runtime_nodes(ast.parse(path.read_text(encoding='utf-8'))):
        if isinstance(node, ast.Import):
            offenders += [alias.name for alias in node.names if _is_forbidden(alias.name)]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                offenders.append(f'relative import (level {node.level}) — use absolute imports')
            elif node.module and _is_forbidden(node.module):
                offenders.append(node.module)
    assert not offenders, f'navigate/core/{path.relative_to(CORE)} imports {offenders} at runtime'
