# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import as_list, as_scalar, assign_id_list, assign_value
from navigate.core.enum_ import FuelTypeID
from navigate.core.node_type import TANK, VARIABLE
from navigate.core.nodes._machinery import _Machinery
from navigate.exceptions import no_value_assigned_error

if TYPE_CHECKING:
    from navigate.core.nodes.input_kinds import ScalarInput


class Tank(_Machinery):
    def __init__(self, name: str) -> None:
        super().__init__(name, TANK)

        # external variables -----------------------------------------------------------
        self.fuel_types: list[FuelTypeID] | None = None
        self.size: ScalarInput | None = None

    # external methods (DSL attributes) ------------------------------------------------
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
        self.fuel_types = assign_id_list(
            as_list(fuel_types), FuelTypeID, length=(1, None)
        )

    def set_size(self, size):
        """
        Set the volumetric size of the tank in cubic meter.

        Examples
        --------
        - 8000

        Parameters
        ----------
        size : float
            Volumetric size of the tank in cubic meter.
        """
        self.size = assign_value(as_scalar(size), type_=VARIABLE, lower=0.0)

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:
        if self.fuel_types is None:
            no_value_assigned_error(self, "FuelTypes")

        if self.size is None:
            no_value_assigned_error(self, "Size")

    def get_fuel_types(self):
        return self.fuel_types
