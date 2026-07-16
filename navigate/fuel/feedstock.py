# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core import Node
from navigate.core.id_ import FEEDSTOCK


class Feedstock(Node):
    def __init__(self, name):
        super().__init__(name)

        self._type = FEEDSTOCK
