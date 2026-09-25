# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.assign import assign_value
from navigate.core.general_nodes._general_node import _GeneralNode
from navigate.exceptions import no_value_assigned_error

if TYPE_CHECKING:
    import numpy as np


class ModelDefinition(_GeneralNode):
    def __init__(self) -> None:
        super().__init__()

        # external variables -----------------------------------------------------------
        self._start_date: np.datetime64 | None = None
        self.emissions_lifetime: float = 100.0

    # external methods (DSL attributes) ------------------------------------------------
    def set_start_date(self, start_date):
        """
        Set the start date of the simulation in dd-mm-yyyy format (hyphen or slash).

        Examples
        --------
        - "01-01-2023"
        - "01/01/2023"

        Parameters
        ----------
        start_date : np.datetime64
            Assignment read from input deck.
        """
        self._start_date = assign_value(start_date, scalar=False, date=True)

    def set_emissions_lifetime(self, emissions_lifetime):
        """
        Set the emission lifetime used to calculate GWP for CO2 equivalent emissions.

        Examples
        --------
        - 100

        Parameters
        ----------
        emissions_lifetime : float
            Assignment read from input deck.
        """
        self.emissions_lifetime = assign_value(emissions_lifetime, lower=0.0)

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:

        if self._start_date is None:
            no_value_assigned_error(self, "StartDate")

    @property
    def start_date(self) -> np.datetime64:
        if self._start_date is None:
            no_value_assigned_error(self, "StartDate")

        return self._start_date
