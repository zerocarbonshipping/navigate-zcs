# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Source node, a source of energy for fuel production."""

from __future__ import annotations

from navigate.core import SECTION_DEFINE, assign_id, deck_attribute
from navigate.core.enum_ import SourceDependencyID
from navigate.core.node import Node
from navigate.core.node_type import SOURCE


class Source(Node):
    """An energy source for fuel production, stand-alone or connected to a grid."""

    type = SOURCE

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # external variables -----------------------------------------------------------
        self.dependency: SourceDependencyID

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(SECTION_DEFINE, required=True)
    def set_dependency(self, value: str) -> None:
        """Set whether the source is standalone or connected to its region's grid."""
        self.dependency = assign_id(value, SourceDependencyID)
