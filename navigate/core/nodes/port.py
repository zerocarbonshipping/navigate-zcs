# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core import (
    Scalar,
    as_scalar,
    assign_value,
    command_assignment_to_boolean_dict,
    command_assignment_to_dict,
    command_assignment_to_tuple_dict,
)
from navigate.core.expectations import PortExpectation
from navigate.core.node import Node
from navigate.core.node_type import FORECAST, PORT, VARIABLE
from navigate.core.profiles import PortProfile
from navigate.core.unit import MWH_TO_GJ

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel

logger = logging.getLogger(__name__)


class Port(Node):
    def __init__(self, name):
        super().__init__(name)

        self.type = PORT

        # external properties ------------------------------------------------------------------------------------------
        # bunkering
        self.bunkering_allowed = {}    # dict[bool], whether bunkering of a fuel is allowed
        self.bunkering_limit = {}      # dict[float], maximum achievable bunkering of a fuel in the port, ton/year
        self.bunkering_inertia = {}    # dict[float], fraction of bunkering of a fuel that must occur in next year

        # fuel handling
        self.handling_cost = {}        # dict[float], costs related to storage and the service of bunkering, USD/ton

        # bunker overwrite
        self.liquid_market_fuel = {}       # dict[bool], whether a fuel belongs to a liquid market
        self.bunker_price_overwrite = {}   # dict[float], manual bunker price, overwrites production, USD/ton
        self.bunker_WTT_overwrite = {}     # dict[float], manual bunker WTT, overwrites production, USD/ton

        # shore power
        self.shore_power_cost: Scalar | None = None               # USD/GJ (stored internally, input in USD/MWh)
        self.shore_power_connection_share: Scalar | None = None   # fraction [0,1]
        self.shore_power_emission_factor = {}                     # dict[emission_name: Scalar], ton/GJ (internal)

    # external commands called in the input deck -----------------------------------------------------------------------
    def set_bunkering_allowed(self, fuel_name, value):
        """
        Set whether it is allowed to bunker a specific fuel in the port.

        Examples
        --------
        - "fuel_name", TRUE
        - "fuel_name", FALSE

        Parameters
        ----------
        fuel_name : str
            The name of a fuel.
        value : str
            Whether the fuel is allowed to be bunkered in the port.
        """

        command_assignment_to_boolean_dict(fuel_name, value, self.bunkering_allowed)

    def set_bunkering_limit(self, fuel_name, value):
        """
        Set a limitation for the amount of fuel that can be bunkered in the port in tons/year.

        Examples
        --------
        - "fuel_name", 1e6
        - "fuel_name", Forecast("name")

        Parameters
        ----------
        fuel_name : str
            The name of a fuel.
        value : float | NodeReference
            The amount of fuel available for bunkering in tons/year.
        """

        command_assignment_to_dict(fuel_name, value, self.bunkering_limit, type_=(FORECAST, VARIABLE), lower=0.)

    def set_bunkering_inertia(self, fuel_name, value):
        """
        Set the inertia of a fuel being bunkered in fraction/year.

        The inertia refers to the fraction of the amount bunkered in the previous time-step that must at minimum be
        bunkered in the current time-step.

        Examples
        --------
        - "fuel_name", 0.66
        - "fuel_name", Forecast("name")

        Parameters
        ----------
        fuel_name : str
            The name of a fuel.
        value : float | NodeReference
            The inertia of the bunkering of the fuel.
        """

        command_assignment_to_dict(fuel_name, value, self.bunkering_inertia, type_=(FORECAST, VARIABLE), lower=0., upper=1.)

    def set_handling_cost(self, fuel_name, value):
        """
        Set the costs related to storage and the service of bunkering of a specific fuel in the port in USD/ton.

        Examples
        --------
        - "fuel_name", 50
        - "fuel_name", Forecast("name")

        Parameters
        ----------
        fuel_name : str
            The name of a fuel.
        value : float | NodeReference
            The cost of storage and the service of bunkering a specific fuel in the port in USD/ton.
        """

        command_assignment_to_dict(fuel_name, value, self.handling_cost, type_=(FORECAST, VARIABLE), lower=0.)

    def set_bunker_price_overwrite(self, fuel_name, value):
        """
        Set an overwrite cost for a specific fuel in the port in USD/ton.

        If an overwrite is set for a specific fuel, then the bottom-up calculation of production cost is ignored.

        Examples
        --------
        - "fuel_name", 600
        - "fuel_name", Forecast("name")

        Parameters
        ----------
        fuel_name : str
            The name of a fuel.
        value : float | NodeReference
            The overwrite price of a specific fuel in the port in USD/ton.
        """

        command_assignment_to_dict(fuel_name, value, self.bunker_price_overwrite, type_=(FORECAST, VARIABLE), lower=0.)

    def set_bunker_wtt_overwrite(self, fuel_name, emission_name, value):
        """
        Set an overwrite WTT emissions for a specific fuel and emission in the port in ton emission/ton fuel.

        If an overwrite is set for a specific fuel and emission, then the bottom-up calculation of production emissions
        is ignored.

        Examples
        --------
        - "fuel_name", "emission_name", 600
        - "fuel_name", "emission_name", Forecast("name")

        Parameters
        ----------
        fuel_name : str
            The name of a fuel.
        emission_name : str
            The name of an emission.
        value : float | NodeReference
            The overwrite price of a specific fuel in the port in USD/ton.
        """

        command_assignment_to_tuple_dict((fuel_name, emission_name),
                                         value,
                                         self.bunker_WTT_overwrite,
                                         type_=(FORECAST, VARIABLE))

    def set_shore_power_cost(self, value):
        """
        Set the shore power electricity tariff in USD/MWh.

        Internally converted to USD/GJ for consistency with the energy model.

        Examples
        --------
        - 80
        - Forecast("shore_power_cost_europe")

        Parameters
        ----------
        value : float | NodeReference
            Shore power cost in USD/MWh.
        """

        self.shore_power_cost = assign_value(as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.)

    def set_shore_power_connection_share(self, value):
        """
        Set the fraction of port time during which shore power connection is available.

        A value of 0.0 (the default) means shore power is not available at this port.

        Examples
        --------
        - 0.8
        - Forecast("shore_power_connection_share")

        Parameters
        ----------
        value : float | NodeReference
            Fraction of port time with shore power connection [0, 1].
        """

        self.shore_power_connection_share = assign_value(as_scalar(value), type_=(FORECAST, VARIABLE),
                                                         lower=0., upper=1.)

    def set_shore_power_emission_factor(self, emission_name, value):
        """
        Set the WTW emission factor for shore power grid electricity in ton emission/MWh.

        Internally converted to ton/GJ.

        Examples
        --------
        - "carbon_dioxide", 0.180
        - "carbon_dioxide", Forecast("grid_emission_factor")

        Parameters
        ----------
        emission_name : str
            Name of the emission.
        value : float | NodeReference
            Emission factor in ton emission/MWh.
        """

        command_assignment_to_dict(emission_name, value, self.shore_power_emission_factor,
                                   type_=(FORECAST, VARIABLE), lower=0.)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):

        for fuel_name in self.bunkering_allowed:
            if self.bunkering_allowed[fuel_name] is None:
                self.bunkering_allowed[fuel_name] = True

        for fuel_name in self.bunkering_inertia:
            if self.bunkering_inertia[fuel_name] is None:
                self.bunkering_inertia[fuel_name] = Scalar(0.)

        for fuel_name in self.handling_cost:
            if self.handling_cost[fuel_name] is None:
                self.handling_cost[fuel_name] = Scalar(0.)

        for fuel_name, price in self.bunker_price_overwrite.items():
            if (price is None) and self.liquid_market_fuel[fuel_name]:
                self.bunker_price_overwrite[fuel_name] = Scalar(0.)

        for (fuel_name, emission_name), WTT in self.bunker_WTT_overwrite.items():
            if (WTT is None) and self.liquid_market_fuel[fuel_name]:
                self.bunker_WTT_overwrite[(fuel_name, emission_name)] = Scalar(0.)

        # shore power defaults
        if self.shore_power_cost is None:
            self.shore_power_cost = Scalar(0.)

        if self.shore_power_connection_share is None:
            self.shore_power_connection_share = Scalar(0.)

        for emission_name in self.shore_power_emission_factor:
            if self.shore_power_emission_factor[emission_name] is None:
                self.shore_power_emission_factor[emission_name] = Scalar(0.)

    def initialize_dependencies(self, emissions, fuels):
        """
        Initialize dependent dictionaries to allow wildcarding during command calls.

        Parameters
        ----------
        emissions : dict[str, Emission]
            All emissions in the simulation.
        fuels : dict[str, Fuel]
            All fuels in the simulation.
        """

        for fuel_name in fuels:

            self.bunkering_allowed.setdefault(fuel_name, None)
            self.bunkering_limit.setdefault(fuel_name, None)
            self.bunkering_inertia.setdefault(fuel_name, None)

            self.handling_cost.setdefault(fuel_name, None)
            self.bunker_price_overwrite.setdefault(fuel_name, None)

            for emission_name in emissions:
                self.bunker_WTT_overwrite.setdefault((fuel_name, emission_name), None)

        for emission_name in emissions:
            self.shore_power_emission_factor.setdefault(emission_name, None)

        # set internal property
        self.liquid_market_fuel = {fuel_name: fuel.belongs_to_liquid_market() for fuel_name, fuel in fuels.items()}

    def initialize_expectation(self, length: int, fuels: dict[str, Fuel],
                               emissions: dict[str, Emission]) -> None:

        self.expectation = PortExpectation()
        self.expectation.initialize(length, fuels, emissions)

    def initialize_profile(self, timeline: np.ndarray, emissions: dict[str, Emission],
                           fuels: dict[str, Fuel], lifetime: float) -> None:
        """

        Parameters
        ----------
        timeline : np.ndarray
            Simulation timeline in years.
        fuels : dict[Fuel]
            All fuels in the simulation.
        emissions : dict[Emission]
            Dict of class Emission.
        lifetime : float
            GWP lifetime.
        """

        self.profile = PortProfile()
        self.profile.initialize(timeline, emissions, fuels, lifetime)

    def calculate_expectation(self, timeline, idx):

        times = timeline[idx:]

        for fuel_name, limit in self.bunkering_limit.items():

            if limit is not None:

                self.expectation.set_bunkering_limit(idx, fuel_name, limit.get(times))

        for fuel_name, handling_cost in self.handling_cost.items():

            if handling_cost is not None:

                self.expectation.set_handling_cost(idx, fuel_name, handling_cost.get(times))

        for fuel_name, overwrite in self.bunker_price_overwrite.items():

            if overwrite is not None:

                self.expectation.set_bunker_price_overwrite(idx, fuel_name, overwrite.get(times))

        for (fuel_name, emission_name), overwrite in self.bunker_WTT_overwrite.items():

            if overwrite is not None:

                self.expectation.set_bunker_WTT_overwrite(idx, fuel_name, emission_name, overwrite.get(times))

        # shore power (convert from USD/MWh to USD/GJ, and ton/MWh to ton/GJ)
        self.expectation.set_shore_power_cost(idx, self.shore_power_cost.get(times) / MWH_TO_GJ)
        self.expectation.set_shore_power_connection_share(idx, self.shore_power_connection_share.get(times))

        for emission_name, ef in self.shore_power_emission_factor.items():
            if ef is not None:
                self.expectation.set_shore_power_emission_factor(idx, emission_name, ef.get(times) / MWH_TO_GJ)

    def calculate_profile(self, idx):

        for fuel_name, available in self.bunkering_allowed.items():
            self.profile.set_bunkering_allowed(idx, fuel_name, available)

        for fuel_name, limit in self.bunkering_limit.items():

            if limit is not None:

                self.profile.set_bunkering_limit_mass(idx, fuel_name, limit.get())

    def is_bunkering_allowed(self, fuel_name):
        """

        Parameters
        ----------
        fuel_name : str
            Name of fuel.

        Returns
        -------
        bool
            Whether fuel can be bunkered at the current time-step
        """

        return self.bunkering_allowed[fuel_name]
