# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.misc import EMPTY_FLOAT, EMPTY_NAN
from navigate.core.profiles._plant_aggregate_profile import _PlantAggregateProfile
from navigate.util import extract_from_dict

if TYPE_CHECKING:
    from navigate.fuel import Fuel
    from navigate.fuel.feedstock import Feedstock
    from navigate.fuel.process import Process
    from navigate.fuel.region import Region
    from navigate.fuel.source import Source


class ProducerProfile(_PlantAggregateProfile):
    def __init__(self):
        super().__init__()

        self._existing_plants: dict[str, np.ndarray] = {}
        self._average_ages: dict[str, np.ndarray] = {}
        self._decommissions: dict[str, np.ndarray] = {}
        self._newbuilds: dict[str, np.ndarray] = {}

        self._pipeline: dict[str, np.ndarray] = {}
        self._pipeline_additions: dict[str, np.ndarray] = {}

        self._maximum_development: np.ndarray = EMPTY_NAN
        self._development: np.ndarray = EMPTY_FLOAT

        self._fair_share_fuel_fraction: dict[str, np.ndarray] = {}  # fraction of fair-share going to the specific producer

    def initialize(self, timeline: np.ndarray, plant_names: list[str],
                   feedstocks: dict[str, Feedstock], fuels: dict[str, Fuel],
                   processes: dict[str, Process], regions: dict[str, Region],
                   sources: dict[str, Source]) -> None:
        """

        Parameters
        ----------
        timeline : np.ndarray
            Simulation timeline in years.
        plant_names : list[str]
            List of plant names assigned to the producer.
        feedstocks : dict[Feedstock]
            All feedstocks in the simulation.
        fuels : dict[Fuel]
            All fuels in the simulation.
        sources : dict[Source]
            All sources in the simulation

        """

        self._initialize_base(timeline)
        self._initialize_fuel_base(fuels)
        self._initialize_fuel_producer(feedstocks, fuels, processes, sources)
        self._initialize_plant_aggregate(fuels)

        self._existing_plants = self._default_dict(plant_names)
        self._average_ages = self._default_dict(plant_names)
        self._decommissions = self._default_dict(plant_names)
        self._newbuilds = self._default_dict(plant_names)

        self._pipeline = self._default_dict(plant_names)
        self._pipeline_additions = self._default_dict(plant_names)

        self._maximum_development = self._default_array(default=np.nan)
        self._development = self._default_array()

        self._fair_share_fuel_fraction = self._default_dict(fuels)

    def set_existing_plants(self, idx: int, plant_name: str, existing_plants: float) -> None:
        self._existing_plants[plant_name][idx] = existing_plants

    set_existing_assets = set_existing_plants

    def set_average_age(self, idx: int, plant_name: str, average_age: float) -> None:
        self._average_ages[plant_name][idx] = average_age

    def set_decommission(self, idx: int, plant_name: str, decommissioning: float) -> None:
        self._decommissions[plant_name][idx] = decommissioning

    def set_newbuild(self, idx: int, plant_name: str, newbuilds: float) -> None:
        self._newbuilds[plant_name][idx] = newbuilds

    def set_pipeline(self, idx: int, plant_name: str, pipeline: float) -> None:
        self._pipeline[plant_name][idx] = pipeline

    def set_pipeline_additions(self, idx: int, plant_name: str, pipeline_additions: float) -> None:
        self._pipeline_additions[plant_name][idx] = pipeline_additions

    def set_maximum_development(self, idx: int, development_constraint: float) -> None:
        self._maximum_development[idx] = development_constraint

    def set_development(self, idx: int, development: float) -> None:
        self._development[idx] = development

    def set_fair_share_fuel_fraction(self, idx: int, fuel_name: str, fair_share: float) -> None:
        self._fair_share_fuel_fraction[fuel_name][idx] = fair_share

    def get_existing_plants(
            self, plant_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._existing_plants, plant_name, idx)

    def get_average_age(self, plant_name: str | None = None, idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._average_ages, plant_name, idx)

    def get_decommissions(
            self, plant_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._decommissions, plant_name, idx)

    def get_newbuilds(self, plant_name: str | None = None, idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._newbuilds, plant_name, idx)

    def get_total_decommissions(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._get_total_method(self.get_decommissions, idx)

    def get_total_newbuilds(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._get_total_method(self.get_newbuilds, idx)

    def get_pipeline(self, plant_name: str | None = None, idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._pipeline, plant_name, idx)

    def get_pipeline_additions(
            self, plant_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._pipeline_additions, plant_name, idx)

    def get_maximum_development(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._maximum_development[idx]

    def get_development(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._development[idx]

    def get_cumulative_maximum_development(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._to_cumulative(self._maximum_development[idx])

    def get_cumulative_development(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._to_cumulative(self._development[idx])

    def get_fair_share_fuel_fraction(
            self, fuel_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._fair_share_fuel_fraction, fuel_name, idx)
