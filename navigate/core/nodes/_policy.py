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
        self.global_warming_potential: dict[str, CurveInput | None] = {}
        self.fuel_wtt: dict[tuple[str, str], ForecastInput | None] = {}
        self.fuel_ttw: dict[tuple[str, str], ForecastInput | None] = {}

        # internal variables -----------------------------------------------------------
        self.in_jurisdiction_vessel: dict[str, bool] = {}

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute()
    def set_active(self, active: str) -> None:
        """Set the flag for whether the policy is active."""
        self.active = assign_boolean(active)

    @deck_attribute(SECTION_DEFINE)
    def set_jurisdiction(self, ports: Port | list[Port]) -> None:
        """Set the ports under the jurisdiction of the policy."""
        self.jurisdiction = assign_reference_list(ports, PORT)

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_emissions(self, emissions: Emission | list[Emission]) -> None:
        """Set the emissions targeted by the policy."""
        self.emissions = assign_reference_list(
            emissions, EMISSION, min_length=1, unique=True
        )

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_fuels(self, fuels: Fuel | list[Fuel]) -> None:
        """Set the fuels targeted by the policy."""
        self.fuels = assign_reference_list(fuels, FUEL, min_length=1, unique=True)

    @deck_attribute(SECTION_DEFINE)
    def set_scope(self, scope: str) -> None:
        """Set the scope of emissions targeted by the policy."""
        self.scope = assign_id(scope, PolicyScopeID)

    @deck_attribute(SECTION_DEFINE)
    def set_emissions_lifetime(self, emissions_lifetime: ScalarArgument) -> None:
        """Set the emissions lifetime used in the GWP calculation of emissions."""
        self.emissions_lifetime = assign_value(
            as_scalar(emissions_lifetime), type_=VARIABLE, lower=0.0
        )

    @deck_attribute()
    def set_include_slip(self, include_slip: str) -> None:
        """Set whether emissions slip is included in the policy's emissions."""
        self.include_slip = assign_boolean(include_slip)

    # external methods (DSL commands) --------------------------------------------------
    @deck_command()
    def set_include_vessel(self, vessel_name: str, include_vessel: str) -> None:
        """Set whether a vessel is impacted by the policy."""
        write_matching_keys(
            vessel_name,
            assign_boolean(include_vessel),
            self.include_vessel,
            allow_empty=True,
        )

    @deck_command()
    def set_global_warming_potential(
        self, emission_name: str, global_warming_potential: CurveArgument
    ) -> None:
        """Set the GWP of an emission under the policy."""
        write_matching_keys(
            emission_name,
            assign_value(as_scalar(global_warming_potential), type_=(CURVE, VARIABLE)),
            self.global_warming_potential,
        )

    @deck_command()
    def set_fuel_wtt(
        self, fuel_name: str, emission_name: str, emission_factor: ForecastArgument
    ) -> None:
        """Set the WTT emission factor of a fuel and emission under the policy."""
        write_matching_key_pairs(
            (fuel_name, emission_name),
            assign_value(as_scalar(emission_factor), type_=(FORECAST, VARIABLE)),
            self.fuel_wtt,
        )

    @deck_command()
    def set_fuel_ttw(
        self, fuel_name: str, emission_name: str, emission_factor: ForecastArgument
    ) -> None:
        """Set the TTW emission factor of a fuel and emission under the policy."""
        write_matching_key_pairs(
            (fuel_name, emission_name),
            assign_value(as_scalar(emission_factor), type_=(FORECAST, VARIABLE)),
            self.fuel_ttw,
        )

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:
        if not self.jurisdiction:
            raise UnassignedAttributeError(str(self), "Jurisdiction")

    def initialize_dependencies(self, vessels: dict[str, Vessel]) -> None:
        """
        Initialize dependent dictionaries to allow wildcarding during command calls.

        Parameters
        ----------
        vessels
            All vessels in the simulation.
        """
        for vessel_name in vessels:
            self.include_vessel.setdefault(vessel_name, False)

        # unset factors stay None, so consumers fall back to the model's own factors
        for emission in self.emissions:
            self.global_warming_potential.setdefault(emission.name, None)
        for fuel in self.fuels:
            for emission in self.emissions:
                key = (fuel.name, emission.name)
                self.fuel_wtt.setdefault(key, None)
                self.fuel_ttw.setdefault(key, None)

        # recomputed every pass, as routes and jurisdiction may change
        jurisdiction = set(self.jurisdiction)
        for vessel_name, vessel in vessels.items():
            in_jurisdiction = not jurisdiction.isdisjoint(vessel.route.ports)
            self.in_jurisdiction_vessel[vessel_name] = in_jurisdiction

    def vessel_is_policed(self, vessel_name: str) -> bool:
        return (
            self.include_vessel[vessel_name]
            and self.in_jurisdiction_vessel[vessel_name]
        )
