# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Feedstock node, a named input to fuel production processes."""

from __future__ import annotations

from navigate.core.node import Node
from navigate.core.node_type import FEEDSTOCK


class Feedstock(Node):
    """A feedstock that processes consume and regions and plants price and transport."""

    def __init__(self, name: str) -> None:
        super().__init__(name, FEEDSTOCK)
