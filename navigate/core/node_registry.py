# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass, field
from typing import Iterable

from navigate.bunker import BunkerLogistics, BunkerOptions
from navigate.calculator import Curve, Forecast, Surface, Timetable, Variable
from navigate.core import Node
from navigate.fuel import Emission, Feedstock, Fuel, Plant, Process, Producer, Region, Source, Transport
from navigate.model_definition import ModelDefinition
from navigate.output import Plot, Report
from navigate.policy import Levy, Regulation
from navigate.route import Port, Route
from navigate.vessel import Converter, PowerSystem, Tank, Technology, Vessel
from navigate.vessel.fleet import Fleet


@dataclass
class Nodes:
    converters:          dict[str, Converter] = field(default_factory=dict)
    curves:              dict[str, Curve] = field(default_factory=dict)
    emissions:           dict[str, Emission] = field(default_factory=dict)
    feedstocks:          dict[str, Feedstock] = field(default_factory=dict)
    fleets:              dict[str, Fleet] = field(default_factory=dict)
    forecasts:           dict[str, Forecast] = field(default_factory=dict)
    fuels:               dict[str, Fuel] = field(default_factory=dict)
    levies:              dict[str, Levy] = field(default_factory=dict)
    plants:              dict[str, Plant] = field(default_factory=dict)
    plots:               dict[str, Plot] = field(default_factory=dict)
    ports:               dict[str, Port] = field(default_factory=dict)
    power_systems:       dict[str, PowerSystem] = field(default_factory=dict)
    processes:           dict[str, Process] = field(default_factory=dict)
    producers:           dict[str, Producer] = field(default_factory=dict)
    regions:             dict[str, Region] = field(default_factory=dict)
    regulations:         dict[str, Regulation] = field(default_factory=dict)
    reports:             dict[str, Report] = field(default_factory=dict)
    routes:              dict[str, Route] = field(default_factory=dict)
    sources:             dict[str, Source] = field(default_factory=dict)
    surfaces:            dict[str, Surface] = field(default_factory=dict)
    tanks:               dict[str, Tank] = field(default_factory=dict)
    technologies:        dict[str, Technology] = field(default_factory=dict)
    timetables:          dict[str, Timetable] = field(default_factory=dict)
    transports:          dict[str, Transport] = field(default_factory=dict)
    variables:           dict[str, Variable] = field(default_factory=dict)
    vessels:             dict[str, Vessel] = field(default_factory=dict)

    def all_groups(self) -> list[dict[str, Node]]:
        return [
            self.converters, self.curves,
            self.emissions, self.feedstocks, self.fleets, self.forecasts,
            self.fuels, self.levies, self.plants, self.plots, self.ports, self.power_systems, self.processes,
            self.producers, self.regions, self.regulations, self.reports, self.routes, self.sources,
            self.surfaces, self.tanks, self.technologies, self.timetables, self.transports, self.variables,
            self.vessels
        ]

    def all_nodes(self) -> Iterable[Node]:
        for g in self.all_groups():
            yield from g.values()

    def all_names(self) -> Iterable[str]:
        for g in self.all_groups():
            yield from g.keys()


@dataclass
class GeneralNodes:
    bunker_logistics:   BunkerLogistics | None = None
    bunker_options:     BunkerOptions | None = None
    model_definition:   ModelDefinition | None = None
