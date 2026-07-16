# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import FuelTypeID
from navigate.core.profiles._fuel_base_profile import _FuelBaseProfile
from navigate.util import extract_from_dict

if TYPE_CHECKING:
    from navigate.fuel import Fuel
    from navigate.fuel.feedstock import Feedstock
    from navigate.fuel.process import Process
    from navigate.fuel.source import Source


class _FuelProducerProfile(_FuelBaseProfile):
    """
    This class is used exclusively for sub-classing.
    """

    def __init__(self):
        super().__init__()

        # current production
        self._capacity_mass: dict[str, np.ndarray] = {}    # capacity for production, tons/year
        self._production_mass: dict[str, np.ndarray] = {}  # actual production, tons/year

        # pipeline
        self._pipeline_capacity_mass: dict[str, np.ndarray] = {}       # capacity in pipeline, tons/year
        self._pipeline_production_mass: dict[str, np.ndarray] = {}     # production in pipeline, tons/year

        # sources and feedstock
        self._source_energy: dict[str, np.ndarray] = {}    # energy used for production, MWh/year
        self._feed_mass: dict[str, np.ndarray] = {}       # feedstock for production, ton/year

        # constraints
        self._feed_constraint: dict[str, np.ndarray] = {}

    def _initialize_fuel_producer(self, feedstocks: dict[str, Feedstock], fuels: dict[str, Fuel],
                                  processes: dict[str, Process],
                                  sources: dict[str, Source]) -> None:

        self._capacity_mass = self._default_dict(fuels)
        self._production_mass = self._default_dict(fuels)

        self._pipeline_capacity_mass = self._default_dict(fuels)
        self._pipeline_production_mass = self._default_dict(fuels)

        self._source_energy = self._default_dict(sources)

        feed = {**feedstocks, **processes}
        self._feed_mass = self._default_dict(feed)
        self._feed_constraint = self._default_dict(feed, default=np.inf)

    def add_fuel_producer_profile(self, profile: _FuelProducerProfile, idx: int | slice = np.s_[:]) -> None:
        """

        Parameters
        ----------
        profile : _PlantAggregateProfile | ProducerProfile
            Aggregate profile from other node.
        idx : int
            Time-step index.
        """

        for key in self._capacity_mass:
            self._capacity_mass[key][idx] += profile._capacity_mass[key][idx]

        for key in self._production_mass:
            self._production_mass[key][idx] += profile._production_mass[key][idx]

        for key in self._pipeline_capacity_mass:
            self._pipeline_capacity_mass[key][idx] += profile._pipeline_capacity_mass[key][idx]

        for key in self._pipeline_production_mass:
            self._pipeline_production_mass[key][idx] += profile._pipeline_production_mass[key][idx]

        for key in self._source_energy:
            self._source_energy[key][idx] += profile._source_energy[key][idx]

        for key in self._feed_mass:
            self._feed_mass[key][idx] += profile._feed_mass[key][idx]

        for key in self._feed_constraint:
            self._feed_constraint[key][idx] += profile._feed_constraint[key][idx]

    def add_capacity_mass(self, idx: int, fuel_name: str, mass: float) -> None:
        self._capacity_mass[fuel_name][idx] += mass

    def add_production_mass(self, idx: int, fuel_name: str, mass: float) -> None:
        self._production_mass[fuel_name][idx] += mass

    def add_pipeline_capacity_mass(self, idx: int, fuel_name: str, mass: float) -> None:
        self._pipeline_capacity_mass[fuel_name][idx] += mass

    def add_pipeline_production_mass(self, idx: int, fuel_name: str, mass: float) -> None:
        self._pipeline_production_mass[fuel_name][idx] += mass

    def add_source_energy(self, idx: int, source_name: str, energy: float) -> None:
        self._source_energy[source_name][idx] += energy

    def add_feed_mass(self, idx: int, feed_name: str, mass: float) -> None:
        self._feed_mass[feed_name][idx] += mass

    def set_feed_constraint(self, idx: int, feed_name: str, constraint: float) -> None:
        self._feed_constraint[feed_name][idx] = constraint

    def get_capacity_mass(self, fuel_name: str | None = None,
                          idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._capacity_mass, fuel_name, idx)

    def get_capacity_energy(self, fuel_name: str | None = None,
                            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._fuel_mass_to_energy(self._capacity_mass, fuel_name, idx)

    def get_capacity_volume(self, fuel_name: str | None = None,
                            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._fuel_mass_to_volume(self._capacity_mass, fuel_name, idx)

    def get_capacity_type_mass(self, idx: int | slice = np.s_[:]) -> dict[FuelTypeID, np.ndarray]:
        return self._fuel_type_mass_to_mass(self._capacity_mass, idx)

    def get_capacity_type_energy(self, idx: int | slice = np.s_[:]) -> dict[FuelTypeID, np.ndarray]:
        return self._fuel_type_mass_to_energy(self._capacity_mass, idx)

    def get_capacity_path_energy(self, idx: int | slice = np.s_[:]) -> dict[FuelTypeID, np.ndarray]:
        return self._fuel_type_mass_to_energy(self._capacity_mass, idx)

    def get_production_mass(self, fuel_name: str | None = None,
                            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._production_mass, fuel_name, idx)

    def get_production_energy(self, fuel_name: str | None = None,
                              idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._fuel_mass_to_energy(self._production_mass, fuel_name, idx)

    def get_production_volume(self, fuel_name: str | None = None,
                              idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._fuel_mass_to_volume(self._production_mass, fuel_name, idx)

    def get_production_type_mass(self, idx: int | slice = np.s_[:]) -> dict[FuelTypeID, np.ndarray]:
        return self._fuel_type_mass_to_mass(self._production_mass, idx)

    def get_production_type_energy(self, idx: int | slice = np.s_[:]) -> dict[FuelTypeID, np.ndarray]:
        return self._fuel_type_mass_to_energy(self._production_mass, idx)

    def get_pipeline_capacity_mass(self, fuel_name: str | None = None,
                                   idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._pipeline_capacity_mass, fuel_name, idx)

    def get_pipeline_capacity_energy(self, fuel_name: str | None = None,
                                     idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._fuel_mass_to_energy(self._pipeline_capacity_mass, fuel_name, idx)

    def get_pipeline_capacity_volume(self, fuel_name: str | None = None,
                                     idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._fuel_mass_to_volume(self._pipeline_capacity_mass, fuel_name, idx)

    def get_pipeline_capacity_type_mass(self, idx: int | slice = np.s_[:]) -> dict[FuelTypeID, np.ndarray]:
        return self._fuel_type_mass_to_mass(self._pipeline_capacity_mass, idx)

    def get_pipeline_capacity_type_energy(self, idx: int | slice = np.s_[:]) -> dict[FuelTypeID, np.ndarray]:
        return self._fuel_type_mass_to_energy(self._pipeline_capacity_mass, idx)

    def get_pipeline_capacity_path_energy(self, idx: int | slice = np.s_[:]) -> dict[FuelTypeID, np.ndarray]:
        return self._fuel_type_mass_to_energy(self._pipeline_capacity_mass, idx)

    def get_pipeline_production_mass(self, fuel_name: str | None = None,
                                     idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._pipeline_production_mass, fuel_name, idx)

    def get_pipeline_production_energy(self, fuel_name: str | None = None,
                                       idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._fuel_mass_to_energy(self._pipeline_production_mass, fuel_name, idx)

    def get_pipeline_production_volume(self, fuel_name: str | None = None,
                                       idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._fuel_mass_to_volume(self._pipeline_production_mass, fuel_name, idx)

    def get_pipeline_production_type_mass(self, idx: int | slice = np.s_[:]) -> dict[FuelTypeID, np.ndarray]:
        return self._fuel_type_mass_to_mass(self._pipeline_production_mass, idx)

    def get_pipeline_production_type_energy(self, idx: int | slice = np.s_[:]) -> dict[FuelTypeID, np.ndarray]:
        return self._fuel_type_mass_to_energy(self._pipeline_production_mass, idx)

    def get_source_energy(self, source_name: str | None = None,
                          idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._source_energy, source_name, idx)

    def get_feed_mass(self, feed_name: str | None = None,
                      idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._feed_mass, feed_name, idx)

    def get_feed_constraint(self, feedstock_name: str | None = None,
                            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._feed_constraint, feedstock_name, idx)
