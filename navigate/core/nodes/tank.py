# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Tank node, onboard storage for a set of fuel types."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    SECTION_DEFINE,
    as_scalar,
    assign_id_list,
    assign_value,
    deck_attribute,
)
from navigate.core.enum_ import FuelTypeID
from navigate.core.node_type import TANK, VARIABLE
from navigate.core.nodes._machinery import _Machinery

if TYPE_CHECKING:
    from navigate.core.types_ import ScalarArgument, ScalarInput


class Tank(_Machinery):
    """An onboard fuel tank: the fuel types it can hold and its volume."""

    type = TANK

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # external variables -----------------------------------------------------------
        self.fuel_types: list[FuelTypeID]
        self.size: ScalarInput

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(SECTION_DEFINE, required=True)
    def set_fuel_types(self, fuel_types: str | list[str]) -> None:
        """Set the fuel types that can be stored in the tank."""
        self.fuel_types = assign_id_list(fuel_types, FuelTypeID, min_length=1)

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_size(self, size: ScalarArgument) -> None:
        """Set the volumetric size of the tank."""
        self.size = assign_value(as_scalar(size), type_=VARIABLE, lower=0.0)
