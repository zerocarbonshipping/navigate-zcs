# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the node type-tag contract.

Every NODE_CLASS entry's instances carry that type, and `is_calculator`
agrees with the `_Calculator` class hierarchy.
"""

from __future__ import annotations

import pytest

from navigate.core.node_type import is_calculator
from navigate.core.nodes._calculator import _Calculator
from navigate.parser._keywords import NODE_CLASS


class TestNodeTypeAttribute:
    @pytest.mark.parametrize(("type_", "cls"), NODE_CLASS.items())
    def test_every_node_class_carries_its_type(self, type_: str, cls: type):
        node = cls("n")
        assert node.type == type_

    @pytest.mark.parametrize("cls", NODE_CLASS.values())
    def test_is_calculator_agrees_with_the_calculator_hierarchy(self, cls: type):
        assert is_calculator(cls("n")) == issubclass(cls, _Calculator)
