# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Feedstock node, a named input to fuel production processes."""

from __future__ import annotations

from navigate.core.enum_ import NodeTypeID
from navigate.core.node import Node


class Feedstock(Node):
    """A feedstock that processes consume, regions price and plants transport."""

    type = NodeTypeID.FEEDSTOCK

    def __init__(self, name: str) -> None:
        super().__init__(name)
