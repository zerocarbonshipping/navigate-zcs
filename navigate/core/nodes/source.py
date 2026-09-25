# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from navigate.core import assign_id
from navigate.core.enum_ import SourceDependencyID
from navigate.core.node import Node
from navigate.core.node_type import SOURCE
from navigate.exceptions import no_value_assigned_error


class Source(Node):
    def __init__(self, name: str) -> None:
        super().__init__(name, SOURCE)

        # external variables -----------------------------------------------------------
        self._dependency: SourceDependencyID | None = None

    # external methods (DSL attributes) ------------------------------------------------
    def set_dependency(self, dependency):
        """
        Set the dependency of the source.

        Examples
        --------
        - STANDALONE
        - CONNECTED

        Parameters
        ----------
        dependency : str
            Type of dependency.
        """
        self._dependency = assign_id(dependency, SourceDependencyID)

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:
        if self._dependency is None:
            no_value_assigned_error(self, "Dependency")

    @property
    def dependency(self) -> SourceDependencyID:
        if self._dependency is None:
            no_value_assigned_error(self, "Dependency")

        return self._dependency
