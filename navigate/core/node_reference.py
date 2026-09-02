# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.node_type import TypeCheckMixin


class NodeReference(TypeCheckMixin):
    def __init__(self, type_: str, name: str) -> None:
        super().__init__(type_)

        self.name = name

        # string indicating the file and line in
        # the deck where the node is referenced
        self.reference_location = ''

        # this attribute is only relevant for calculators
        # they are set during the call to assign_value if
        # bounds on the attribute are included in the call
        self.internal_bounds = (-np.inf, np.inf)

    def set_internal_bounds(self, lower, upper):
        self.internal_bounds = (lower, upper)

    def __repr__(self):
        return "{}(\"{}\")".format(self.type, self.name)


class WildcardNodeReference(NodeReference):
    """A node reference whose name contains glob wildcards (``*``, ``?``).

    Expanded into concrete nodes during reference resolution in the parser.
    May only appear inside list contexts; a ``WildcardNodeReference`` found
    outside a list raises an error.
    """

    @property
    def pattern(self) -> str:
        return self.name
