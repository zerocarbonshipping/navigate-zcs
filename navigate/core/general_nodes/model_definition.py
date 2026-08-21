# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core.assign import assign_value
from navigate.core.general_nodes._general_node import _GeneralNode
from navigate.exceptions import DeckKeywordError


class ModelDefinition(_GeneralNode):
    def __init__(self):
        super().__init__()

        self._start_date = None
        self._emissions_lifetime = None

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_start_date(self, start_date):
        """
        Set the start date of the simulation in dd-mm-yyyy format (either hyphen or slash).

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
        Set the emission lifetime used to calculate the GWP value for calculation of CO2 equivalent emissions.

        Examples
        --------
        - 100

        Parameters
        ----------
        emissions_lifetime : float
            Assignment read from input deck.
        """

        self._emissions_lifetime = assign_value(emissions_lifetime, lower=0.)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):

        if self._start_date is None:
            raise DeckKeywordError("Error in ModelDefinition: 'StartDate' must be defined.")

        if self._emissions_lifetime is None:
            self._emissions_lifetime = 100.

    def get_start_date(self):
        return self._start_date

    def get_emissions_lifetime(self):
        return self._emissions_lifetime
