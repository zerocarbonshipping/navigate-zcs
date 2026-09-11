# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from navigate.core import as_list, as_scalar_list, assign_list
from navigate.core.node import Node
from navigate.core.node_type import FEEDSTOCK, FORECAST, PROCESS, VARIABLE


class Process(Node):
    def __init__(self, name):
        super().__init__(name, PROCESS)

        # external variables -----------------------------------------------------------
        self.feeds = []  # list[Feedstock | Process], feedstock or sub-process input
        self.conversions = []  # list[float], conversion factor per process/feedstock

    # external methods (DSL attributes) ------------------------------------------------
    def set_feeds(self, feeds):
        """
        Set the list of feedstocks or output from other processes used in the process.

        Examples
        --------
        - Feedstock("name")
        - [Feedstock("name"), Process("name")]

        Parameters
        ----------
        feeds : list[NodeReference]
            A list of feedstock and/or process.
        """
        self.feeds = assign_list(
            as_list(feeds), unique=True, scalar=False, type_=(FEEDSTOCK, PROCESS)
        )

    def set_conversions(self, conversion):
        """
        Set the conversion factors required for turning the feed into fuel.

        Examples
        --------
        - [0.5, 2.5]

        Parameters
        ----------
        conversion : list[float | NodeReference]
            A list of conversion factors in tons of feed per tons of fuel.
        """
        self.conversions = assign_list(
            as_scalar_list(conversion), type_=(FORECAST, VARIABLE), lower=0.0
        )

    # internal methods -----------------------------------------------------------------
    def initialize(self):

        if len(self.feeds) != len(self.conversions):
            raise ValueError(
                f"The number of feeds ({len(self.feeds)}) and conversions"
                f" ({len(self.conversions)}) must correspond."
            )
