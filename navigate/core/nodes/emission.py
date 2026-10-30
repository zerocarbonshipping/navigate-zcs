# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Emission node, an emitted species weighted into CO2 equivalents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    SECTION_DEFINE,
    Scalar,
    as_scalar,
    assign_id,
    assign_value,
    deck_attribute,
)
from navigate.core.enum_ import FuelTypeID
from navigate.core.node import Node
from navigate.core.node_type import CURVE, EMISSION, VARIABLE

if TYPE_CHECKING:
    from navigate.core.types_ import CurveArgument, CurveInput


class Emission(Node):
    """A species, its global warming potential and the fuel type whose slip emits it."""

    type = EMISSION

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # external variables -----------------------------------------------------------
        self.global_warming_potential: CurveInput = Scalar(0.0)
        self.fuel_type: FuelTypeID | None = None

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(SECTION_DEFINE)
    def set_global_warming_potential(self, value: CurveArgument) -> None:
        """Set the Global Warming Potential (GWP) of the emission."""
        self.global_warming_potential = assign_value(
            as_scalar(value), type_=(CURVE, VARIABLE), lower=0.0
        )

    @deck_attribute(SECTION_DEFINE)
    def set_fuel_type(self, value: str) -> None:
        """Set the fuel type whose slip produces the emission."""
        self.fuel_type = assign_id(value, FuelTypeID)
