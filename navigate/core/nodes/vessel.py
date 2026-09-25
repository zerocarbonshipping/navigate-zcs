# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Vessel node, one vessel type with its loads, machinery and route."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    Scalar,
    as_list,
    as_scalar,
    assign_id,
    assign_list,
    assign_value,
)
from navigate.core.enum_ import FuelTypeID
from navigate.core.expectations import VesselExpectation
from navigate.core.node import Node
from navigate.core.node_type import (
    CURVE,
    FORECAST,
    POWER_SYSTEM,
    ROUTE,
    SURFACE,
    TANK,
    VARIABLE,
    VESSEL,
)
from navigate.core.profiles import VesselProfile
from navigate.exceptions import no_value_assigned_error

if TYPE_CHECKING:
    from collections.abc import Sequence

    import numpy as np

    from navigate.core.expression import Expression
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.input_kinds import (
        ForecastInput,
        ScalarInput,
        SurfaceInput,
    )
    from navigate.core.nodes.power_system import PowerSystem
    from navigate.core.nodes.route import Route
    from navigate.core.nodes.tank import Tank


class Vessel(Node):
    """A vessel type: its power demand, machinery, route, capacity and base cost."""

    def __init__(self, name: str) -> None:
        super().__init__(name, VESSEL)

        # external variables -----------------------------------------------------------
        # power demand
        self.propulsion_load: SurfaceInput = Scalar(0.0)
        self.electrical_load_at_sea: SurfaceInput = Scalar(0.0)
        self.electrical_load_in_port: ScalarInput = Scalar(0.0)
        self.heat_load_at_sea: SurfaceInput = Scalar(0.0)
        self.heat_load_in_port: ScalarInput = Scalar(0.0)

        # fuel based power
        self.power_system: PowerSystem | Expression
        self.tanks: list[Tank] = []

        # voyage
        self.route: Route | Expression
        self.nominal_capacity: ScalarInput

        # base cost
        self.capex: ForecastInput = Scalar(0.0)
        self.opex: ForecastInput = Scalar(0.0)
        self.lifetime: ForecastInput = Scalar(25.0)
        self.lead_time: ForecastInput = Scalar(0.0)
        self.cost_of_capital: ForecastInput = Scalar(0.0)

        # tag
        self.fuel_type: FuelTypeID | None = None

        # internal variables -----------------------------------------------------------
        self.expectation: VesselExpectation = VesselExpectation()
        self.profile: VesselProfile = VesselProfile()

        # convenience variables
        self.usable_fuel_types: list[FuelTypeID] = []
        self.usable_fuels: dict[str, Fuel] = {}

        # cross-check variables
        self.fleet_assignment: str | None = None

    # external methods (DSL attributes) ------------------------------------------------
    def set_propulsion_load(self, propulsion_load: float | SurfaceInput) -> None:
        """
        Set the propulsion load, in MW.

        This is the power required to propel the vessel at a given speed and draft
        (cargo utilization used as proxy).

        If a Curve is assigned it should return power (MW) as a function of speed
        (knots). If a Surface is assigned it should return power (MW) as a function of
        speed (knots) and cargo utilization (-).

        Examples
        --------
        - 16.5
        - Curve("name")
        - Surface("name")

        Parameters
        ----------
        propulsion_load
            The propulsion load in MW.
        """
        self.propulsion_load = assign_value(
            as_scalar(propulsion_load), type_=(CURVE, SURFACE, VARIABLE), lower=0.0
        )

    def set_electrical_load_at_sea(
        self, electrical_load_at_sea: float | SurfaceInput
    ) -> None:
        """
        Set the electrical load at sea, in MW.

        This is the power required to run auxiliary systems on the vessel at sea at a
        given speed and cargo utilization.

        If a Curve is assigned it should return power (MW) as a function of speed
        (knots). If a Surface is assigned it should return power (MW) as a function of
        speed (knots) and cargo utilization (-).

        Examples
        --------
        - 16.5
        - Curve("name")
        - Surface("name")

        Parameters
        ----------
        electrical_load_at_sea
            The electrical load at sea in MW.
        """
        self.electrical_load_at_sea = assign_value(
            as_scalar(electrical_load_at_sea),
            type_=(CURVE, SURFACE, VARIABLE),
            lower=0.0,
        )

    def set_electrical_load_in_port(
        self, electrical_load_in_port: float | ScalarInput
    ) -> None:
        """
        Set the electrical load in port in MW.

        This is the power required to run auxiliary systems on the vessel in port.

        Examples
        --------
        - 16.5

        Parameters
        ----------
        electrical_load_in_port
            The electrical load in port in MW.
        """
        self.electrical_load_in_port = assign_value(
            as_scalar(electrical_load_in_port), type_=VARIABLE, lower=0.0
        )

    def set_heat_load_at_sea(self, heat_load_at_sea: float | SurfaceInput) -> None:
        """
        Set the heat load at sea, in MW.

        This is the power required to produce heat on the vessel at sea at a given
        speed and cargo utilization.

        If a Curve is assigned it should return power (MW) as a function of speed
        (knots). If a Surface is assigned it should return power (MW) as a function of
        speed (knots) and cargo utilization (-).

        Examples
        --------
        - 16.5
        - Curve("name")
        - Surface("name")

        Parameters
        ----------
        heat_load_at_sea
            The heating load at sea in MW.
        """
        self.heat_load_at_sea = assign_value(
            as_scalar(heat_load_at_sea), type_=(CURVE, SURFACE, VARIABLE), lower=0.0
        )

    def set_heat_load_in_port(self, heat_load_in_port: float | ScalarInput) -> None:
        """
        Set the heating load in port in MW.

        This is the power required to produce heat on the vessel in port.

        Examples
        --------
        - 16.5

        Parameters
        ----------
        heat_load_in_port
            The heating load in port in MW.
        """
        self.heat_load_in_port = assign_value(
            as_scalar(heat_load_in_port), type_=VARIABLE, lower=0.0
        )

    def set_fuel_type(self, fuel_type: str) -> None:
        """
        Set the primary main fuel type of the vessel.

        If not assigned, the value is defaulted during initialization based on the
        assigned PowerSystem.

        Examples
        --------
        - OIL
        - AMMONIA
        - METHANOL

        Parameters
        ----------
        fuel_type
            Primary type of main fuel.
        """
        self.fuel_type = assign_id(fuel_type, FuelTypeID)

    def set_power_system(self, power_system: PowerSystem) -> None:
        """
        Set the PowerSystem used to convert fuel to energy.

        Examples
        --------
        - PowerSystem("name")

        Parameters
        ----------
        power_system
            The powersystem used to convert fuel to energy.
        """
        self.power_system = assign_value(power_system, scalar=False, type_=POWER_SYSTEM)

    def set_tanks(self, tanks: list[Tank]) -> None:
        """
        Set the list of tanks used for onboard fuel storage.

        Examples
        --------
        - Tank("name")
        - [Tank("name1"), Tank("name2")]

        Parameters
        ----------
        tanks
            List of Tank nodes.
        """
        self.tanks = assign_list(as_list(tanks), unique=True, scalar=False, type_=TANK)

    def set_route(self, route: Route) -> None:
        """
        Set the Route the vessel is sailing on.

        Examples
        --------
        - Route("name")

        Parameters
        ----------
        route
            The route the vessel is sailing on.
        """
        self.route = assign_value(route, scalar=False, type_=ROUTE)

    def set_nominal_capacity(self, nominal_capacity: float | ScalarInput) -> None:
        """
        Set the nominal cargo carrying capacity of the vessel.

        There is not a well-defined unit, it just has to match with the
        'Trade' attribute of the Fleet node the vessel is assigned to.
        In general the most logical unit for the vessel segment is applied:
        - Container: TEU (twenty-foot equivalent unit)
        - RoRo: CEU (car equivalent unit)
        - Bulk Carrier: DWT (dead weight tonnes)
        - etc.

        Examples
        --------
        - 8000

        Parameters
        ----------
        nominal_capacity
            The nominal cargo carrying capacity of the vessel.
        """
        self.nominal_capacity = assign_value(
            as_scalar(nominal_capacity), type_=VARIABLE, lower=0.0
        )

    def set_lifetime(self, lifetime: float | ForecastInput) -> None:
        """
        Set the lifetime of the vessel in years.

        The vessel is scrapped when it surpasses its lifetime.

        Examples
        --------
        - 25

        Parameters
        ----------
        lifetime
            Lifetime of the vessel in years.
        """
        self.lifetime = assign_value(
            as_scalar(lifetime),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    def set_lead_time(self, lead_time: float | ForecastInput) -> None:
        """
        Set the lead time of the vessel in years.

        The lead time is only used for the calculation of the levelized cost of a vessel
        (charter rate) and does not impact the delivery of vessels.

        Examples
        --------
        - 2

        Parameters
        ----------
        lead_time
            Lead time of the vessel in years.
        """
        self.lead_time = assign_value(
            as_scalar(lead_time), type_=(FORECAST, VARIABLE), lower=0.0
        )

    def set_capex(self, capex: float | ForecastInput) -> None:
        """
        Set the base CAPEX of building the vessel in USD.

        Examples
        --------
        - 100e6
        - Forecast("name")

        Parameters
        ----------
        capex
            The base CAPEX of building the vessel in USD.
        """
        self.capex = assign_value(
            as_scalar(capex), type_=(FORECAST, VARIABLE), lower=0.0
        )

    def set_opex(self, opex: float | ForecastInput) -> None:
        """
        Set the base OPEX of maintaining the vessel in USD/year.

        Examples
        --------
        - 10e6
        - Forecast("name")

        Parameters
        ----------
        opex
            The base OPEX of maintaining the vessel in USD/year.
        """
        self.opex = assign_value(as_scalar(opex), type_=(FORECAST, VARIABLE), lower=0.0)

    def set_cost_of_capital(self, cost_of_capital: float | ForecastInput) -> None:
        """
        Set the cost of capital used in calculating the finance costs of the vessel.

        Also used as the discount rate for net present cost calculations for investment
        decisions.

        Examples
        --------
        - 0.1
        - Forecast("name")

        Parameters
        ----------
        cost_of_capital
            Cost of capital.
        """
        self.cost_of_capital = assign_value(
            as_scalar(cost_of_capital), type_=(FORECAST, VARIABLE), lower=0.0
        )

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:

        if not self.tanks:
            no_value_assigned_error(self, "Tanks")

    def initialize_expectation(self, length: int, fuels: dict[str, Fuel]) -> None:
        self.expectation.initialize(length, self.route, fuels)

    def initialize_profile(
        self,
        timeline: np.ndarray,
        emissions: dict[str, Emission],
        fuels: dict[str, Fuel],
        emissions_lifetime: float,
        regulation_names: Sequence[str] = (),
        levy_names: Sequence[str] = (),
    ) -> None:

        self.profile.initialize(
            timeline, emissions, fuels, emissions_lifetime, regulation_names, levy_names
        )

    def calculate_expectation(self, idx: int) -> None:
        self.expectation.set_speeds(idx, [speed.get() for speed in self.route.speeds])

    def calculate_profile(self, idx: int) -> None:
        """
        Write the vessel lifetime and lead time to the profile at idx.

        Parameters
        ----------
        idx
            Current time-step index.
        """
        self.profile.set_lifetime(idx, self.lifetime.get())
        self.profile.set_lead_time(idx, self.lead_time.get())

    def set_fleet_assignment(self, fleet_name: str) -> None:
        """
        Assign the vessel to a fleet, rejecting a second assignment elsewhere.

        Parameters
        ----------
        fleet_name
            Name of the fleet the vessel is assigned to.

        Raises
        ------
        ValueError
            If the vessel is already assigned to a different fleet.
        """
        if self.fleet_assignment is not None:
            raise ValueError(
                f'Fleet("{fleet_name}"): {self} is already assigned to a different'
                f' fleet, Fleet("{self.fleet_assignment}").'
            )

        self.fleet_assignment = fleet_name
