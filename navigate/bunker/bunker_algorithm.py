# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
import timeit
from typing import TYPE_CHECKING

import navigate.bunker.solver as gp
import navigate.core.enum_ as enum_

# cleanup
from navigate.bunker.cleanup import (
    remove_redundant_fuels_from_ports,
    remove_redundant_regulations,
    remove_redundant_vessel,
)
from navigate.bunker.constraints.bunkered_equals_spent import update_bunkered_equals_spent_constraint

# constraints
from navigate.bunker.constraints.energy_conservation import update_energy_conservation_constraints
from navigate.bunker.constraints.mass_conservation import update_mass_conservation_constraints
from navigate.bunker.constraints.mass_sufficient import update_mass_sufficient_constraints
from navigate.bunker.constraints.pilot_fuel import update_pilot_fuel_constraints
from navigate.bunker.constraints.power_capacity import update_power_capacity_constraints
from navigate.bunker.constraints.regulation_flexibility import update_flexibility_regulation_threshold_constraints
from navigate.bunker.constraints.regulation_helpers import (
    update_regulation_flexibility_rhs,
    update_regulation_individual_rhs,
)
from navigate.bunker.constraints.regulation_individual import update_individual_regulation_threshold_constraints
from navigate.bunker.constraints.tank_capacity import update_tank_capacity_constraints

# fair-share
from navigate.bunker.fair_share import (
    perform_flexibility_unit_cost_evaluation,
    run_fair_share_solve,
)
from navigate.bunker.objectives import update_regulation_objectives, update_vessel_objectives
from navigate.bunker.threshold_adjustment import adjust_regulation_thresholds

# transfer
from navigate.bunker.transfer.bunker import transfer_bunker
from navigate.bunker.transfer.dual_solution import transfer_dual_solution
from navigate.bunker.transfer.regulation_properties import calculate_regulation_emission_properties
from navigate.bunker.transfer.regulations_flexibility import transfer_regulations_flexibility
from navigate.bunker.transfer.regulations_individual import transfer_regulations_individual
from navigate.bunker.transfer.regulations_measure import transfer_regulations_measure
from navigate.bunker.transfer.shore_power import transfer_shore_power
from navigate.bunker.transfer.spend_port import transfer_spend_port
from navigate.bunker.transfer.spend_sea import transfer_spend_sea

# variables and objectives
from navigate.bunker.variables import update_regulation_variables, update_vessel_variables

# vessel setup
from navigate.bunker.vessel_setup import (
    build_vessel_specifics,
    calculate_emission_factors,
    calculate_policy_coefficients,
)
from navigate.core.enum_ import BunkerScopeID
from navigate.fuel import get_fuels_per_fuel_type
from navigate.output import log_fair_share_convergence
from navigate.policy import policies_affecting_port

if TYPE_CHECKING:
    import numpy as np

    from navigate.bunker.bunker_options import BunkerOptions
    from navigate.core.enum_ import BunkerScopeID as BunkerScopeIDType
    from navigate.fuel import Emission, Feedstock, Fuel
    from navigate.policy import Levy, Regulation
    from navigate.route import Port
    from navigate.vessel import Vessel
    from navigate.vessel.fleet import Fleet

logger = logging.getLogger(__name__)


