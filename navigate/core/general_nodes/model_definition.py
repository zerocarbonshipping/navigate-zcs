# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the ModelDefinition general node, the start date and GWP horizon of a run."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.assign import assign_date, assign_value
from navigate.core.general_nodes._general_node import _GeneralNode

if TYPE_CHECKING:
    import numpy as np


class ModelDefinition(_GeneralNode):
    """Hold the simulation start date and the emission lifetime used for GWP."""

    def __init__(self) -> None:
        super().__init__()

        # external variables -----------------------------------------------------------
        self.start_date: np.datetime64
        self.emissions_lifetime: float = 100.0

    # external methods (DSL attributes) ------------------------------------------------
    def set_start_date(self, start_date: np.datetime64) -> None:
        """
        Set the start date of the simulation in dd-mm-yyyy format (hyphen or slash).

        Examples
        --------
        - "01-01-2023"
        - "01/01/2023"

        Parameters
        ----------
        start_date
            Assignment read from input deck.
        """
        self.start_date = assign_date(start_date)

    def set_emissions_lifetime(self, emissions_lifetime: float) -> None:
        """
        Set the emission lifetime used to calculate GWP for CO2 equivalent emissions.

        Examples
        --------
        - 100

        Parameters
        ----------
        emissions_lifetime
            Assignment read from input deck.
        """
        self.emissions_lifetime = assign_value(emissions_lifetime, lower=0.0)
