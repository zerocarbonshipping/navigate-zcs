# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Tank node, onboard storage for a set of fuel types."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import as_list, as_scalar, assign_id_list, assign_value
from navigate.core.enum_ import FuelTypeID
from navigate.core.node_type import TANK, VARIABLE
from navigate.core.nodes._machinery import _Machinery

if TYPE_CHECKING:
    from navigate.core.nodes.input_kinds import ScalarInput


class Tank(_Machinery):
    """An onboard fuel tank: the fuel types it can hold and its volume."""

    def __init__(self, name: str) -> None:
        super().__init__(name, TANK)

        # external variables -----------------------------------------------------------
        self.fuel_types: list[FuelTypeID]
        self.size: ScalarInput

    # external methods (DSL attributes) ------------------------------------------------
    def set_fuel_types(self, fuel_types: list[str]) -> None:
        """
        Set the fuel types that can be stored in the tank.

        Examples
        --------
        - OIL
        - [OIL, METHANOL]
        - [METHANOL]

        Parameters
        ----------
        fuel_types
            List of fuel types which can be stored in the tank.
        """
        self.fuel_types = assign_id_list(
            as_list(fuel_types), FuelTypeID, length=(1, None)
        )

    def set_size(self, size: float | ScalarInput) -> None:
        """
        Set the volumetric size of the tank in cubic meter.

        Examples
        --------
        - 8000

        Parameters
        ----------
        size
            Volumetric size of the tank in cubic meter.
        """
        self.size = assign_value(as_scalar(size), type_=VARIABLE, lower=0.0)

    # internal methods -----------------------------------------------------------------
    def get_fuel_types(self) -> list[FuelTypeID]:
        return self.fuel_types
