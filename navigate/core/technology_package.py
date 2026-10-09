# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the technology package, a bundle of technologies held by the Fleet node."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from navigate.core.enum_ import EnergyDemandID
    from navigate.core.nodes.technology import Technology
    from navigate.core.types_ import CurveInput
    from navigate.util.types_ import FloatArray


@dataclass(slots=True, eq=False)
class TechnologyPackage:
    """
    Represent a bundle of technologies with their combined effects and cost flow.

    The combined effects and the cost flow derive from the technologies and are
    refreshed every time-step, as technology properties may depend on time.

    Parameters
    ----------
    technologies
        Technologies in the package.
    compound_savings
        Combined energy-saving fraction per energy demand type.
    compound_powers
        Summed external power per energy demand type, MW.
    transfer_curves
        Power-transfer curves per (source, destination) pair with any transfer.
    shore_power_capacity
        Summed shore power connection capacity, MW.
    cost_flow
        Cumulative CAPEX and OPEX cost flow of the package, USD/year.
    """

    technologies: list[Technology]
    compound_savings: dict[EnergyDemandID, float] = field(default_factory=dict)
    compound_powers: dict[EnergyDemandID, float] = field(default_factory=dict)
    transfer_curves: dict[tuple[EnergyDemandID, EnergyDemandID], list[CurveInput]] = (
        field(default_factory=dict)
    )
    shore_power_capacity: float = 0.0
    cost_flow: FloatArray = field(default_factory=lambda: np.zeros(0, dtype=float))

    @property
    def is_empty(self) -> bool:
        """Whether the package holds no technology."""
        return len(self.technologies) == 0

    @property
    def includes_transfer(self) -> bool:
        """Whether any technology transfers power between energy demand types."""
        return bool(self.transfer_curves)
