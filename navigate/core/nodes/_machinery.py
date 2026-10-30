# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the machinery base shared by the Converter, Tank and Technology nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import Scalar, as_scalar, assign_value, deck_attribute
from navigate.core.node import Node
from navigate.core.node_type import FORECAST, VARIABLE

if TYPE_CHECKING:
    from navigate.core.types_ import ForecastArgument, ForecastInput


class _Machinery(Node):
    """The costs, lifetime and replacement share common to every machinery node."""

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # external variables -----------------------------------------------------------
        self.capex: ForecastInput = Scalar(0.0)
        self.opex: ForecastInput = Scalar(0.0)
        self.lifetime: ForecastInput | None = None
        self.replacement: ForecastInput = Scalar(1.0)

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute()
    def set_capex(self, value: ForecastArgument) -> None:
        """Set the CAPEX of installing the machinery."""
        self.capex = assign_value(
            as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0
        )

    @deck_attribute()
    def set_opex(self, value: ForecastArgument) -> None:
        """Set the yearly OPEX of maintaining the machinery."""
        self.opex = assign_value(
            as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0
        )

    @deck_attribute()
    def set_lifetime(self, value: ForecastArgument) -> None:
        """Set the lifetime of the machinery."""
        self.lifetime = assign_value(
            as_scalar(value),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    @deck_attribute()
    def set_replacement(self, value: ForecastArgument) -> None:
        """Set the CAPEX fraction paid to reinstall the machinery at end of lifetime."""
        self.replacement = assign_value(
            as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0
        )
