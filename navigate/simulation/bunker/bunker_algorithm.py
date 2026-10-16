# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Bunkering LP of one scope, built, solved and transferred at every time step.

``Simulation`` runs one instance for existing and one for expected bunkering;
the other modules of the package build, solve and transfer through it.
"""

from __future__ import annotations

import logging
import timeit
from typing import TYPE_CHECKING

import numpy as np

import navigate.simulation.bunker.solver as gp
from navigate.core import get_fuels_per_fuel_type
from navigate.core.enum_ import BunkerScopeID
from navigate.simulation.bunker.cleanup import (
    remove_redundant_fuels_from_ports,
    remove_redundant_regulations,
    remove_redundant_vessel,
)
from navigate.simulation.bunker.coefficients import update_regulation_spend_coefficients
from navigate.simulation.bunker.constraints.bunkered_equals_spent import (
    update_bunkered_equals_spent_constraint,
)
from navigate.simulation.bunker.constraints.energy_conservation import (
    update_energy_conservation_constraints,
)
from navigate.simulation.bunker.constraints.mass_conservation import (
    update_mass_conservation_constraints,
)
from navigate.simulation.bunker.constraints.mass_sufficient import (
    update_mass_sufficient_constraints,
)
from navigate.simulation.bunker.constraints.pilot_fuel import (
    update_pilot_fuel_constraints,
)
from navigate.simulation.bunker.constraints.regulation_flexibility import (
    update_flexibility_regulation_threshold_constraints,
)
from navigate.simulation.bunker.constraints.regulation_individual import (
    update_individual_regulation_threshold_constraints,
)
from navigate.simulation.bunker.constraints.regulation_terms import (
    update_regulation_flexibility_rhs,
    update_regulation_individual_rhs,
)
from navigate.simulation.bunker.constraints.tank_capacity import (
    update_tank_capacity_constraints,
)
from navigate.simulation.bunker.fair_share import run_fair_share_solve
from navigate.simulation.bunker.objectives import (
    update_regulation_objectives,
    update_vessel_objectives,
)
from navigate.simulation.bunker.threshold_adjustment import adjust_regulation_thresholds
from navigate.simulation.bunker.transfer.allocation_fuel import transfer_allocation_fuel
from navigate.simulation.bunker.transfer.bunker import transfer_bunker
from navigate.simulation.bunker.transfer.dual_solution import transfer_dual_solution
from navigate.simulation.bunker.transfer.regulation_solution import (
    transfer_regulation_solution,
)
from navigate.simulation.bunker.transfer.shore_power import transfer_shore_power
from navigate.simulation.bunker.transfer.spend_port import transfer_spend_port
from navigate.simulation.bunker.transfer.spend_sea import transfer_spend_sea
from navigate.simulation.bunker.variables import (
    update_regulation_variables,
    update_vessel_variables,
)

if TYPE_CHECKING:
    from pathlib import Path

    from navigate.core.enum_ import EnergyDemandID, FuelTypeID
    from navigate.core.general_nodes.bunker_options import BunkerOptions
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.fair_share import FairShareSolutions
    from navigate.util.types_ import FloatLike

logger = logging.getLogger(__name__)


def _is_admitted(multiplier: FloatLike) -> bool:
    """
    Check whether a vessel multiplier admits the vessel into a bunkering LP.

    A vessel enters the LP of its step only with a positive multiplier. Expected
    bunkering needs a solution for every vessel type, as its results feed the uptake
    metrics of the vessel; vessel types not in the fleet therefore carry a low
    multiplier, so every vessel type enters the expected LPs, while existing bunkering
    drops a vessel whose multiplier is zero.

    Parameters
    ----------
    multiplier
        Multiplier of the vessel at one time step or over several.

    Returns
    -------
    bool
        True if the multiplier is positive at any of the steps.
    """
    return bool(np.max(multiplier) > 0.0)


class BunkerAlgorithm:
    """Build, solve and transfer the bunkering LP of one scope at every time step."""

    def __init__(self) -> None:

        # global attributes not linked to a specific vessel ----------------------------

        # miscellaneous
        self.scope: BunkerScopeID
        self.options: BunkerOptions
        self.output_directory: Path

        # time
        self.current_idx: int
        self.idx: int
        self.time: float
        self.time_step: float

        # global node references
        self.emissions: dict[str, Emission] = {}
        self.feedstock: dict[str, Feedstock] = {}
        self.fleets: dict[str, Fleet] = {}
        self.fuels: dict[str, Fuel] = {}
        self.ports: dict[str, Port] = {}
        self.regulations: dict[str, Regulation] = {}

        # auxiliary
        self.vessels: dict[str, Vessel] = {}
        self.multipliers: dict[str, float] = {}
        self.fuels_per_fuel_type: dict[FuelTypeID, list[Fuel]] = {}

        # dynamic properties updated at every time-step --------------------------------

        # policies
        self.active_regulations: dict[str, Regulation] = {}
        self.regulation_spend_coefficient: dict[tuple[str, str, str, str], float] = {}
        self.shore_power_regulation_coefficient: dict[tuple[str, int, str], float] = {}
        self.regulation_rhs_individual: dict[tuple[str, str], float] = {}
        self.regulation_total_rhs_flexibility: dict[str, float] = {}

        # regulation emission and energy terms per (regulation, vessel)
        self.regulation_emission_terms: dict[tuple[str, str], gp.LinExpr] = {}
        self.regulation_energy_terms: dict[tuple[str, str], gp.LinExpr] = {}

        # thresholds after threshold adjustment, per (regulation, vessel) and per
        # regulation
        self.adjusted_vessel_thresholds: dict[tuple[str, str], float] = {}
        self.adjusted_shared_thresholds: dict[str, float] = {}

        # fair-share fuel properties ---------------------------------------------------

        self.previous_bunker: dict[tuple[str, int, str], float] = {}
        self.allocation_fuel: dict[tuple[str, str, str], float] = {}
        self.previously_released_fuel: dict[tuple[str, str, str], bool] = {}
        self.fair_share_convergence_statistics: dict[str, list[float]] = {}
        self.fair_share_solutions: FairShareSolutions | None = None

        # primary model attributes -----------------------------------------------------

        self.model: gp.Model

        # vessel variables
        self.bunker: dict[tuple[str, int, str], gp.Var]
        self.spend_sea: dict[tuple[str, str, str, int, int], gp.Var]
        self.spend_port: dict[tuple[str, str, str, int], gp.Var]
        self.mass_tank: dict[tuple[str, int, str], gp.Var]
        self.shore_power: dict[tuple[str, int], gp.Var]

        # regulation variables
        self.remedial_factor_individual: dict[tuple[str, str], gp.Var]
        self.remedial_factor_flexibility: dict[str, gp.Var]

        # vessel constraints
        self.energy_conservation_sea: dict[
            tuple[str, int, int, EnergyDemandID], gp.Constr
        ]
        self.energy_conservation_port: dict[tuple[str, int, EnergyDemandID], gp.Constr]
        self.pilot_fuel_sea: dict[tuple[str, str, int, int], gp.Constr]
        self.pilot_fuel_port: dict[tuple[str, str, int], gp.Constr]
        self.mass_conservation: dict[tuple[str, int, str], gp.Constr]
        self.mass_sufficient: dict[tuple[str, int, str], gp.Constr]
        self.tank_capacity: dict[tuple[str, int, str], gp.Constr]
        self.bunker_equals_spent: dict[tuple[str, str], gp.Constr]
        self.fuel_inertia: dict[tuple[str, str, str], gp.Constr]

        # regulation constraints
        self.regulation_threshold_individual: dict[tuple[str, str], gp.Constr]
        self.regulation_threshold_flexibility: dict[str, gp.Constr]

        # fair-share constraints
        self.fair_share_fuel: dict[tuple[str, str, str], gp.Constr]

        # timing -----------------------------------------------------------------------
        self.build_time: float = 0.0
        self.solve_time: float = 0.0
        self.transfer_time: float = 0.0

    def initialize(
        self,
        emissions: dict[str, Emission],
        feedstock: dict[str, Feedstock],
        fleets: dict[str, Fleet],
        fuels: dict[str, Fuel],
        ports: dict[str, Port],
        regulations: dict[str, Regulation],
        options: BunkerOptions,
        scope: BunkerScopeID,
        output_directory: Path,
    ) -> None:
        """
        Initialize the algorithm once, when the simulation is initialized.

        Parameters
        ----------
        emissions
            All emissions in the simulation.
        feedstock
            All feedstock in the simulation.
        fleets
            All fleets in the simulation.
        fuels
            All fuels in the simulation.
        ports
            All ports in the simulation.
        regulations
            All regulations in the simulation.
        options
            Settings of the bunker algorithm.
        scope
            Whether the algorithm bunkers the existing or the expected fleet.
        output_directory
            Directory the LP files of an infeasible model are written to.
        """
        self.scope = scope
        self.options = options
        self.output_directory = output_directory

        self.fleets = fleets
        self.ports = ports
        self.fuels = fuels
        self.feedstock = feedstock
        self.emissions = emissions
        self.regulations = regulations

        self.fuels_per_fuel_type = get_fuels_per_fuel_type(self.fuels)

        self._initialize_model()

    def build(self, current_idx: int, idx: int, time: float, time_step: float) -> None:
        """
        Build the LP model for a time step.

        The first call adds every variable and constraint; later calls update them and
        add or remove those whose vessels, fuels or regulations came or went.

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

        self.current_idx = current_idx
        self.idx = idx
        self.time = time
        self.time_step = time_step

        self._reset_dynamic_properties()

        remove_redundant_fuels_from_ports(self)

        for fleet in self.fleets.values():
            for vessel in fleet.vessels:
                v = vessel.name

                multiplier = fleet.expectation.get_multiplier(v, self.scope, self.idx)

                if _is_admitted(multiplier):
                    self.vessels[v] = vessel
                    self.multipliers[v] = np.float64(multiplier)

                    update_regulation_spend_coefficients(self, vessel)

                    update_vessel_variables(self, vessel)
                    update_vessel_objectives(self, vessel)
                    self._update_vessel_constraints(vessel)

                elif v in self.vessels:
                    # a zero multiplier, which only existing bunkering gives, drops a
                    # vessel that was in the model at an earlier time step
                    remove_redundant_vessel(self, v)

        update_regulation_individual_rhs(self)
        update_regulation_flexibility_rhs(self)
        remove_redundant_regulations(self)

        update_regulation_variables(self)
        update_regulation_objectives(self)
        update_individual_regulation_threshold_constraints(self)
        update_flexibility_regulation_threshold_constraints(self)

    def solve(self) -> None:
        """
        Solve the LP with fair-share iterations.

        A regulation that is non-compliant and allows threshold adjustment has its
        threshold adjusted, and the LP is solved again against the adjusted thresholds.
        """
        converged = run_fair_share_solve(self)

        if adjust_regulation_thresholds(self):
            converged = run_fair_share_solve(self)

        if self.scope == BunkerScopeID.EXISTING:
            self._log_fair_share_convergence(converged)

        # the fair-share iterations rebuild constraints between solves; that time
        # counts as build time, while optimize accumulates the solve time
        self.build_time = timeit.default_timer() - self.build_time - self.solve_time

    def transfer(self) -> None:
        """Transfer the LP solution to the expectations and profiles of the nodes."""
        start = timeit.default_timer()

        if self.scope == BunkerScopeID.EXISTING:
            # transfer_bunker accumulates the existing bunker masses, which the fuel
            # inertia constraints read, so they restart from zero at every transfer
            for vessel in self.vessels.values():
                vessel.expectation.reset_bunker_mass_existing()

            # every vessel's spent energy restarts, as a vessel out of the LP
            # spends none
            for fleet in self.fleets.values():
                for vessel in fleet.vessels:
                    vessel.expectation.reset_spend_energy()

        transfer_bunker(self)
        transfer_spend_sea(self)
        transfer_spend_port(self)
        transfer_shore_power(self)
        transfer_allocation_fuel(self)

        if self.scope == BunkerScopeID.EXPECTED:
            transfer_dual_solution(self)

        transfer_regulation_solution(self)

        end = timeit.default_timer()
        self.transfer_time = end - start

    def get_admitted_vessels(self, current_idx: int) -> list[Vessel]:
        """
        Get the vessels that enter at least one LP built from a time step.

        Existing bunkering builds one LP, at the time step itself; expected bunkering
        builds one for every step of the remaining horizon.

        Parameters
        ----------
        current_idx
            Time-step index at which current or forward bunkering is initiated.

        Returns
        -------
        list[Vessel]
            Vessels of every fleet with a positive multiplier in a built LP.
        """
        is_existing = self.scope == BunkerScopeID.EXISTING
        steps = current_idx if is_existing else np.s_[current_idx:]

        admitted = []

        for fleet in self.fleets.values():
            for vessel in fleet.vessels:
                v = vessel.name
                multiplier = fleet.expectation.get_multiplier(v, self.scope, steps)

                if _is_admitted(multiplier):
                    admitted.append(vessel)

        return admitted

    def _initialize_model(self) -> None:
        """Create the LP model and its empty variable and constraint containers."""
        model_name = "existing" if self.scope == BunkerScopeID.EXISTING else "expected"

        self.model = gp.create_model(model_name)

        self.model.Params.OutputFlag = 0
        self.model.Params.Method = self.options.solver_method.value
        self.model.Params.Threads = self.options.threads
        self.model.Params.FeasibilityTol = self.options.solution_tolerance
        self.model.Params.OptimalityTol = self.options.solution_tolerance

        self.bunker = {}
        self.spend_sea = {}
        self.spend_port = {}
        self.mass_tank = {}
        self.shore_power = {}
        self.remedial_factor_individual = {}
        self.remedial_factor_flexibility = {}

        self.energy_conservation_sea = {}
        self.energy_conservation_port = {}
        self.pilot_fuel_sea = {}
        self.pilot_fuel_port = {}
        self.mass_conservation = {}
        self.mass_sufficient = {}
        self.tank_capacity = {}
        self.bunker_equals_spent = {}
        self.fuel_inertia = {}
        self.fair_share_fuel = {}
        self.regulation_threshold_individual = {}
        self.regulation_threshold_flexibility = {}

    def _reset_dynamic_properties(self) -> None:
        """Reset the containers recalculated at every time step, so none goes stale."""
        self.regulation_spend_coefficient = {}
        self.shore_power_regulation_coefficient = {}

        self.regulation_rhs_individual = {}
        self.regulation_total_rhs_flexibility = {}
        self.regulation_emission_terms = {}
        self.regulation_energy_terms = {}

        self.adjusted_vessel_thresholds = {}
        self.adjusted_shared_thresholds = {}

        self.active_regulations = {
            r: reg for r, reg in self.regulations.items() if reg.is_active()
        }

    def _update_vessel_constraints(self, vessel: Vessel) -> None:
        """
        Update all constraints of a vessel.

        Parameters
        ----------
        vessel
            Vessel for which constraints are updated.
        """
        update_energy_conservation_constraints(self, vessel)
        update_pilot_fuel_constraints(self, vessel)

        update_mass_conservation_constraints(self, vessel)
        update_mass_sufficient_constraints(self, vessel)
        update_tank_capacity_constraints(self, vessel)

        update_bunkered_equals_spent_constraint(self, vessel)

    def _log_fair_share_convergence(self, converged: bool) -> None:
        """
        Log the outcome of the fair-share iterations, with a table of their statistics.

        Parameters
        ----------
        converged
            Whether the iterations reached the convergence criterion.
        """
        statistics = self.fair_share_convergence_statistics
        iterations = len(statistics["Norm"])
        table = {"Iter.": range(1, iterations + 1), **statistics}

        if converged:
            logger.info("Fair-share bunkering convergence status: Successful.")
            logger.debug(
                "Fair-share bunkering convergence statistics:", extra={"table": table}
            )
        else:
            logger.info(
                "Fair-share bunkering convergence status: Failure.\n"
                "Fair-share bunkering convergence statistics:",
                extra={"table": table},
            )
