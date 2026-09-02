# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core import Scalar, as_scalar, assign_value
from navigate.core.node import Node
from navigate.core.node_type import FORECAST, VARIABLE


class _Machinery(Node):
    """
    Generic node used for the cost parameters of all pieces of machinery:
    - PowerSystem
    - Converter
    - Technology
    """

    def __init__(self, name: str, type_: str) -> None:
        super().__init__(name, type_)

        self.capex = None          # float, CAPEX for installation
        self.opex = None           # float, OPEX for installation
        self.lifetime = None       # float, lifetime of the installation
        self.replacement = None    # float, fraction of CAPEX paid when replacing at end of lifetime

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_capex(self, capex):
        """
        Set the CAPEX related to installing the machinery.

        Examples
        --------
        - 1e6
        - Forecast("name")

        Parameters
        ----------
        capex : float | NodeReference
            CAPEX cost of installing the machinery.
        """

        self.capex = assign_value(as_scalar(capex), type_=(FORECAST, VARIABLE), lower=0.)

    def set_opex(self, opex):
        """
        Set the OPEX related to maintaining the machinery.

        Examples
        --------
        - 1e4
        - Forecast("name")

        Parameters
        ----------
        opex : float | NodeReference
            OPEX cost per year of maintaining the machinery.
        """

        self.opex = assign_value(as_scalar(opex), type_=(FORECAST, VARIABLE), lower=0.)

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

        if self.capex is None:
            self.capex = Scalar(0.)

        if self.opex is None:
            self.opex = Scalar(0.)

        if self.replacement is None:
            self.replacement = Scalar(1.)
