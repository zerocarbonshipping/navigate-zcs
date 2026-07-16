# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import numpy as np

from navigate.core.profiles._fuel_infrastructure_profile import _FuelInfrastructureProfile


class _InfrastructureAggregateProfile(_FuelInfrastructureProfile):
    def __init__(self):
        super().__init__()

    def _initialize_infrastructure_aggregate(self) -> None:
        pass

    def add_infrastructure_aggregate_profile(
            self, profile: _InfrastructureAggregateProfile,
            idx: int | slice = np.s_[:]) -> None:
        """

        Parameters
        ----------
        profile : _InfrastructureAggregateProfile | PortProfile
            Aggregate profile from other node.
        idx : int
            Time-step index.
        """