class BunkerAlgorithm:
    def __init__(self) -> None:

        # global attributes not linked to a specific vessel ------------------------------------------------------------

        # miscellaneous
        self.scope: BunkerScopeIDType | None = None
        self.options: BunkerOptions | None = None
        self.output_directory: str | None = None

        # time
        self.current_idx: int | None = None
        self.idx: int | None = None
        self.time: float | None = None
        self.time_step: float | None = None

        # global node references
        self.emissions: dict[str, Emission] = {}
        self.feedstock: dict[str, Feedstock] = {}
        self.fleets: dict[str, Fleet] = {}
        self.fuels: dict[str, Fuel] = {}
        self.levies: dict[str, Levy] = {}
        self.ports: dict[str, Port] = {}
        self.regulations: dict[str, Regulation] = {}

        # auxiliary
        self.vessels: dict[str, Vessel] = {}
        self.multipliers: dict[str, float] = {}
        self.fuels_per_fuel_type: dict[str, list[Fuel]] = {}

        # local attributes for a specific vessel -----------------------------------------------------------------------

        # fuel specific
        self.converters: dict[str, dict] = {}
        self.port_converters: dict[str, dict] = {}
        self.usable_fuels: dict[str, dict[str, Fuel]] = {}
        self.converter_fuels: dict[str, dict[str, dict[str, Fuel]]] = {}

        # indices
        self.port_idx: dict[str, tuple[int, ...]] = {}
        self.leg_idx: dict[str, tuple[tuple[int, int], ...]] = {}

        # pre-computed vessel properties
        self.port_name_to_indices: dict[str, dict[str, list[int]]] = {}
        self.efficiency: dict[str, dict[str, float]] = {}
        self.effective_lhv: dict[tuple, float] = {}

        # dynamic properties updated at every time-step ----------------------------------------------------------------

        # policies
        self.cost_levy: dict[tuple, float] = {}
        self.regulation_emission_factor: dict[tuple, float] = {}
        self.regulation_spend_coefficient: dict[tuple, float] = {}
        self.shore_power_regulation_ef: dict[tuple, float] = {}
        self.shore_power_regulation_coeff: dict[tuple, float] = {}
        self.regulation_rhs_individual: dict[tuple, float] = {}
        self.regulation_rhs_flexibility: dict[tuple, float] = {}
        self.regulation_total_rhs_flexibility: dict[str, float] = {}
        self.regulation_measure: dict[tuple, float] = {}

        # convenience containers for easy calculation
        self.regulation_emission_terms: dict[tuple, gp.LinExpr] = {}
        self.regulation_energy_terms: dict[tuple, gp.LinExpr] = {}

        # flexibility units
        self.flexible_unit_cost: dict[str, float] = {}

        # adjusted thresholds (from threshold adjustment)
        self.adjusted_vessel_thresholds: dict[tuple, float] = {}  # (r, v) -> adjusted threshold
        self.adjusted_shared_thresholds: dict[str, float] = {}    # r -> adjusted shared threshold

        # offsetting context (set by manager before build/solve)
        self.offsetting_enabled: bool = False
        self.offsetting_cost: float | None = None

        # emission factors
        self.emission_factor: dict[tuple, float] = {}

        # fair-share fuel properties -----------------------------------------------------------------------------------

        self.previous_bunker: dict[tuple, float] = {}
        self.allocation_fuel: dict[tuple, float] = {}
        self.previously_released_fuel: dict[tuple, bool] = {}
        self.fair_share_convergence_statistics: dict = {}
        self.fs_bunker_keys: list[tuple] | None = None
        self.fs_sol_previous: np.ndarray | None = None
        self.fs_sol_new: np.ndarray | None = None
        self.fs_difference: np.ndarray | None = None

        # primary model attributes -------------------------------------------------------------------------------------

        self.model: gp.Model | None = None

        # vessel variables
        self.bunker: gp.tupledict | None = None
        self.spend_sea: gp.tupledict | None = None
        self.spend_port: gp.tupledict | None = None
        self.mass_tank: gp.tupledict | None = None
        self.shore_power: gp.tupledict | None = None

        # regulation variables
        self.remedial_factor_individual: gp.tupledict | None = None
        self.remedial_factor_flexibility: gp.tupledict | None = None

        # vessel constraints
        self.energy_conservation_sea: gp.tupledict | None = None
        self.energy_conservation_port: gp.tupledict | None = None
        self.power_capacity_sea: gp.tupledict | None = None
        self.power_capacity_port: gp.tupledict | None = None
        self.pilot_fuel_sea: gp.tupledict | None = None
        self.pilot_fuel_port: gp.tupledict | None = None
        self.mass_conservation: gp.tupledict | None = None
        self.mass_sufficient: gp.tupledict | None = None
        self.tank_capacity: gp.tupledict | None = None
        self.bunker_equals_spent: gp.tupledict | None = None
        self.fuel_inertia: gp.tupledict | None = None

        # regulation constraints
        self.regulation_threshold_individual: gp.tupledict | None = None
        self.regulation_threshold_flexibility: gp.tupledict | None = None

        # fair-share constraints
        self.fair_share_fuel: gp.tupledict | None = None

        # timing -------------------------------------------------------------------------------------------------------
        self.build_time: float = 0.
        self.solve_time: float = 0.
        self.transfer_time: float = 0.

    # ==================================================================================================================
    # external methods
    # ==================================================================================================================
    def initialize(
        self,
        emissions: dict[str, Emission],
        feedstock: dict[str, Feedstock],
        fleets: dict[str, Fleet],
        fuels: dict[str, Fuel],
        levies: dict[str, Levy],
        ports: dict[str, Port],
        regulations: dict[str, Regulation],
        options: BunkerOptions,
        scope: BunkerScopeIDType,
        output_directory: str | None = None,
    ) -> None:
        """
        This method initializes an instance of BunkerAlgorithm.
        The method is only called once, namely when the FT simulation is initialized.

        Parameters
        ----------
        fleets
            All fleets in the simulation.
        ports
            All ports in the simulation.
        fuels
            All fuels in the simulation.
        feedstock
            All feedstock in the simulation.
        emissions
            All emissions in the simulation.
        regulations
            All regulations in the simulation.
        levies
            All levies in the simulation.
        options
            Various options relevant to the bunker algorithm.
        scope
            Whether it is expected or existing bunkering.
        output_directory
            Directory for debug output files (typically the deck directory).
        """

        self.scope = scope
        self.options = options
        self.output_directory = output_directory

        # initialize references to dicts in Manager
        self.fleets = fleets
        self.ports = ports
        self.fuels = fuels
        self.feedstock = feedstock
        self.emissions = emissions
        self.regulations = regulations
        self.levies = levies

        # initialize fuel related properties
        self.fuels_per_fuel_type = get_fuels_per_fuel_type(self.fuels)

        # initialize LP model attributes
        self._initialize_model()

    def set_offsetting(self, enabled: bool, cost: float | None) -> None:
        """
        Set the offsetting context for the current time step.

        Parameters
        ----------
        enabled
            Whether offsetting is globally enabled.
        cost
            The global offsetting cost in USD/ton emission, or None if not enabled.
        """
        self.offsetting_enabled = enabled
        self.offsetting_cost = cost

    def build(self, current_idx: int, idx: int, time: float, time_step: float) -> None:
        """
        Build the solver model for the specific time-step.
        If this is the first time the method is called (during the initialization step) the model is built from scratch,
        alternatively variables, objectives and constraints, are updated.

        Parameters
        ----------
        current_idx
            Time-step index at which current or forward bunkering is initiated.
        idx
            Time-step index being evaluated forward in time.
        time
            Time since start of simulation.
        time_step
            Size of the current time-step, days.
        """

        self.build_time = timeit.default_timer()
        self.solve_time = 0
        self.transfer_time = 0

        # assign time-step specific information
        self.current_idx = current_idx
        self.idx = idx
        self.time = time
        self.time_step = time_step

        # reset dynamic properties which will
        # be recalculated from scratch at
        # the current time-step
        self._reset_dynamic_properties()

        # clean old variables
        remove_redundant_fuels_from_ports(self)

        # loop over all vessels and add/update properties
        # if they are active and in the fleet
        for fleet in self.fleets.values():

            for vessel in fleet.get_vessels():

                v = vessel.get_name()

                # during expected bunkering it is necessary to find a solution
                # for every vessel type as the results are used for calculating
                # the uptake metrics of the vessel. In order to ensure a solution,
                # non-existing ships are initialized with a low multiplier to
                # have a limited impact on the overall solution, but still yield
                # a result.
                if self.scope == BunkerScopeID.EXISTING:
                    multiplier = fleet.expectation.get_existing_multipliers(v, self.idx)
                else:
                    multiplier = fleet.expectation.get_expected_multipliers(v, self.idx)

                if multiplier > 0.:

                    # save for later use on global level
                    self.vessels[v] = vessel
                    self.multipliers[v] = multiplier

                    build_vessel_specifics(self, vessel)
                    calculate_emission_factors(self, vessel)
                    calculate_policy_coefficients(self, vessel)

                    # define variables, objectives and constraints for the vessel
                    update_vessel_variables(self, vessel)
                    update_vessel_objectives(self, vessel)
                    self._update_vessel_constraints(vessel)

                else:

                    # previously existing vessel that has now
                    # left the model due to zero multiplier.
                    # Notice this can only occur in existing
                    # bunkering, not expected bunkering
                    if v in self.vessels:
                        remove_redundant_vessel(self, v)

        # calculate the regulatory measure and remove any
        # redundant variables/constraints from previous solves
        update_regulation_individual_rhs(self)
        update_regulation_flexibility_rhs(self)
        remove_redundant_regulations(self)

        # define variables, objectives and constraints for all regulations
        update_regulation_variables(self)
        update_regulation_objectives(self)
        update_individual_regulation_threshold_constraints(self)
        update_flexibility_regulation_threshold_constraints(self)

    def solve(self) -> None:

        # run the fair-share solve loop
        iterations, converged = run_fair_share_solve(self)

        # for offset-enabled regulations with threshold adjustment, capture the
        # pre-adjustment shadow price. Before adjustment, SharedThreshold=0 guarantees
        # remedial_factor > 0 and a shadow price = min(offset_cost, remedial_cost).
        # After adjustment, the relaxed constraint becomes non-binding (shadow price ≈ 0).
        pre_adjustment_cost = {}
        if self.offsetting_enabled:
            for r, constraint in self.regulation_threshold_flexibility.items():
                reg = self.regulations.get(r)
                if (reg is not None
                        and reg.allow_offsetting
                        and reg.allow_threshold_adjustment):
                    pre_adjustment_cost[r] = -constraint.Pi

        # perform threshold adjustment for regulations that allow it
        needs_resolve = adjust_regulation_thresholds(self)

        # if any regulation is non-compliant and has the threshold adjustment
        # flag enabled, update constraints and re-solve with adjusted thresholds
        if needs_resolve:
            iterations, converged = run_fair_share_solve(self)

        # evaluate the flexibility unit cost from the (possibly re-solved) shadow prices
        perform_flexibility_unit_cost_evaluation(self)

        # restore pre-adjustment shadow prices for offset regulations
        for r, cost in pre_adjustment_cost.items():
            self.flexible_unit_cost[r] = cost

        if self.scope == BunkerScopeID.EXISTING:
            log_fair_share_convergence(logger, self.fair_share_convergence_statistics, iterations, converged)

        # the solve involves a lot of build time due to
        # the fair-share iterative algorithm. Solve time
        # is instead accounted for in self.optimize method
        self.build_time = timeit.default_timer() - self.build_time - self.solve_time

    def transfer(self) -> None:

        start = timeit.default_timer()

        # reset the expected fuel mass to allow
        # for updated inertia calculations
        for vessel in self.vessels.values():
            vessel.expectation.reset_bunker_mass_expected()

        for port in self.ports.values():
            port.expectation.reset_bunker_mass_expected()

        if self.scope == BunkerScopeID.EXISTING:

            for vessel in self.vessels.values():
                vessel.expectation.reset_bunker_mass_existing()

            for port in self.ports.values():
                port.expectation.reset_bunker_mass_existing()

        # transfer vessel solutions
        transfer_bunker(self)
        transfer_spend_sea(self)
        transfer_spend_port(self)
        transfer_shore_power(self)

        if self.scope == BunkerScopeID.EXPECTED:
            transfer_dual_solution(self)

        # transfer regulations. Notice that regulation measures
        # must be calculated prior to the others as part of the
        # results are used in subsequent calculations
        properties = calculate_regulation_emission_properties(self)
        transfer_regulations_measure(self, properties)
        transfer_regulations_individual(self)
        transfer_regulations_flexibility(self, properties)

        end = timeit.default_timer()
        self.transfer_time = end - start

    # ==================================================================================================================
    # internal methods
    # ==================================================================================================================
    def _initialize_model(self) -> None:
        """
        Initialize the LP model as well as containers used for storing LP variables and constraints.
        This method is only called once, namely when the high-level initialization occurs.
        """

        # initialize LP model
        if self.scope == BunkerScopeID.EXISTING:
            model_name = "existing"
        else:
            model_name = "expected"

        self.model = gp.Model(model_name)

        self.model.Params.OutputFlag = 0   # suppress solver console output
        self.model.Params.Method = self.options.get_solver_method().value  # using the integer value directly
        self.model.Params.Threads = self.options.get_threads()
        self.model.Params.FeasibilityTol = self.options.get_solution_tolerance()
        self.model.Params.OptimalityTol = self.options.get_solution_tolerance()

        # initialize primary LP variables
        self.bunker = gp.tupledict()
        self.spend_sea = gp.tupledict()
        self.spend_port = gp.tupledict()
        self.mass_tank = gp.tupledict()
        self.shore_power = gp.tupledict()
        self.remedial_factor_individual = gp.tupledict()
        self.remedial_factor_flexibility = gp.tupledict()

        # initialize primary LP constraints
        self.energy_conservation_sea = gp.tupledict()
        self.energy_conservation_port = gp.tupledict()
        self.power_capacity_sea = gp.tupledict()
        self.power_capacity_port = gp.tupledict()
        self.pilot_fuel_sea = gp.tupledict()
        self.pilot_fuel_port = gp.tupledict()
        self.mass_conservation = gp.tupledict()
        self.mass_sufficient = gp.tupledict()
        self.tank_capacity = gp.tupledict()
        self.bunker_equals_spent = gp.tupledict()
        self.fuel_inertia = gp.tupledict()
        self.fair_share_fuel = gp.tupledict()
        self.regulation_threshold_individual = gp.tupledict()
        self.regulation_threshold_flexibility = gp.tupledict()

    def _reset_dynamic_properties(self) -> None:
        """
        Certain properties are dynamic and recalculated at every time-step. The containers holding these properties are
        reset to avoid the risk of values from previous time-steps remaining.
        """

        # reset policy coefficients
        self.regulation_emission_factor = {}
        self.regulation_emission_coefficient = {}
        self.cost_levy = {}

        # reset regulation measurements
        self.regulation_rhs_individual = {}
        self.regulation_rhs_flexibility = {}
        self.regulation_total_rhs_flexibility = {}
        self.regulation_emission_terms = {}
        self.regulation_energy_terms = {}
        self.flexible_unit_cost = {}

        # reset adjusted thresholds
        self.adjusted_vessel_thresholds = {}
        self.adjusted_shared_thresholds = {}

        # reset emission reduction coefficients
        self.emission_factor = {}

        # pre-filter active policies
        self.active_regulations = {r: reg for r, reg in self.regulations.items() if reg.is_active()}
        self.port_levies = {}
        for port_name, port in self.ports.items():
            self.port_levies[port_name] = policies_affecting_port(port, self.levies)

    def _update_vessel_constraints(self, vessel: Vessel) -> None:
        """
        Update all constraints pertaining to a specific vessel.

        Parameters
        ----------
        vessel
            Vessel for which constraints are updated.
        """

        # add vessel technical constraints
        update_energy_conservation_constraints(self, vessel)
        update_power_capacity_constraints(self, vessel)
        update_pilot_fuel_constraints(self, vessel)

        # add mass conservation constraints
        if vessel.route.route_type == enum_.RouteTypeID.ROUND_TRIP:

            update_mass_conservation_constraints(self, vessel)
            update_mass_sufficient_constraints(self, vessel)
            update_tank_capacity_constraints(self, vessel)

        # ensure all fuel is spent on each voyage
        update_bunkered_equals_spent_constraint(self, vessel)

    def get_build_time(self) -> float:
        return self.build_time

    def get_solve_time(self) -> float:
        return self.solve_time

    def get_transfer_time(self) -> float:
        return self.transfer_time
