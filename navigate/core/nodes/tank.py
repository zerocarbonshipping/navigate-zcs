# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core import as_list, as_scalar, assign_id_list, assign_value
from navigate.core.enum_ import FuelTypeID
from navigate.core.node_type import TANK, VARIABLE
from navigate.core.nodes._machinery import _Machinery
from navigate.exceptions import no_value_assigned_error


class Tank(_Machinery):
    def __init__(self, name):
        super().__init__(name, TANK)

        self.fuel_types = None             # list, fuel type ID
        self.size = None                   # float, tank size

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_fuel_types(self, fuel_types):
        """
        Set the fuel types that can be stored in the tank.

        Examples
        --------
        - OIL
        - [OIL, METHANOL]
        - [METHANOL]

        Parameters
        ----------
        fuel_types : list[str]
            List of fuel types which can be stored in the tank.
        """

        self.fuel_types = assign_id_list(as_list(fuel_types), FuelTypeID, length=(1, None))

    def set_size(self, size):
        """
        Set the volumetric size of the tank in cubic meter.

        Examples
        - 8000

        Parameters
        ----------
        size : float
            Volumetric size of the tank in cubic meter.
        """

        self.size = assign_value(as_scalar(size), type_=VARIABLE, lower=0.)

    # external attributes set through the input deck -------------------------------------------------------------------
    def initialize(self):
        if self.fuel_types is None:
            no_value_assigned_error(self, 'FuelTypes')

        if self.size is None:
            no_value_assigned_error(self, 'Size')

        self._initialize_machinery()

    def get_fuel_types(self):
        return self.fuel_types
