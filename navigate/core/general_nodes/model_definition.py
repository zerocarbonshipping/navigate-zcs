# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the ModelDefinition general node, the start date and emission lifetime."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import SECTION_DEFINE, assign_date, assign_value, deck_attribute
from navigate.core.general_nodes.general_node import GeneralNode
from navigate.core.node_type import MODEL_DEFINITION

if TYPE_CHECKING:
    import numpy as np


class ModelDefinition(GeneralNode):
    """Hold the simulation start date and the emission lifetime used for GWP."""

    type = MODEL_DEFINITION

    def __init__(self) -> None:
        super().__init__()

        # external variables -----------------------------------------------------------
        self.start_date: np.datetime64
        self.emissions_lifetime: float = 100.0

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(SECTION_DEFINE, required=True)
    def set_start_date(self, value: np.datetime64) -> None:
        """Set the start date of the simulation."""
        self.start_date = assign_date(value)

    @deck_attribute(SECTION_DEFINE)
    def set_emissions_lifetime(self, value: float) -> None:
        """Set the emission lifetime used for GWP."""
        self.emissions_lifetime = assign_value(value, lower=0.0, allow_expression=False)
