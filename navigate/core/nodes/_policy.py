# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core import (
    as_list,
    as_scalar,
    assign_id,
    assign_list,
    assign_value,
    command_assignment_to_boolean_dict,
    command_assignment_to_dict,
    command_assignment_to_tuple_dict,
)
from navigate.core.assign import BOOL_ID
from navigate.core.enum_ import PolicyScopeID
from navigate.core.node import Node
from navigate.core.node_type import CURVE, EMISSION, FORECAST, FUEL, PORT, VARIABLE
from navigate.exceptions import no_value_assigned_error


class _Policy(Node):
    def __init__(self, name):
        super().__init__(name)

        # active
        self.active = None                 # bool, whether the regulation is active and known

        # design
        self.scheme = None                 # enum, ID of implementation scheme
        self.jurisdiction = []             # list[Port], list of ports affected

        # emissions
        self.emissions = []                        # list[Emission], specific emissions being regulated
        self.fuels = []                            # list[Fuel], specific fuels being regulated
        self.scope = None                          # enum, ID of emission scope
        self.emissions_lifetime = None             # float, emissions lifetime in GWP calculations
        self.include_slip = None                   # bool, whether to include slip in coefficients

        # vessels impacted by the policy
        self.include_vessel = {}       # dict[vessel_name: bool], whether a vessel is impacted by the policy.

        # emission factors
        self.global_warming_potential = {}     # dict[emission_name: float], policy specific GWP
        self.fuel_wtt = {}     # dict[(fuel_name, emission_name): float], policy specified WTT emissions factor
        self.fuel_ttw = {}     # dict[(fuel_name, emission_name): float], policy specified TTW emissions factor

        # internal attributes
        self.in_jurisdiction_vessel = {}  # dict[vessel_name: bool], whether a vessel is outside the jurisdiction

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_active(self, active):
        """
        Set the flag for whether the policy is active.

        If the policy is active it is included in the calculation of results as well as expectations.
        If the policy is inactive it is ignored from all aspects of the simulation.

        Parameters
        ----------
        active : str
            Boolean flag.
        """

        self.active = assign_id(active, BOOL_ID)

    def set_jurisdiction(self, ports):
        """
        Set the list of ports that are under the jurisdiction of the policy.

        Examples
        --------
        - Port("name")
        - [Port("name1"), Port("name2")]

        Parameters
        ----------
        ports : list[NodeReference]
            List of node references to ports.
        """

        self.jurisdiction = assign_list(as_list(ports), scalar=False, type_=PORT)

    def set_emissions(self, emissions):
        """
        Set the emission(s) targeted by the policy.

        Examples
        --------
        - Emission("name")
        - [Emission("name1"), Emission("name2")]
        - Emission("*")

        Parameters
        ----------
        emissions : list[Emission]
            A list of node references to Emissions.
        """

        self.emissions = assign_list(as_list(emissions), unique=True, scalar=False, type_=EMISSION)

    def set_fuels(self, fuels):
        """
        Set the fuel(s) targeted by the policy.

        Examples
        --------
        - Fuel("name")
        - [Fuel("name1"), Fuel("name2")]
        - Fuel("*")

        Parameters
        ----------
        fuels : list[Emission]
            A list of node references to Fuels.
        """

        self.fuels = assign_list(as_list(fuels), unique=True, scalar=False, type_=FUEL)

    def set_scope(self, scope):
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
        scope : str
            Emission scope.
        """

        self.scope = assign_id(scope, PolicyScopeID)

    def set_include_slip(self, include_slip):
        """
        Set the flag for whether emissions slip is included in the calculation of the emissions in the policy.

        Examples
        --------
        - TRUE
        - FALSE

        Parameters
        ----------
        include_slip : str
            Boolean flag.
        """

        self.include_slip = assign_id(include_slip, BOOL_ID)

    def set_emissions_lifetime(self, emissions_lifetime):
        """
        Set the emission lifetime used in the GWP calculation of emissions.

        Examples
        --------
        - 100

        Parameters
        ----------
        emissions_lifetime : float | NodeReference
            Emissions lifetime used in GWP calculation.
        """

        self.emissions_lifetime = assign_value(as_scalar(emissions_lifetime), type_=VARIABLE, lower=0.)

    # external commands called in the input deck -----------------------------------------------------------------------
    def set_include_vessel(self, vessel_name, include_vessel):
        """
        Set whether a specific vessel is impacted by the policy.

        Examples
        --------
        - "vessel_name", TRUE
        - "vessel_name", FALSE

        Parameters
        ----------
        vessel_name : str
            Name of vessel.
        include_vessel : float | NodeReference
            Whether the vessel is impacted by the policy.
        """

        command_assignment_to_boolean_dict(vessel_name, include_vessel, self.include_vessel, allow_empty=True)

    def set_global_warming_potential(self, emission_name, global_warming_potential):
        """
        Set the global warming potential used to translate tons of emissions into CO2-equivalent emissions.

        If this value is not assigned the global warming potential assigned to the emission node is used instead.

        Examples
        --------
        - "emission_name", 25
        - "emission_name", Curve("curve_name")

        Parameters
        ----------
        emission_name : str
            Name of emission for which the global warming potential is assigned.
        global_warming_potential : float | NodeReference
            Global warming potential in ton CO2eq/ton emission.
        """

        command_assignment_to_dict(emission_name,
                                   global_warming_potential,
                                   self.global_warming_potential,
                                   type_=(CURVE, VARIABLE))

    def set_fuel_wtt(self, fuel_name, emission_name, emission_factor):
        """
        Set the WTT emission factor for a given fuel and emission to be used in the calculation of emissions.

        If this value is not assigned the production specific calculation of the WTT is used instead.

        Examples
        --------
        - "fuel_name", "emission_name", 3.2
        - "fuel_name", "emission_name", Forecast("forecast_name")

        Parameters
        ----------
        fuel_name : str
            Name of fuel for which the emission factor is assigned.
        emission_name : str
            Name of emission for which the emission factor is assigned.
        emission_factor : float | NodeReference
            WTT emission factor in ton emission/ton fuel.
        """

        command_assignment_to_tuple_dict((fuel_name, emission_name),
                                         emission_factor,
                                         self.fuel_wtt,
                                         type_=(FORECAST, VARIABLE))

    def set_fuel_ttw(self, fuel_name, emission_name, emission_factor):
        """
        Set the TTW emission factor for a given fuel and emission to be used in the calculation of emissions.

        If this value is not assigned the production specific calculation of the TTW is used instead.

        Examples
        --------
        - "fuel_name", "emission_name", 3.2
        - "fuel_name", "emission_name", Forecast("forecast_name")

        Parameters
        ----------
        fuel_name : str
            Name of fuel for which the emission factor is assigned.
        emission_name : str
            Name of emission for which the emission factor is assigned.
        emission_factor : float | NodeReference
            TTW emission factor in ton emission/ton fuel.
        """

        command_assignment_to_tuple_dict((fuel_name, emission_name),
                                         emission_factor,
                                         self.fuel_ttw,
                                         type_=(FORECAST, VARIABLE))

    # internal methods -------------------------------------------------------------------------------------------------
    def _initialize_policy(self):

        if not self.jurisdiction:
            no_value_assigned_error(self, 'Jurisdiction')

        if not self.emissions:
            no_value_assigned_error(self, 'Emissions')

        if not self.fuels:
            no_value_assigned_error(self, 'Fuels')

        if self.active is None:
            self.active = True

        if self.scope is None:
            self.scope = PolicyScopeID.WTW

        if self.include_slip is None:
            self.include_slip = True

    def _initialize_policy_dependencies(self, vessels):

        for fuel in self.fuels:
            fuel_name = fuel.name

            for emission in self.emissions:
                key = (fuel_name, emission.name)
                self.fuel_wtt[key] = None
                self.fuel_ttw[key] = None

        for emission in self.emissions:
            self.global_warming_potential[emission.name] = None

        for vessel_name in vessels:
            if vessel_name not in self.include_vessel:
                self.include_vessel[vessel_name] = False

        for vessel_name, vessel in vessels.items():
            in_jurisdiction = not set(vessel.route.ports).isdisjoint(set(self.jurisdiction))
            self.in_jurisdiction_vessel[vessel_name] = in_jurisdiction

    def _calculate_policy_expectations(self, expectation, emissions, emissions_lifetime):

        if self.emissions_lifetime is not None:
            emissions_lifetime = self.emissions_lifetime.get()

        for emissions_name, global_warming_potential in self.global_warming_potential.items():

            if global_warming_potential is not None:
                gwp = global_warming_potential.get()
            else:
                gwp = emissions[emissions_name].global_warming_potential.get(emissions_lifetime)

            expectation.set_global_warming_potential(emissions_name, gwp)

    def is_active(self):
        return self.active

    def vessel_is_policed(self, vessel_name):
        return self.include_vessel[vessel_name] and self.in_jurisdiction_vessel[vessel_name]
