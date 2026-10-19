# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""GlobalProfile, the model-wide output storage the simulation fills."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from navigate.core.enum_ import TimingID
from navigate.core.profiles._base_profile import result
from navigate.core.profiles._fuel_infrastructure_profile import (
    _FuelInfrastructureProfile,
)
from navigate.core.profiles._plant_aggregate_profile import _PlantAggregateProfile
from navigate.core.profiles._vessel_aggregate_profile import _VesselAggregateProfile

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.process import Process
    from navigate.core.profiles.profile_context import ProfileContext
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class GlobalProfile(
    _VesselAggregateProfile, _PlantAggregateProfile, _FuelInfrastructureProfile
):
    """Totals over every vessel, plant and port, plus the run's computational time."""

    computational_time: dict[TimingID, FloatArray] = result("s/year", per_step=True)

    def initialize(
        self,
        context: ProfileContext,
        feedstocks: dict[str, Feedstock],
        processes: dict[str, Process],
        regulation_names: Sequence[str] = (),
        levy_names: Sequence[str] = (),
    ) -> None:
        """
        Initialize the global profile's storage arrays and lookups.

        Parameters
        ----------
        context
            Timeline, fuels and emissions of the run.
        feedstocks
            All feedstocks in the simulation.
        processes
            All processes in the simulation.
        regulation_names
            Names of all regulations in the simulation.
        levy_names
            Names of all levies in the simulation.
        """
        self._initialize_base(context)
        self._initialize_fuel_consumer(regulation_names, levy_names)
        self._initialize_fuel_producer(feedstocks, processes)
        self._initialize_fuel_infrastructure()
        self._initialize_vessel_aggregate()
        self._initialize_plant_aggregate()

        self.computational_time = self._default_dict(TimingID)
