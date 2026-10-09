# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Vessel node, one vessel type with its loads, machinery and route."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    Scalar,
    as_scalar,
    assign_id,
    assign_reference,
    assign_reference_list,
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
from navigate.exceptions import UnassignedAttributeError

if TYPE_CHECKING:
    from collections.abc import Sequence

    import numpy as np

    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.power_system import PowerSystem
    from navigate.core.nodes.route import Route
    from navigate.core.nodes.tank import Tank
    from navigate.core.types_ import (
        ForecastArgument,
        ForecastInput,
        ScalarArgument,
        ScalarInput,
        SurfaceArgument,
        SurfaceInput,
    )


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
        self.power_system: PowerSystem
        self.tanks: list[Tank] = []

        # voyage
        self.route: Route
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
        self.primary_fuel_type: FuelTypeID
        self.usable_fuel_types: list[FuelTypeID] = []
        self.usable_fuels: dict[str, Fuel] = {}
        self.fleet_assignment: str

    # external methods (DSL attributes) ------------------------------------------------
    def set_propulsion_load(self, propulsion_load: SurfaceArgument) -> None:
        """Set the propulsion load of the vessel."""
        self.propulsion_load = assign_value(
            as_scalar(propulsion_load), type_=(CURVE, SURFACE, VARIABLE), lower=0.0
        )

    def set_electrical_load_at_sea(
        self, electrical_load_at_sea: SurfaceArgument
    ) -> None:
        """Set the electrical load of the vessel at sea."""
        self.electrical_load_at_sea = assign_value(
            as_scalar(electrical_load_at_sea),
            type_=(CURVE, SURFACE, VARIABLE),
            lower=0.0,
        )

    def set_electrical_load_in_port(
        self, electrical_load_in_port: ScalarArgument
    ) -> None:
        """Set the electrical load of the vessel in port."""
        self.electrical_load_in_port = assign_value(
            as_scalar(electrical_load_in_port), type_=VARIABLE, lower=0.0
        )

    def set_heat_load_at_sea(self, heat_load_at_sea: SurfaceArgument) -> None:
        """Set the heat load of the vessel at sea."""
        self.heat_load_at_sea = assign_value(
            as_scalar(heat_load_at_sea), type_=(CURVE, SURFACE, VARIABLE), lower=0.0
        )

    def set_heat_load_in_port(self, heat_load_in_port: ScalarArgument) -> None:
        """Set the heat load of the vessel in port."""
        self.heat_load_in_port = assign_value(
            as_scalar(heat_load_in_port), type_=VARIABLE, lower=0.0
        )

    def set_fuel_type(self, fuel_type: str) -> None:
        """Set the primary main fuel type of the vessel."""
        self.fuel_type = assign_id(fuel_type, FuelTypeID)

    def set_power_system(self, power_system: PowerSystem) -> None:
        """Set the power system converting fuel to energy."""
        self.power_system = assign_reference(power_system, POWER_SYSTEM)

    def set_tanks(self, tanks: Tank | list[Tank]) -> None:
        """Set the tanks used for onboard fuel storage."""
        self.tanks = assign_reference_list(tanks, TANK, unique=True)

    def set_route(self, route: Route) -> None:
        """Set the route the vessel sails on."""
        self.route = assign_reference(route, ROUTE)

    def set_nominal_capacity(self, nominal_capacity: ScalarArgument) -> None:
        """Set the nominal cargo carrying capacity of the vessel."""
        self.nominal_capacity = assign_value(
            as_scalar(nominal_capacity), type_=VARIABLE, lower=0.0
        )

    def set_lifetime(self, lifetime: ForecastArgument) -> None:
        """Set the lifetime of the vessel."""
        self.lifetime = assign_value(
            as_scalar(lifetime),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    def set_lead_time(self, lead_time: ForecastArgument) -> None:
        """Set the lead time of the vessel."""
        self.lead_time = assign_value(
            as_scalar(lead_time), type_=(FORECAST, VARIABLE), lower=0.0
        )

    def set_capex(self, capex: ForecastArgument) -> None:
        """Set the base CAPEX of building the vessel."""
        self.capex = assign_value(
            as_scalar(capex), type_=(FORECAST, VARIABLE), lower=0.0
        )

    def set_opex(self, opex: ForecastArgument) -> None:
        """Set the base OPEX of maintaining the vessel."""
        self.opex = assign_value(as_scalar(opex), type_=(FORECAST, VARIABLE), lower=0.0)

    def set_cost_of_capital(self, cost_of_capital: ForecastArgument) -> None:
        """Set the cost of capital of the vessel."""
        self.cost_of_capital = assign_value(
            as_scalar(cost_of_capital), type_=(FORECAST, VARIABLE), lower=0.0
        )

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:

        if not self.tanks:
            raise UnassignedAttributeError(str(self), "Tanks")

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
