# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Mechanical layering check: core must not import the domain packages at runtime.

The known core -> logging_/output back-edge of the table/report/plot nodes is a separate
concern and not asserted here.
"""
import ast
from pathlib import Path

import pytest

CORE = Path(__file__).resolve().parents[2] / 'navigate' / 'core'
FORBIDDEN = ('navigate.fleet', 'navigate.fuel')


def _is_forbidden(module):
    return any(module == package or module.startswith(package + '.') for package in FORBIDDEN)


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
def test_core_does_not_import_domain_packages_at_runtime(path):
    offenders = []
    for node in _runtime_nodes(ast.parse(path.read_text(encoding='utf-8'))):
        if isinstance(node, ast.Import):
            offenders += [alias.name for alias in node.names if _is_forbidden(alias.name)]
        elif isinstance(node, ast.ImportFrom) and node.module and _is_forbidden(node.module):
            offenders.append(node.module)
    assert not offenders, f'navigate/core/{path.relative_to(CORE)} imports {offenders} at runtime'
