# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Every public profile reader takes no arguments and returns the whole timeline.

The report writer calls a profile getter with no arguments, and the plots and the
fleet post-processing index the returned array or dict, so a key or time-index
parameter has no caller to serve. The sweep covers the private base classes too:
a subclass inherits every reader they define.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

import pytest

import navigate.core.profiles as profiles

READER_PREFIXES = ("get_", "is_", "has_", "cost_is_")


def _function(member):
    # vars() hands over the staticmethod or classmethod wrapper, not its function
    if isinstance(member, (staticmethod, classmethod)):
        func = member.__func__
    else:
        func = member

    return func


def _readers():
    found = []
    for module_info in pkgutil.iter_modules(profiles.__path__):
        module = importlib.import_module(f"{profiles.__name__}.{module_info.name}")
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
def test_reader_takes_only_self(cls, name):
    assert list(inspect.signature(getattr(cls, name)).parameters) == ["self"]
