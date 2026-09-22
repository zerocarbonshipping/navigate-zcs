# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
No public expectation reader declares a parameter defaulting to None.

A None default spells two operations under one name — read this key, or read
the whole storage — which CODESTYLE.md asks to be split, and leaves the return
type a union no caller needs. A time index defaulting to the full slice is one
operation and stays, so None, not optionality, is what fails here. The sweep
covers the private base classes too: a subclass inherits every reader they
define.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

import pytest

import navigate.core.expectations as expectations

READER_PREFIXES = ("get_", "is_")


def _function(member):
    # vars() hands over a staticmethod or classmethod wrapper rather than its
    # function: unwrap it, or a reader declared as one is silently skipped
    if isinstance(member, (staticmethod, classmethod)):
        return member.__func__
    return member


def _readers():
    found = []
    for module_info in pkgutil.iter_modules(expectations.__path__):
        module = importlib.import_module(f"{expectations.__name__}.{module_info.name}")
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module.__name__:
                continue

            found.extend(
                pytest.param(cls, name, id=f"{cls.__name__}.{name}")
                for name, member in vars(cls).items()
                if name.startswith(READER_PREFIXES)
                and inspect.isfunction(_function(member))
            )

    # an empty scan means the module walk rotted, not that the invariant holds
    assert found

    return found


@pytest.mark.parametrize(("cls", "name"), _readers())
def test_reader_has_no_none_default(cls, name):
    parameters = inspect.signature(getattr(cls, name)).parameters

    assert [p.name for p in parameters.values() if p.default is None] == []
