# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core.node import Node
from navigate.core.node_type import TRANSPORT


class Transport(Node):
    def __init__(self, name):
        super().__init__(name)

        self.type = TRANSPORT
