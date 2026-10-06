# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Converter node, machinery turning fuel into usable energy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    Scalar,
    as_scalar,
    assign_id_list,
    assign_member,
    assign_value,
    write_matching_key_pairs,
    write_matching_keys,
)
from navigate.core.enum_ import FuelTypeID
from navigate.core.node_type import CONVERTER, FORECAST, VARIABLE
from navigate.core.nodes._machinery import _Machinery
from navigate.exceptions import UnassignedAttributeError
from navigate.util import list_is_unique

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.types_ import (
        ForecastArgument,
        ForecastInput,
        ScalarArgument,
        ScalarInput,
    )


class Converter(_Machinery):
    """An energy converter: its capacity, efficiency, fuel types and emissions."""

    def __init__(self, name: str) -> None:
        super().__init__(name, CONVERTER)

        # external variables -----------------------------------------------------------
        # power
        self.power_capacity: ScalarInput
        self.minimum_load: ScalarInput | None = None

        # fuels
        self.main_fuel_types: list[FuelTypeID] = []
        self.pilot_fuel_types: list[FuelTypeID] = []
        self.minimum_pilot_fuel: ForecastInput = Scalar(0.0)

        # performance
        self.efficiency: ScalarInput

        # emissions
        self.consumption_ttw: dict[tuple[FuelTypeID, str], ScalarInput] = {}
        self.slip_fraction: dict[FuelTypeID, ScalarInput] = {}

    # external methods (DSL attributes) ------------------------------------------------
    def set_power_capacity(self, power_capacity: ScalarArgument) -> None:
        """
        Set the maximum power capacity of the converter.

        Examples
        --------
        - 50.0
        - Variable("name")

        Parameters
        ----------
        power_capacity
            The maximum power capacity of the converter.
        """
        self.power_capacity = assign_value(
            as_scalar(power_capacity), type_=VARIABLE, lower=0.0
        )

    def set_minimum_load(self, minimum_load: ScalarArgument) -> None:
        """
        Set the minimum load as a fraction of power capacity.

        Examples
        --------
        - 0.3
        - Variable("name")

        Parameters
        ----------
        minimum_load
            The minimum load as a fraction of power capacity.
        """
        self.minimum_load = assign_value(
            as_scalar(minimum_load), type_=VARIABLE, lower=0.0, upper=1.0
        )

    def set_main_fuel_types(self, main_fuel_types: str | list[str]) -> None:
        """
        Set the main fuel types of the converter.

        Examples
        --------
        - OIL
        - [METHANOL, OIL]

        Parameters
        ----------
        main_fuel_types
            Main fuel type or list of main fuel types of the converter.
        """
        self.main_fuel_types = assign_id_list(main_fuel_types, FuelTypeID, min_length=1)

    def set_pilot_fuel_types(self, pilot_fuel_types: str | list[str]) -> None:
        """
        Set the pilot fuel types of the converter.

        No fuel type may appear in both MainFuelTypes and PilotFuelTypes.

        Examples
        --------
        - OIL
        - [METHANOL, OIL]

        Parameters
        ----------
        pilot_fuel_types
            Pilot fuel type or list of pilot fuel types of the converter.
        """
        self.pilot_fuel_types = assign_id_list(
            pilot_fuel_types, FuelTypeID, min_length=1
        )

    def set_minimum_pilot_fuel(self, minimum_pilot_fuel: ForecastArgument) -> None:
        """
        Set the minimum pilot fuel fraction required to utilize the converter in GJ/GJ.

        Examples
        --------
        - 0.05
        - Forecast("name")

        Parameters
        ----------
        minimum_pilot_fuel
            Minimum pilot fuel fraction.
        """
        self.minimum_pilot_fuel = assign_value(
            as_scalar(minimum_pilot_fuel),
            type_=(VARIABLE, FORECAST),
            lower=0.0,
            upper=1.0,
        )

    def set_efficiency(self, efficiency: ScalarArgument) -> None:
        """
        Set the energy conversion efficiency from potential to required kinetic energy.

        Examples
        --------
        - 0.3
        - Variable("name")

        Parameters
        ----------
        efficiency
            The energy conversion efficiency.
        """
        self.efficiency = assign_value(
            as_scalar(efficiency), type_=VARIABLE, lower=0.0, upper=1.0
        )

    # external methods (DSL commands) --------------------------------------------------
    def set_slip_fraction(self, fuel_type: str, value: ScalarArgument) -> None:
        """
        Set the fraction of fuel mass escaping unburned (slip) for a specific fuel type.

        The fuel type must be one of the converter's main or pilot fuel types.

        Examples
        --------
        - METHANE, 0.03
        - METHANE, Variable("methane_slip")

        Parameters
        ----------
        fuel_type
            Type of fuel which has slip when used.
        value
            Fraction of fuel mass escaping unburned.
        """
        value_ = assign_value(as_scalar(value), type_=VARIABLE, lower=0.0, upper=1.0)

        id_ = assign_member(fuel_type, tuple(self.get_fuel_types()))

        write_matching_keys(id_, value_, self.slip_fraction)

    def set_consumption_ttw(
        self, fuel_type: str, emission_name: str, value: ScalarArgument
    ) -> None:
        """
        Set a consumption related emission for a specific fuel type in the converter.

        Notice that this number is given in the unit ton emission / ton fuel into the
        engine. I.e., if the engine has slip (e.g., methane slip) then this number is
        already adjusted for this. The fuel type must be one of the converter's main or
        pilot fuel types.

        Examples
        --------
        - OIL, "nitrous_oxide", 0.001
        - OIL, "carbon_dioxide", Variable("name")

        Parameters
        ----------
        fuel_type
            Type of fuel which has a consumption related emission when used.
        emission_name
            Name of the emission, possibly including wildcards.
        value
            Ton of emission emitted per ton of fuel consumed.
        """
        value_ = assign_value(as_scalar(value), type_=VARIABLE, lower=0.0)

        id_ = assign_member(fuel_type, tuple(self.get_fuel_types()))

        write_matching_key_pairs((id_, emission_name), value_, self.consumption_ttw)

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:

        if not self.main_fuel_types:
            raise UnassignedAttributeError(str(self), "MainFuelTypes")

    def check_consistency(self) -> None:

        if not list_is_unique(self.main_fuel_types):
            raise ValueError(f"{self}: All 'MainFuelTypes' must be unique.")

        if self.pilot_fuel_types and not list_is_unique(
            self.main_fuel_types + self.pilot_fuel_types
        ):
            raise ValueError(
                f"{self}: All fuel types across 'MainFuelTypes' and 'PilotFuelTypes'"
                " must be unique."
            )

    def initialize_dependencies(self, emissions: dict[str, Emission]) -> None:
        """
        Seed the per-fuel-type dictionaries with their defaults.

        Parameters
        ----------
        emissions
            Dict of class Emission.
        """
        for fuel_type in self.get_fuel_types():
            self.slip_fraction.setdefault(fuel_type, Scalar(0.0))

            for emission_name in emissions:
                self.consumption_ttw.setdefault((fuel_type, emission_name), Scalar(0.0))

    def get_fuel_types(self) -> list[FuelTypeID]:
        return self.main_fuel_types + self.pilot_fuel_types

    def is_dual_fuel(self) -> bool:
        return bool(self.pilot_fuel_types)

    def get_effective_lhv(self, fuel: Fuel) -> float:
        """
        Return the heating value of a fuel net of slip, (1 - slip) * LHV.

        Parameters
        ----------
        fuel
            Fuel burned in the converter; its fuel type must be one of the converter's.

        Returns
        -------
        float
            Effective lower heating value, in GJ/ton fuel-in.
        """
        slip = self.slip_fraction[fuel.fuel_type].get()
        return (1.0 - slip) * fuel.lower_heating_value.get()
