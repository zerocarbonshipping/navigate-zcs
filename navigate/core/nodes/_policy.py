# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the policy base shared by the Levy and Regulation nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    SECTION_DEFINE,
    as_scalar,
    assign_boolean,
    assign_id,
    assign_reference_list,
    assign_value,
    deck_attribute,
    deck_command,
    write_matching_key_pairs,
    write_matching_keys,
)
from navigate.core.enum_ import PolicyScopeID
from navigate.core.node import Node
from navigate.core.node_type import CURVE, EMISSION, FORECAST, FUEL, PORT, VARIABLE
from navigate.exceptions import UnassignedAttributeError

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.types_ import (
        CurveArgument,
        CurveInput,
        ForecastArgument,
        ForecastInput,
        ScalarArgument,
        ScalarInput,
    )


class _Policy(Node):
    """The scope, jurisdiction and emission factors common to every policy node."""

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # external variables -----------------------------------------------------------
        self.active: bool = True
        self.jurisdiction: list[Port] = []

        # emissions
        self.emissions: list[Emission]
        self.fuels: list[Fuel]
        self.scope: PolicyScopeID = PolicyScopeID.WTW
        self.emissions_lifetime: ScalarInput | None = None
        self.include_slip: bool = True

        # vessels impacted by the policy
        self.include_vessel: dict[str, bool] = {}

        # emission factors
        self.global_warming_potentials: dict[str, CurveInput | None] = {}
        self.fuel_wtt: dict[tuple[str, str], ForecastInput | None] = {}
        self.fuel_ttw: dict[tuple[str, str], ForecastInput | None] = {}

        # internal variables -----------------------------------------------------------
        # node maps
        self.in_jurisdiction_vessel: dict[str, bool]

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute()
    def set_active(self, value: str) -> None:
        """Set whether the policy is active."""
        self.active = assign_boolean(value)

    @deck_attribute(SECTION_DEFINE)
    def set_jurisdiction(self, value: Port | list[Port]) -> None:
        """Set the ports under the jurisdiction of the policy."""
        self.jurisdiction = assign_reference_list(value, PORT)

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_emissions(self, value: Emission | list[Emission]) -> None:
        """Set the emissions targeted by the policy."""
        self.emissions = assign_reference_list(
            value, EMISSION, min_length=1, unique=True
        )

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_fuels(self, value: Fuel | list[Fuel]) -> None:
        """Set the fuels targeted by the policy."""
        self.fuels = assign_reference_list(value, FUEL, min_length=1, unique=True)

    @deck_attribute(SECTION_DEFINE)
    def set_scope(self, value: str) -> None:
        """Set the scope of emissions targeted by the policy."""
        self.scope = assign_id(value, PolicyScopeID)

    @deck_attribute(SECTION_DEFINE)
    def set_emissions_lifetime(self, value: ScalarArgument) -> None:
        """Set the emissions lifetime used in the GWP calculation of emissions."""
        self.emissions_lifetime = assign_value(
            as_scalar(value), type_=VARIABLE, lower=0.0
        )

    @deck_attribute()
    def set_include_slip(self, value: str) -> None:
        """Set whether emissions slip is included in the policy's emissions."""
        self.include_slip = assign_boolean(value)

    # external methods (DSL commands) --------------------------------------------------
    @deck_command()
    def set_include_vessel(self, key: str, value: str) -> None:
        """Set whether a vessel is impacted by the policy."""
        write_matching_keys(
            key, assign_boolean(value), self.include_vessel, allow_empty=True
        )

    @deck_command()
    def set_global_warming_potential(self, key: str, value: CurveArgument) -> None:
        """Set the GWP of an emission under the policy."""
        write_matching_keys(
            key,
            assign_value(as_scalar(value), type_=(CURVE, VARIABLE)),
            self.global_warming_potentials,
        )

    @deck_command()
    def set_fuel_wtt(self, key1: str, key2: str, value: ForecastArgument) -> None:
        """Set the WTT emission factor of a fuel and emission under the policy."""
        write_matching_key_pairs(
            (key1, key2),
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE)),
            self.fuel_wtt,
        )

    @deck_command()
    def set_fuel_ttw(self, key1: str, key2: str, value: ForecastArgument) -> None:
        """Set the TTW emission factor of a fuel and emission under the policy."""
        write_matching_key_pairs(
            (key1, key2),
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE)),
            self.fuel_ttw,
        )

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:
        if not self.jurisdiction:
            raise UnassignedAttributeError(str(self), "Jurisdiction")

    def initialize_dependencies(self, vessels: dict[str, Vessel]) -> None:
        """
        Initialize dependent dictionaries to allow wildcarding in command calls.

        Parameters
        ----------
        vessels
            All vessels in the simulation.
        """
        for vessel_name in vessels:
            self.include_vessel.setdefault(vessel_name, False)

        # unset factors stay None, so consumers fall back to the model's own factors
        for emission in self.emissions:
            self.global_warming_potentials.setdefault(emission.name, None)
        for fuel in self.fuels:
            for emission in self.emissions:
                key = (fuel.name, emission.name)
                self.fuel_wtt.setdefault(key, None)
                self.fuel_ttw.setdefault(key, None)

    def vessel_is_policed(self, vessel_name: str) -> bool:
        return (
            self.include_vessel[vessel_name]
            and self.in_jurisdiction_vessel[vessel_name]
        )
