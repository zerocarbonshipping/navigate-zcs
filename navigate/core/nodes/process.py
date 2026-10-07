# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Process node, a step in the bottom-up fuel production hierarchy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import as_list, as_scalar, assign_list, assign_reference_list
from navigate.core.node import Node
from navigate.core.node_type import FEEDSTOCK, FORECAST, PROCESS, VARIABLE

if TYPE_CHECKING:
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.types_ import ForecastArgument, ForecastInput


class Process(Node):
    """A production process turning feedstocks and process outputs into a new stream."""

    def __init__(self, name: str) -> None:
        super().__init__(name, PROCESS)

        # external variables -----------------------------------------------------------
        self.feeds: list[Feedstock | Process] = []
        self.conversions: list[ForecastInput] = []

    # external methods (DSL attributes) ------------------------------------------------
    def set_feeds(self, feeds: Feedstock | Process | list[Feedstock | Process]) -> None:
        """Set the feedstocks and processes whose output feed the process."""
        self.feeds = assign_reference_list(feeds, (FEEDSTOCK, PROCESS), unique=True)

    def set_conversions(
        self, conversion: ForecastArgument | list[ForecastArgument]
    ) -> None:
        """Set the conversion factors of the feeds into fuel."""
        entries: list[ForecastArgument] = as_list(conversion)
        self.conversions = assign_list(
            [as_scalar(entry) for entry in entries],
            type_=(FORECAST, VARIABLE),
            lower=0.0,
        )

    # internal methods -----------------------------------------------------------------
    def check_consistency(self) -> None:
        if len(self.feeds) != len(self.conversions):
            raise ValueError(
                f"The number of feeds ({len(self.feeds)}) and conversions"
                f" ({len(self.conversions)}) must correspond."
            )
