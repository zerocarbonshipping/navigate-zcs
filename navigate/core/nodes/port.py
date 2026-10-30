# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Port node, where vessels bunker fuel and connect to shore power."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    Scalar,
    as_scalar,
    assign_boolean,
    assign_value,
    deck_attribute,
    deck_command,
    write_matching_key_pairs,
    write_matching_keys,
)
from navigate.core.expectations import PortExpectation
from navigate.core.node import Node
from navigate.core.node_type import FORECAST, PORT, VARIABLE
from navigate.core.results import PortResults

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.levy import Levy
    from navigate.core.results import ResultsContext
    from navigate.core.types_ import ForecastArgument, ForecastInput


class Port(Node):
    """A port: the fuels bunkered there, their limits and costs, and shore power."""

    type = PORT

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # external variables -----------------------------------------------------------
        # shore power
        self.shore_power_cost: ForecastInput = Scalar(0.0)
        self.shore_power_connection_share: ForecastInput = Scalar(0.0)

        # bunkering
        self.bunkering_allowed: dict[str, bool] = {}
        self.bunkering_limits: dict[str, ForecastInput | None] = {}
        self.bunkering_inertia: dict[str, ForecastInput] = {}

        # fuel handling
        self.handling_costs: dict[str, ForecastInput] = {}

        # bunker overwrites
        self.bunker_price_overwrites: dict[str, ForecastInput | None] = {}
        self.bunker_wtt_overwrites: dict[tuple[str, str], ForecastInput | None] = {}

        # shore power emissions
        self.shore_power_emission_factors: dict[str, ForecastInput] = {}

        # internal variables -----------------------------------------------------------
        self.expectation: PortExpectation = PortExpectation()
        self.results: PortResults = PortResults()

        self.liquid_market_fuel: dict[str, bool] = {}
        self.imposed_levies: list[Levy]

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute()
    def set_shore_power_cost(self, value: ForecastArgument) -> None:
        """Set the shore power electricity tariff of the port."""
        self.shore_power_cost = assign_value(
            as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0
        )

    @deck_attribute()
    def set_shore_power_connection_share(self, value: ForecastArgument) -> None:
        """Set the fraction of port time with a shore power connection."""
        self.shore_power_connection_share = assign_value(
            as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
        )

    # external methods (DSL commands) --------------------------------------------------
    @deck_command()
    def set_bunkering_allowed(self, key: str, value: str) -> None:
        """Set whether a fuel may be bunkered in the port."""
        write_matching_keys(key, assign_boolean(value), self.bunkering_allowed)

    @deck_command()
    def set_bunkering_limit(self, key: str, value: ForecastArgument) -> None:
        """Set the limit on the amount of a fuel bunkered in the port."""
        write_matching_keys(
            key,
            assign_value(
                as_scalar(value),
                type_=(FORECAST, VARIABLE),
                lower=0.0,
                allow_infinite=True,
            ),
            self.bunkering_limits,
        )

    @deck_command()
    def set_bunkering_inertia(self, key: str, value: ForecastArgument) -> None:
        """Set the bunkering inertia of a fuel in the port."""
        write_matching_keys(
            key,
            assign_value(
                as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
            ),
            self.bunkering_inertia,
        )

    @deck_command()
    def set_handling_cost(self, key: str, value: ForecastArgument) -> None:
        """Set the storage and bunkering service cost of a fuel in the port."""
        write_matching_keys(
            key,
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0),
            self.handling_costs,
        )

    @deck_command()
    def set_bunker_price_overwrite(self, key: str, value: ForecastArgument) -> None:
        """Set the overwrite price of a fuel in the port."""
        write_matching_keys(
            key,
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0),
            self.bunker_price_overwrites,
        )

    @deck_command()
    def set_bunker_wtt_overwrite(
        self, key1: str, key2: str, value: ForecastArgument
    ) -> None:
        """Set the overwrite WTT emissions of a fuel in the port for an emission."""
        write_matching_key_pairs(
            (key1, key2),
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE)),
            self.bunker_wtt_overwrites,
        )

    @deck_command()
    def set_shore_power_emission_factor(
        self, key: str, value: ForecastArgument
    ) -> None:
        """Set the shore power emission factor for an emission."""
        write_matching_keys(
            key,
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0),
            self.shore_power_emission_factors,
        )

    # internal methods -----------------------------------------------------------------
    def apply_command_defaults(self) -> None:
        # a liquid-market fuel has no bottom-up production chain to price it, so its
        # entry is filled; any other fuel keeps None, which is what selects the
        # bottom-up calculation
        for fuel_name, price in self.bunker_price_overwrites.items():
            if (price is None) and self.liquid_market_fuel[fuel_name]:
                self.bunker_price_overwrites[fuel_name] = Scalar(0.0)

        for (fuel_name, emission_name), wtt in self.bunker_wtt_overwrites.items():
            if (wtt is None) and self.liquid_market_fuel[fuel_name]:
                self.bunker_wtt_overwrites[(fuel_name, emission_name)] = Scalar(0.0)

    def initialize_dependencies(
        self, emissions: dict[str, Emission], fuels: dict[str, Fuel]
    ) -> None:
        """
        Initialize dependent dictionaries to allow wildcarding in command calls.

        Parameters
        ----------
        emissions
            All emissions in the simulation.
        fuels
            All fuels in the simulation.
        """
        # a None limit is unlimited, a None overwrite selects the bottom-up calculation
        for fuel_name in fuels:
            self.bunkering_allowed.setdefault(fuel_name, True)
            self.bunkering_limits.setdefault(fuel_name, None)
            self.bunkering_inertia.setdefault(fuel_name, Scalar(0.0))

            self.handling_costs.setdefault(fuel_name, Scalar(0.0))

            self.bunker_price_overwrites.setdefault(fuel_name, None)

            for emission_name in emissions:
                self.bunker_wtt_overwrites.setdefault((fuel_name, emission_name), None)

        for emission_name in emissions:
            self.shore_power_emission_factors.setdefault(emission_name, Scalar(0.0))

        # derived from the current fuels, so recomputed unconditionally every pass
        self.liquid_market_fuel = {
            fuel_name: fuel.liquid_market for fuel_name, fuel in fuels.items()
        }

    def initialize_expectation(
        self, length: int, fuels: dict[str, Fuel], emissions: dict[str, Emission]
    ) -> None:
        self.expectation.initialize(length, fuels, emissions)

    def initialize_results(self, context: ResultsContext) -> None:
        self.results.initialize(context)
