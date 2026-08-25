# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core import Scalar, as_scalar, assign_value
from navigate.core.id_ import FORECAST, VARIABLE
from navigate.core.node import Node


class _Machinery(Node):
    """
    Generic node used for the cost parameters of all pieces of machinery:
    - PowerSystem
    - Converter
    - Technology
    """

    def __init__(self, name):
        super().__init__(name)

        self.CAPEX = None          # float, CAPEX for installation
        self.OPEX = None           # float, OPEX for installation
        self.lifetime = None       # float, lifetime of the installation
        self.replacement = None    # float, fraction of CAPEX paid when replacing at end of lifetime

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_CAPEX(self, CAPEX):
        """
        Set the CAPEX related to installing the machinery.

        Examples
        --------
        - 1e6
        - Forecast("name")

        Parameters
        ----------
        CAPEX : float | NodeReference
            CAPEX cost of installing the machinery.
        """

        self.CAPEX = assign_value(as_scalar(CAPEX), type_=(FORECAST, VARIABLE), lower=0.)

    def set_OPEX(self, OPEX):
        """
        Set the OPEX related to maintaining the machinery.

        Examples
        --------
        - 1e4
        - Forecast("name")

        Parameters
        ----------
        OPEX : float | NodeReference
            OPEX cost per year of maintaining the machinery.
        """

        self.OPEX = assign_value(as_scalar(OPEX), type_=(FORECAST, VARIABLE), lower=0.)

    def set_lifetime(self, lifetime):
        """
        Set the lifetime of the machinery.

        If no lifetime is defined, the lifetime will default to the lifetime of vessel it is assigned to.

        Examples
        --------
        - 25.0
        - Forecast("name")

        Parameters
        ----------
        lifetime : float | NodeReference
            Lifetime of the machinery.
        """

        self.lifetime = assign_value(as_scalar(lifetime), type_=(FORECAST, VARIABLE),
                                     lower=0., inclusive_lower=False)

    def set_replacement(self, replacement):
        """
        Set the CAPEX replacement fraction related to re-installing the machinery at the end of lifetime.

        Examples
        --------
        - 0.5
        - Forecast("name")

        Parameters
        ----------
        replacement : float | NodeReference
            Fraction of CAPEX for re-installing the machinery at end of lifetime.
        """

        self.replacement = assign_value(as_scalar(replacement), type_=(FORECAST, VARIABLE), lower=0.)

    # internal methods -------------------------------------------------------------------------------------------------
    def _initialize_machinery(self):

        if self.CAPEX is None:
            self.CAPEX = Scalar(0.)

        if self.OPEX is None:
            self.OPEX = Scalar(0.)

        if self.replacement is None:
            self.replacement = Scalar(1.)
