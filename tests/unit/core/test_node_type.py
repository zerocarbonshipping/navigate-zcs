# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the node type attribute contract: every NODE_CLASS entry's instances carry that type."""
import pytest

from navigate.parser._keywords import NODE_CLASS


class TestNodeTypeAttribute:

    @pytest.mark.parametrize('type_, cls', NODE_CLASS.items())
    def test_every_node_class_carries_its_type(self, type_: str, cls: type):
        node = cls("n")
        assert node.type == type_
