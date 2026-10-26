# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Converter node, machinery turning fuel into usable energy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    SECTION_DEFINE,
    Scalar,
    as_scalar,
    assign_id_list,
    assign_member,
    assign_value,
    deck_attribute,
    deck_command,
    write_matching_key_pairs,
    write_matching_keys,
)
from navigate.core.enum_ import FuelTypeID
from navigate.core.node_type import CONVERTER, FORECAST, VARIABLE
from navigate.core.nodes._machinery import _Machinery

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.types_ import (
        ForecastArgument,
        ForecastInput,
        ScalarArgument,
        ScalarInput,
    )


class Converter(_Machinery):
    """An energy converter: its capacity, efficiency, fuel types and emissions."""

    type = CONVERTER

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # external variables -----------------------------------------------------------
        # power
        self.power_capacity: ScalarInput
        self.minimum_load: ScalarInput | None = None

        # fuels
        self.main_fuel_types: list[FuelTypeID]
        self.pilot_fuel_types: list[FuelTypeID] = []
        self.minimum_pilot_fuel: ForecastInput = Scalar(0.0)

        # performance
        self.efficiency: ScalarInput

        # emissions
        self.slip_fraction: dict[FuelTypeID, ScalarInput] = {}
        self.consumption_ttw: dict[tuple[FuelTypeID, str], ScalarInput] = {}

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(SECTION_DEFINE, required=True)
    def set_power_capacity(self, power_capacity: ScalarArgument) -> None:
        """Set the power capacity of the converter."""
        self.power_capacity = assign_value(
            as_scalar(power_capacity), type_=VARIABLE, lower=0.0
        )

    @deck_attribute(SECTION_DEFINE)
    def set_minimum_load(self, minimum_load: ScalarArgument) -> None:
        """Set the minimum load as a fraction of power capacity."""
        self.minimum_load = assign_value(
            as_scalar(minimum_load), type_=VARIABLE, lower=0.0, upper=1.0
        )

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_main_fuel_types(self, main_fuel_types: str | list[str]) -> None:
        """Set the main fuel types of the converter."""
        self.main_fuel_types = assign_id_list(
            main_fuel_types, FuelTypeID, min_length=1, unique=True
        )

    @deck_attribute(SECTION_DEFINE)
    def set_pilot_fuel_types(self, pilot_fuel_types: str | list[str]) -> None:
        """Set the pilot fuel types of the converter."""
        self.pilot_fuel_types = assign_id_list(
            pilot_fuel_types, FuelTypeID, min_length=1, unique=True
        )

    @deck_attribute()
    def set_minimum_pilot_fuel(self, minimum_pilot_fuel: ForecastArgument) -> None:
        """Set the minimum pilot fuel fraction required to use the converter."""
        self.minimum_pilot_fuel = assign_value(
            as_scalar(minimum_pilot_fuel),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            upper=1.0,
        )

    @deck_attribute(required=True)
    def set_efficiency(self, efficiency: ScalarArgument) -> None:
        """Set the energy conversion efficiency of the converter."""
        self.efficiency = assign_value(
            as_scalar(efficiency), type_=VARIABLE, lower=0.0, upper=1.0
        )

    # external methods (DSL commands) --------------------------------------------------
    @deck_command()
    def set_slip_fraction(self, fuel_type: str, value: ScalarArgument) -> None:
        """Set the fraction of fuel mass escaping unburned for a fuel type."""
        id_ = assign_member(fuel_type, self.get_fuel_types())
        value_ = assign_value(as_scalar(value), type_=VARIABLE, lower=0.0, upper=1.0)

        write_matching_keys(id_, value_, self.slip_fraction)

    @deck_command()
    def set_consumption_ttw(
        self, fuel_type: str, emission_name: str, value: ScalarArgument
    ) -> None:
        """Set a consumption-related emission for a fuel type in the converter."""
        id_ = assign_member(fuel_type, self.get_fuel_types())
        value_ = assign_value(as_scalar(value), type_=VARIABLE, lower=0.0)

        write_matching_key_pairs((id_, emission_name), value_, self.consumption_ttw)

    # internal methods -----------------------------------------------------------------
    def check_consistency(self) -> None:
        shared: list[str] = []

        for fuel_type in self.pilot_fuel_types:
            if fuel_type in self.main_fuel_types:
                shared.append(fuel_type.name)

        if shared:
            raise ValueError(
                f"{self}: No fuel type may be in both 'MainFuelTypes' and"
                f" 'PilotFuelTypes', but got {', '.join(shared)} in both."
            )

    def initialize_dependencies(self, emissions: dict[str, Emission]) -> None:
        """
        Initialize dependent dictionaries to allow wildcarding in command calls.

        Parameters
        ----------
        emissions
            All emissions in the simulation.
        """
        for fuel_type in self.get_fuel_types():
            self.slip_fraction.setdefault(fuel_type, Scalar(0.0))
            for emission_name in emissions:
                self.consumption_ttw.setdefault((fuel_type, emission_name), Scalar(0.0))

    def get_fuel_types(self) -> tuple[FuelTypeID, ...]:
        return (*self.main_fuel_types, *self.pilot_fuel_types)

    def is_dual_fuel(self) -> bool:
        return bool(self.pilot_fuel_types)
