# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Source node, a source of energy for fuel production."""

from __future__ import annotations

from navigate.core import assign_id
from navigate.core.enum_ import SourceDependencyID
from navigate.core.node import Node
from navigate.core.node_type import SOURCE


class Source(Node):
    """An energy source for fuel production, stand-alone or connected to a grid."""

    def __init__(self, name: str) -> None:
        super().__init__(name, SOURCE)

        # external variables -----------------------------------------------------------
        self.dependency: SourceDependencyID

    # external methods (DSL attributes) ------------------------------------------------
    def set_dependency(self, dependency: str) -> None:
        """
        Set the dependency of the source.

        Examples
        --------
        - STANDALONE
        - CONNECTED

        Parameters
        ----------
        dependency
            Type of dependency.
        """
        self.dependency = assign_id(dependency, SourceDependencyID)
