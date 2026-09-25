# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the policy base shared by the Levy and Regulation nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    as_list,
    as_scalar,
    assign_boolean,
    assign_id,
    assign_list,
    assign_value,
    command_assignment_to_boolean_dict,
    command_assignment_to_dict,
    command_assignment_to_tuple_dict,
)
from navigate.core.enum_ import PolicyScopeID
from navigate.core.node import Node
from navigate.core.node_type import CURVE, EMISSION, FORECAST, FUEL, PORT, VARIABLE
from navigate.exceptions import no_value_assigned_error

if TYPE_CHECKING:
    from navigate.core.enum_ import LevySchemeID, RegulationSchemeID
    from navigate.core.expectations import LevyExpectation, RegulationExpectation
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.input_kinds import CurveInput, ForecastInput, ScalarInput
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.vessel import Vessel


class _Policy(Node):
    """The scope, jurisdiction and emission factors common to every policy node."""

    def __init__(self, name: str, type_: str) -> None:
        super().__init__(name, type_)

        # external variables -----------------------------------------------------------
        # active
        self.active: bool = True

        # design
        self.scheme: LevySchemeID | RegulationSchemeID
        self.jurisdiction: list[Port] = []

        # emissions
        self.emissions: list[Emission] = []
        self.fuels: list[Fuel] = []
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
    def set_active(self, active: str) -> None:
        """
        Set the flag for whether the policy is active.

        If the policy is active it is included in the calculation of results as well as
        expectations. If the policy is inactive it is ignored from all aspects of the
        simulation.

        Parameters
        ----------
        active
            Boolean flag.
        """
        self.active = assign_boolean(active)

    def set_jurisdiction(self, ports: list[Port]) -> None:
        """
        Set the list of ports that are under the jurisdiction of the policy.

        Examples
        --------
        - Port("name")
        - [Port("name1"), Port("name2")]

        Parameters
        ----------
        ports
            List of Port nodes.
        """
        self.jurisdiction = assign_list(as_list(ports), scalar=False, type_=PORT)

    def set_emissions(self, emissions: list[Emission]) -> None:
        """
        Set the emission(s) targeted by the policy.

        Examples
        --------
        - Emission("name")
        - [Emission("name1"), Emission("name2")]
        - Emission("*")

        Parameters
        ----------
        emissions
            A list of Emission nodes.
        """
        self.emissions = assign_list(
            as_list(emissions), unique=True, scalar=False, type_=EMISSION
        )

    def set_fuels(self, fuels: list[Fuel]) -> None:
        """
        Set the fuel(s) targeted by the policy.

        Examples
        --------
        - Fuel("name")
        - [Fuel("name1"), Fuel("name2")]
        - Fuel("*")

        Parameters
        ----------
        fuels
            A list of Fuel nodes.
        """
        self.fuels = assign_list(as_list(fuels), unique=True, scalar=False, type_=FUEL)

    def set_scope(self, scope: str) -> None:
        """
        Set the scope of emission targeted by the policy.

        If 'WTT' then only the well-to-tank emissions are included in the policy.
        If 'TTW' then only the tank-to-wake emissions are included in the policy.
        If 'WTW' then the full well-to-wake emissions are included in the policy.

        Examples
        --------
        - WTT
        - TTW
        - WTW

        Parameters
        ----------
        scope
            Emission scope.
        """
        self.scope = assign_id(scope, PolicyScopeID)

    def set_include_slip(self, include_slip: str) -> None:
        """
        Set whether emissions slip is included in the policy's emissions calculation.

        Examples
        --------
        - TRUE
        - FALSE

        Parameters
        ----------
        include_slip
            Boolean flag.
        """
        self.include_slip = assign_boolean(include_slip)

    def set_emissions_lifetime(self, emissions_lifetime: float | ScalarInput) -> None:
        """
        Set the emission lifetime used in the GWP calculation of emissions.

        Examples
        --------
        - 100

        Parameters
        ----------
        emissions_lifetime
            Emissions lifetime used in GWP calculation.
        """
        self.emissions_lifetime = assign_value(
            as_scalar(emissions_lifetime), type_=VARIABLE, lower=0.0
        )

    # external methods (DSL commands) --------------------------------------------------
    def set_include_vessel(self, vessel_name: str, include_vessel: str) -> None:
        """
        Set whether a specific vessel is impacted by the policy.

        Examples
        --------
        - "vessel_name", TRUE
        - "vessel_name", FALSE

        Parameters
        ----------
        vessel_name
            Name of vessel.
        include_vessel
            Whether the vessel is impacted by the policy.
        """
        command_assignment_to_boolean_dict(
            vessel_name, include_vessel, self.include_vessel, allow_empty=True
        )

    def set_global_warming_potential(
        self, emission_name: str, global_warming_potential: float | CurveInput
    ) -> None:
        """
        Set the GWP used to translate tons of emissions into CO2-equivalent emissions.

        If this value is not assigned the global warming potential assigned to the
        emission node is used instead. A curve is read at the emissions lifetime of
        the policy, or of the model when the policy assigns none.

        Examples
        --------
        - "emission_name", 25
        - "emission_name", Curve("curve_name")

        Parameters
        ----------
        emission_name
            Name of emission for which the global warming potential is assigned.
        global_warming_potential
            Global warming potential in ton CO2eq/ton emission.
        """
        command_assignment_to_dict(
            emission_name,
            as_scalar(global_warming_potential),
            self.global_warming_potential,
            type_=(CURVE, VARIABLE),
        )

    def set_fuel_wtt(
        self, fuel_name: str, emission_name: str, emission_factor: float | ForecastInput
    ) -> None:
        """
        Set the WTT emission factor for a given fuel and emission.

        If this value is not assigned the production specific calculation of the WTT is
        used instead.

        Examples
        --------
        - "fuel_name", "emission_name", 3.2
        - "fuel_name", "emission_name", Forecast("forecast_name")

        Parameters
        ----------
        fuel_name
            Name of fuel for which the emission factor is assigned.
        emission_name
            Name of emission for which the emission factor is assigned.
        emission_factor
            WTT emission factor in ton emission/ton fuel.
        """
        command_assignment_to_tuple_dict(
            (fuel_name, emission_name),
            as_scalar(emission_factor),
            self.fuel_wtt,
            type_=(FORECAST, VARIABLE),
        )

    def set_fuel_ttw(
        self, fuel_name: str, emission_name: str, emission_factor: float | ForecastInput
    ) -> None:
        """
        Set the TTW emission factor for a given fuel and emission.

        If this value is not assigned the production specific calculation of the TTW is
        used instead.

        Examples
        --------
        - "fuel_name", "emission_name", 3.2
        - "fuel_name", "emission_name", Forecast("forecast_name")

        Parameters
        ----------
        fuel_name
            Name of fuel for which the emission factor is assigned.
        emission_name
            Name of emission for which the emission factor is assigned.
        emission_factor
            TTW emission factor in ton emission/ton fuel.
        """
        command_assignment_to_tuple_dict(
            (fuel_name, emission_name),
            as_scalar(emission_factor),
            self.fuel_ttw,
            type_=(FORECAST, VARIABLE),
        )

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:

        if not self.jurisdiction:
            no_value_assigned_error(self, "Jurisdiction")

        if not self.emissions:
            no_value_assigned_error(self, "Emissions")

        if not self.fuels:
            no_value_assigned_error(self, "Fuels")

    def _initialize_policy_dependencies(self, vessels: dict[str, Vessel]) -> None:

        # fuel_wtt, fuel_ttw, and global_warming_potential stay None when unset:
        # consumers fall back to the model's own factors
        for fuel in self.fuels:
            fuel_name = fuel.name

            for emission in self.emissions:
                key = (fuel_name, emission.name)
                self.fuel_wtt.setdefault(key, None)
                self.fuel_ttw.setdefault(key, None)

        for emission in self.emissions:
            self.global_warming_potential.setdefault(emission.name, None)

        for vessel_name in vessels:
            self.include_vessel.setdefault(vessel_name, False)

        # derived from the current routes and jurisdiction, so recomputed
        # unconditionally every pass
        jurisdiction = set(self.jurisdiction)
        for vessel_name, vessel in vessels.items():
            self.in_jurisdiction_vessel[vessel_name] = not jurisdiction.isdisjoint(
                vessel.route.ports
            )

    def _calculate_policy_expectations(
        self,
        expectation: LevyExpectation | RegulationExpectation,
        emissions: dict[str, Emission],
        emissions_lifetime: float,
    ) -> None:

        if self.emissions_lifetime is not None:
            emissions_lifetime = self.emissions_lifetime.get()

        for (
            emissions_name,
            global_warming_potential,
        ) in self.global_warming_potential.items():
            if global_warming_potential is not None:
                gwp = global_warming_potential.get(emissions_lifetime)
            else:
                gwp = emissions[emissions_name].global_warming_potential.get(
                    emissions_lifetime
                )

            expectation.set_global_warming_potential(emissions_name, gwp)

    def is_active(self) -> bool:
        return self.active

    def vessel_is_policed(self, vessel_name: str) -> bool:
        return (
            self.include_vessel[vessel_name]
            and self.in_jurisdiction_vessel[vessel_name]
        )
