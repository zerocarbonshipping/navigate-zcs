# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import navigate.core.id_ as id_
from navigate.core import assign_id
from navigate.core.enum_ import SourceDependencyID
from navigate.core.nodes.node import Node
from navigate.exceptions import no_value_assigned_error


class Source(Node):
    def __init__(self, name):
        super().__init__(name)

        self._type = id_.SOURCE

        self._dependency = None  # enum, whether source is standalone or connected

    # external attributes set through the input deck -------------------------------------------------------------------
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

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):
        if self._dependency is None:
            no_value_assigned_error(self, 'Dependency')

    def get_dependency(self):
        return self._dependency
