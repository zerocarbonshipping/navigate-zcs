# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import Scalar, as_scalar, assign_value
from navigate.core.node import Node
from navigate.core.node_type import FORECAST, VARIABLE

if TYPE_CHECKING:
    from navigate.core.nodes.input_kinds import ForecastInput


class _Machinery(Node):
    """
    Provide a generic node for cost parameters shared by all machinery types.

    - PowerSystem
    - Converter
    - Technology
    """

    def __init__(self, name: str, type_: str) -> None:
        super().__init__(name, type_)

        # external variables -----------------------------------------------------------
        self.capex: ForecastInput = Scalar(0.0)
        self.opex: ForecastInput = Scalar(0.0)
        self.lifetime: ForecastInput | None = None
        self.replacement: ForecastInput = Scalar(1.0)

    # external methods (DSL attributes) ------------------------------------------------
    def set_capex(self, capex: float | ForecastInput) -> None:
        """
        Set the CAPEX related to installing the machinery.

        Examples
        --------
        - 1e6
        - Forecast("name")

        Parameters
        ----------
        capex
            CAPEX cost of installing the machinery.
        """
        self.capex = assign_value(
            as_scalar(capex), type_=(FORECAST, VARIABLE), lower=0.0
        )

    def set_opex(self, opex: float | ForecastInput) -> None:
        """
        Set the OPEX related to maintaining the machinery.

        Examples
        --------
        - 1e4
        - Forecast("name")

        Parameters
        ----------
        opex
            OPEX cost per year of maintaining the machinery.
        """
        self.opex = assign_value(as_scalar(opex), type_=(FORECAST, VARIABLE), lower=0.0)

    def set_lifetime(self, lifetime: float | ForecastInput) -> None:
        """
        Set the lifetime of the machinery.

        If no lifetime is defined, the lifetime will default to the lifetime of vessel
        it is assigned to.

        Examples
        --------
        - 25.0
        - Forecast("name")

        Parameters
        ----------
        lifetime
            Lifetime of the machinery.
        """
        self.lifetime = assign_value(
            as_scalar(lifetime),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    def set_replacement(self, replacement: float | ForecastInput) -> None:
        """
        Set the CAPEX replacement fraction to reinstall machinery at end of lifetime.

        Examples
        --------
        - 0.5
        - Forecast("name")

        Parameters
        ----------
        replacement
            Fraction of CAPEX for re-installing the machinery at end of lifetime.
        """
        self.replacement = assign_value(
            as_scalar(replacement), type_=(FORECAST, VARIABLE), lower=0.0
        )
