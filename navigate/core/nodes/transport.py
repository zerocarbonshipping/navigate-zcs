# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Transport node, a mode of transport for a fuel or a feedstock."""

from __future__ import annotations

from navigate.core.node import Node
from navigate.core.node_type import TRANSPORT


class Transport(Node):
    """A mode of transport that plants use to move feedstocks and fuels."""

    def __init__(self, name: str) -> None:
        super().__init__(name, TRANSPORT)
