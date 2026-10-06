# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Fuel node, a fuel's type, physical properties and TTW emissions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    Scalar,
    as_scalar,
    assign_boolean,
    assign_id,
    assign_value,
    write_matching_keys,
)
from navigate.core.enum_ import FuelTypeID
from navigate.core.node import Node
from navigate.core.node_type import FUEL, VARIABLE

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.types_ import ScalarArgument, ScalarInput


class Fuel(Node):
    """A fuel: its type, market, heating value, density and TTW emission factors."""

    def __init__(self, name: str) -> None:
        super().__init__(name, FUEL)

        # external variables -----------------------------------------------------------
        # definition
        self.fuel_type: FuelTypeID
        self.liquid_market: bool = False

        # physical properties
        self.lower_heating_value: ScalarInput
        self.mass_density: ScalarInput

        # emissions
        self.ttw: dict[str, ScalarInput] = {}

    # external methods (DSL attributes) ------------------------------------------------
    def set_fuel_type(self, fuel_type: str) -> None:
        """
        Set the fuel type of the fuel.

        Examples
        --------
        - OIL
        - AMMONIA
        - METHANOL

        Parameters
        ----------
        fuel_type
            Type of fuel.
        """
        self.fuel_type = assign_id(fuel_type, FuelTypeID)

    def set_liquid_market(self, liquid_market: str) -> None:
        """
        Set the flag for whether the fuel belongs to a liquid market.

        Fuels which belong to a liquid market cannot be modelled bottom-up via Plant and
        Producer nodes but require manual assignment of supply, price, and WTT emissions
        at Port level.

        Examples
        --------
        - TRUE
        - FALSE

        Parameters
        ----------
        liquid_market
            Whether the fuel belongs to a liquid market.
        """
        self.liquid_market = assign_boolean(liquid_market)

    def set_lower_heating_value(self, lower_heating_value: ScalarArgument) -> None:
        """
        Set the lower heating value of the fuel in GJ/ton.

        Examples
        --------
        - 42.6

        Parameters
        ----------
        lower_heating_value
            The lower heating value of the fuel in GJ/ton.
        """
        self.lower_heating_value = assign_value(
            as_scalar(lower_heating_value), type_=VARIABLE, lower=0.0
        )

    def set_mass_density(self, mass_density: ScalarArgument) -> None:
        """
        Set the mass density of the fuel in ton/m3.

        Examples
        --------
        - 0.96

        Parameters
        ----------
        mass_density
            The mass density of the fuel in ton/m3.
        """
        self.mass_density = assign_value(
            as_scalar(mass_density), type_=VARIABLE, lower=0.0
        )

    # external methods (DSL commands) --------------------------------------------------
    def set_ttw(self, emission_name: str, ttw: ScalarArgument) -> None:
        """
        Set the TTW emission factor for the stoichiometric conversion of fuel to energy.

        Only allowed in the DEFINE section.

        Examples
        --------
        - "emission_name", 2.75
        - "emission_name", Variable("name")

        Parameters
        ----------
        emission_name
            Name of emission emitted.
        ttw
            Ton of emissions per ton of fuel.
        """
        write_matching_keys(
            emission_name,
            assign_value(as_scalar(ttw), type_=VARIABLE, lower=0.0),
            self.ttw,
        )

    # internal methods -----------------------------------------------------------------
    def check_consistency(self) -> None:

        if self.lower_heating_value.get() == 0.0:
            raise ValueError(
                f"{self}: Attribute 'LowerHeatingValue' must be greater than zero."
            )

        if self.mass_density.get() == 0.0:
            raise ValueError(
                f"{self}: Attribute 'MassDensity' must be greater than zero."
            )

    def initialize_dependencies(self, emissions: dict[str, Emission]) -> None:
        """
        Initialize dependent dictionaries to allow wildcarding during command calls.

        Parameters
        ----------
        emissions
            All emissions in the simulation.
        """
        for emission_name in emissions:
            self.ttw.setdefault(emission_name, Scalar(0.0))
