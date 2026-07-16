# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core.assign import as_scalar, assign_id, assign_value
from navigate.core.general_node import GeneralNode
from navigate.core.id_ import FORECAST, VARIABLE
from navigate.core.misc import BOOL_ID
from navigate.exceptions import DeckKeywordError


class ModelDefinition(GeneralNode):
    def __init__(self):
        super().__init__()

        self._start_date = None
        self._emissions_lifetime = None
        self._enable_offsetting = False
        self._offsetting_cost = None

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

    def set_enable_offsetting(self, enable_offsetting):
        """
        Set whether emissions offsetting is enabled in the simulation.

        When enabled, actors can purchase emission offsets at the OffsettingCost instead of paying
        higher compliance costs under regulations or levies that allow offsetting.

        Examples
        --------
        - TRUE
        - FALSE

        Parameters
        ----------
        enable_offsetting : str
            Boolean flag.
        """

        self._enable_offsetting = assign_id(enable_offsetting, BOOL_ID)

    def set_offsetting_cost(self, offsetting_cost):
        """
        Set the cost of purchasing emission offsets in USD/ton emission.

        This is the global offset market price. If a policy allows offsetting and the offsetting cost is
        lower than the policy's compliance cost, actors will offset instead of paying the higher cost.

        Examples
        --------
        - 50
        - Forecast("offset_price")

        Parameters
        ----------
        offsetting_cost : float | NodeReference
            Cost of offsetting in USD/ton emission.
        """

        self._offsetting_cost = assign_value(as_scalar(offsetting_cost), type_=(FORECAST, VARIABLE), lower=0.)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):

        if self._start_date is None:
            raise DeckKeywordError("Error in ModelDefinition: 'StartDate' must be defined.")

        if self._emissions_lifetime is None:
            self._emissions_lifetime = 100.

        if self._enable_offsetting and self._offsetting_cost is None:
            raise DeckKeywordError("Error in ModelDefinition: 'OffsettingCost' must be defined"
                                   " when 'EnableOffsetting' is TRUE.")

    def get_start_date(self):
        return self._start_date

    def get_emissions_lifetime(self):
        return self._emissions_lifetime

    def get_enable_offsetting(self):
        return self._enable_offsetting

    def get_offsetting_cost(self):
        return self._offsetting_cost
