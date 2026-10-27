# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Fuel node, a fuel's type, physical properties and TTW emissions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    SECTION_DEFINE,
    Scalar,
    as_scalar,
    assign_boolean,
    assign_id,
    assign_value,
    deck_attribute,
    deck_command,
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

    type = FUEL

    def __init__(self, name: str) -> None:
        super().__init__(name)

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
    @deck_attribute(SECTION_DEFINE, required=True)
    def set_fuel_type(self, fuel_type: str) -> None:
        """Set the fuel type of the fuel."""
        self.fuel_type = assign_id(fuel_type, FuelTypeID)

    @deck_attribute(SECTION_DEFINE)
    def set_liquid_market(self, liquid_market: str) -> None:
        """Set whether the fuel belongs to a liquid market."""
        self.liquid_market = assign_boolean(liquid_market)

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_lower_heating_value(self, lower_heating_value: ScalarArgument) -> None:
        """Set the lower heating value of the fuel."""
        self.lower_heating_value = assign_value(
            as_scalar(lower_heating_value),
            type_=VARIABLE,
            lower=0.0,
            inclusive_lower=False,
        )

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_mass_density(self, mass_density: ScalarArgument) -> None:
        """Set the mass density of the fuel."""
        self.mass_density = assign_value(
            as_scalar(mass_density),
            type_=VARIABLE,
            lower=0.0,
            inclusive_lower=False,
        )

    # external methods (DSL commands) --------------------------------------------------
    @deck_command(SECTION_DEFINE)
    def set_ttw(self, emission_name: str, ttw: ScalarArgument) -> None:
        """Set the TTW emission factor of the fuel for an emission."""
        write_matching_keys(
            emission_name,
            assign_value(as_scalar(ttw), type_=VARIABLE, lower=0.0),
            self.ttw,
        )

    # internal methods -----------------------------------------------------------------
    def initialize_dependencies(self, emissions: dict[str, Emission]) -> None:
        """
        Initialize dependent dictionaries to allow wildcarding in command calls.

        Parameters
        ----------
        emissions
            All emissions in the simulation.
        """
        for emission_name in emissions:
            self.ttw.setdefault(emission_name, Scalar(0.0))
