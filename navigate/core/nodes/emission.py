# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The Emission node: a species emitted by fuel use, weighted into CO2 equivalents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import Scalar, as_scalar, assign_id, assign_value
from navigate.core.enum_ import FuelTypeID
from navigate.core.node import Node
from navigate.core.node_type import CURVE, EMISSION, VARIABLE

if TYPE_CHECKING:
    from navigate.core import Expression
    from navigate.core.nodes.curve import Curve
    from navigate.core.nodes.input_kinds import CurveInput
    from navigate.core.nodes.variable import Variable


class Emission(Node):
    """An emitted species and the global warming potential it is weighted by."""

    def __init__(self, name: str) -> None:
        super().__init__(name, EMISSION)

        # external variables -----------------------------------------------------------
        self.global_warming_potential: CurveInput = Scalar(0.0)
        self.fuel_type: FuelTypeID | None = None

    # external methods (DSL attributes) ------------------------------------------------
    def set_global_warming_potential(
        self, global_warming_potential: float | Curve | Variable | Expression
    ) -> None:
        """
        Set the Global Warming Potential (GWP) of the emission.

        Examples
        --------
        - 36.6
        - Curve("name")

        Parameters
        ----------
        global_warming_potential
            The Global Warming Potential of the emission, in ton CO2 equivalent
            per ton emitted.
        """
        self.global_warming_potential = assign_value(
            as_scalar(global_warming_potential), type_=(CURVE, VARIABLE), lower=0.0
        )

    def set_fuel_type(self, fuel_type: str) -> None:
        """
        Set the fuel type associated with this emission for slip gating.

        When set, this emission will only receive slip contributions from fuels
        whose fuel type matches this value.

        Examples
        --------
        - METHANE

        Parameters
        ----------
        fuel_type
            The fuel type that produces this emission when slipping.
        """
        self.fuel_type = assign_id(fuel_type, FuelTypeID)
