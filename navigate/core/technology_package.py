# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the technology package, a bundle of technologies held by the Fleet node."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.core.enum_ import EnergyDemandID
    from navigate.core.nodes.technology import Technology
    from navigate.core.types_ import CurveInput
    from navigate.util.types_ import FloatArray


@dataclass(slots=True, eq=False)
class TechnologyPackage:
    """
    Represent a bundle of technologies with their combined effects.

    The combined effects derive from the technologies and are set by
    ``update_packages`` every time-step, as technology properties may depend on time.
    The cost flows are held apart, per amortization horizon, in ``PackageCostFlows``.

    Parameters
    ----------
    technologies
        Technologies in the package.
    energy_saving
        Combined energy-saving fraction per energy demand type.
    external_power
        Summed external power per energy demand type, MW.
    transfer_curves
        Power-transfer curves per (source, destination) pair with any transfer.
    shore_power_capacity
        Summed shore power connection capacity, MW.
    """

    technologies: list[Technology]
    energy_saving: dict[EnergyDemandID, float] = field(init=False)
    external_power: dict[EnergyDemandID, float] = field(init=False)
    transfer_curves: dict[tuple[EnergyDemandID, EnergyDemandID], list[CurveInput]] = (
        field(init=False)
    )
    shore_power_capacity: float = field(init=False)

    @property
    def is_empty(self) -> bool:
        """Whether the package holds no technology."""
        return not self.technologies

    @property
    def transfers_power(self) -> bool:
        """Whether any technology transfers power between energy demand types."""
        return bool(self.transfer_curves)


@dataclass(slots=True, eq=False)
class PackageCostFlows:
    """
    Hold the CAPEX and OPEX cost flows of a fleet's packages, per amortization horizon.

    An installation is amortized over the years it serves: a vessel's lifetime for a
    newbuild, the remaining lifetime of a cohort for a retrofit. The flows are built
    on demand for the investment decision time and dropped when the time moves on.

    Parameters
    ----------
    time
        Investment decision time the flows start at, days.
    by_horizon
        Cost flow of each package, from empty to full, per horizon in years, USD/year.
    """

    time: float = field(init=False)
    by_horizon: dict[float, list[FloatArray]] = field(default_factory=dict)
