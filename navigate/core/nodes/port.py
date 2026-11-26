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
from navigate.core.enum_ import NodeTypeID
from navigate.core.expectations import PortExpectation
from navigate.core.node import Node
from navigate.core.results import PortResults

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.levy import Levy
    from navigate.core.results import ResultsContext
    from navigate.core.types_ import ForecastArgument, ForecastInput


class Port(Node):
    """A port: the fuels bunkered there, their limits and costs, and shore power."""

    type = NodeTypeID.PORT

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # external variables -----------------------------------------------------------
        # shore power
        self.shore_power_price: ForecastInput = Scalar(0.0)
        self.shore_power_availability: ForecastInput = Scalar(0.0)

        # bunkering
        self.allow_bunkering: dict[str, bool] = {}
        self.bunkering_limits: dict[str, ForecastInput | None] = {}
        self.bunkering_inertia: dict[str, ForecastInput] = {}

        # fuel handling
        self.handling_costs: dict[str, ForecastInput] = {}

        # fuel prices and WTT
        self.fuel_prices: dict[str, ForecastInput | None] = {}
        self.fuel_wtt: dict[tuple[str, str], ForecastInput | None] = {}

        # shore power emissions
        self.shore_power_wtt: dict[str, ForecastInput] = {}

        # internal variables -----------------------------------------------------------
        self.expectation: PortExpectation
        self.results: PortResults = PortResults()

        self.liquid_market_fuel: dict[str, bool] = {}
        self.imposed_levies: list[Levy]

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute()
    def set_shore_power_price(self, value: ForecastArgument) -> None:
        """Set the shore power electricity price of the port."""
        self.shore_power_price = assign_value(
            as_scalar(value),
            type_=(NodeTypeID.FORECAST, NodeTypeID.VARIABLE),
            lower=0.0,
        )

    @deck_attribute()
    def set_shore_power_availability(self, value: ForecastArgument) -> None:
        """Set the fraction of port time with a shore power connection."""
        self.shore_power_availability = assign_value(
            as_scalar(value),
            type_=(NodeTypeID.FORECAST, NodeTypeID.VARIABLE),
            lower=0.0,
            upper=1.0,
        )

    # external methods (DSL commands) --------------------------------------------------
    @deck_command()
    def set_allow_bunkering(self, key: str, value: str) -> None:
        """Set whether a fuel may be bunkered in the port."""
        write_matching_keys(key, assign_boolean(value), self.allow_bunkering)

    @deck_command()
    def set_bunkering_limit(self, key: str, value: ForecastArgument) -> None:
        """Set the limit on the amount of a fuel bunkered in the port."""
        write_matching_keys(
            key,
            assign_value(
                as_scalar(value),
                type_=(NodeTypeID.FORECAST, NodeTypeID.VARIABLE),
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
                as_scalar(value),
                type_=(NodeTypeID.FORECAST, NodeTypeID.VARIABLE),
                lower=0.0,
                upper=1.0,
            ),
            self.bunkering_inertia,
        )

    @deck_command()
    def set_handling_cost(self, key: str, value: ForecastArgument) -> None:
        """Set the storage and bunkering service cost of a fuel in the port."""
        write_matching_keys(
            key,
            assign_value(
                as_scalar(value),
                type_=(NodeTypeID.FORECAST, NodeTypeID.VARIABLE),
                lower=0.0,
            ),
            self.handling_costs,
        )

    @deck_command()
    def set_fuel_price(self, key: str, value: ForecastArgument) -> None:
        """Set the price of a fuel in the port."""
        write_matching_keys(
            key,
            assign_value(
                as_scalar(value),
                type_=(NodeTypeID.FORECAST, NodeTypeID.VARIABLE),
                lower=0.0,
            ),
            self.fuel_prices,
        )

    @deck_command()
    def set_fuel_wtt(self, key1: str, key2: str, value: ForecastArgument) -> None:
        """Set the WTT emissions of a fuel in the port for an emission."""
        write_matching_key_pairs(
            (key1, key2),
            assign_value(
                as_scalar(value), type_=(NodeTypeID.FORECAST, NodeTypeID.VARIABLE)
            ),
            self.fuel_wtt,
        )

    @deck_command()
    def set_shore_power_wtt(self, key: str, value: ForecastArgument) -> None:
        """Set the WTT emissions of shore power for an emission."""
        write_matching_keys(
            key,
            assign_value(
                as_scalar(value),
                type_=(NodeTypeID.FORECAST, NodeTypeID.VARIABLE),
                lower=0.0,
            ),
            self.shore_power_wtt,
        )

    # internal methods -----------------------------------------------------------------
    def apply_command_defaults(self) -> None:
        # a liquid-market fuel has no bottom-up production chain to price it, so its
        # entry is filled; any other fuel keeps None, which is what selects the
        # bottom-up calculation
        for fuel_name, price in self.fuel_prices.items():
            if (price is None) and self.liquid_market_fuel[fuel_name]:
                self.fuel_prices[fuel_name] = Scalar(0.0)

        for (fuel_name, emission_name), wtt in self.fuel_wtt.items():
            if (wtt is None) and self.liquid_market_fuel[fuel_name]:
                self.fuel_wtt[(fuel_name, emission_name)] = Scalar(0.0)

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
        # a None limit is unlimited, and a None price or WTT selects the bottom-up
        # calculation
        for fuel_name in fuels:
            self.allow_bunkering.setdefault(fuel_name, True)
            self.bunkering_limits.setdefault(fuel_name, None)
            self.bunkering_inertia.setdefault(fuel_name, Scalar(0.0))

            self.handling_costs.setdefault(fuel_name, Scalar(0.0))

            self.fuel_prices.setdefault(fuel_name, None)

            for emission_name in emissions:
                self.fuel_wtt.setdefault((fuel_name, emission_name), None)

        for emission_name in emissions:
            self.shore_power_wtt.setdefault(emission_name, Scalar(0.0))

        # derived from the current fuels, so recomputed unconditionally every pass
        self.liquid_market_fuel = {
            fuel_name: fuel.liquid_market for fuel_name, fuel in fuels.items()
        }

    def initialize_expectation(
        self, length: int, fuels: dict[str, Fuel], emissions: dict[str, Emission]
    ) -> None:
        self.expectation = PortExpectation(length, fuels, emissions)

    def initialize_results(self, context: ResultsContext) -> None:
        self.results.initialize(context)
