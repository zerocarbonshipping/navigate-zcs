# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Bunkering LP of one scope, built, solved and transferred at every time step.

``Simulation`` runs one instance for existing and one for expected bunkering;
the other modules of the package build, solve and transfer through it.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

import navigate.simulation.bunker.solver as gp
from navigate.core import get_fuels_per_fuel_type
from navigate.core.enum_ import BunkerScopeID, TimingID
from navigate.simulation.bunker.cleanup import (
    remove_redundant_fuels_from_ports,
    remove_redundant_regulations,
    remove_redundant_vessel,
)
from navigate.simulation.bunker.constraints.bunkered_equals_spent import (
    update_bunkered_equals_spent_constraints,
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
from navigate.util import timed

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from navigate.core.enum_ import EnergyDemandID, FuelTypeID
    from navigate.core.general_nodes.bunker_options import BunkerOptions
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.fair_share import FairShareSolutions
    from navigate.util import Timings
    from navigate.util.types_ import FloatLike, Index

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


def _create_model(scope: BunkerScopeID, options: BunkerOptions) -> gp.Model:
    """
    Create the empty LP model of a scope, set up with the solver options.

    Parameters
    ----------
    scope
        Whether the model bunkers the existing or the expected fleet.
    options
        Settings of the bunker algorithm.

    Returns
    -------
    gp.Model
        The model, named after its scope.
    """
    model_name = "existing" if scope == BunkerScopeID.EXISTING else "expected"

    model = gp.create_model(model_name)

    model.Params.OutputFlag = 0
    model.Params.Method = options.solver_method.value
    model.Params.Threads = options.threads
    model.Params.FeasibilityTol = options.solution_tolerance
    model.Params.OptimalityTol = options.solution_tolerance

    return model


class BunkerAlgorithm:
    """
    Build, solve and transfer the bunkering LP of one scope at every time step.

    Parameters
    ----------
    emissions
        All emissions in the simulation.
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
    timings
        Timings the build, solve and transfer are booked to.
    """

    def __init__(
        self,
        emissions: dict[str, Emission],
        fleets: dict[str, Fleet],
        fuels: dict[str, Fuel],
        ports: dict[str, Port],
        regulations: dict[str, Regulation],
        options: BunkerOptions,
        scope: BunkerScopeID,
        output_directory: Path,
        timings: Timings[TimingID],
    ) -> None:

        # global attributes not linked to a specific vessel ----------------------------

        # miscellaneous
        self.scope: BunkerScopeID = scope
        self.options: BunkerOptions = options
        self.output_directory: Path = output_directory
        self.timings: Timings[TimingID] = timings

        # time
        self.current_idx: int
        self.idx: int
        self.time: float
        self.time_step: float

        # global node references
        self.emissions: dict[str, Emission] = emissions
        self.fleets: dict[str, Fleet] = fleets
        self.fuels: dict[str, Fuel] = fuels
        self.ports: dict[str, Port] = ports
        self.regulations: dict[str, Regulation] = regulations

        # auxiliary
        self.vessels: dict[str, Vessel] = {}
        self.multipliers: dict[str, float] = {}
        self.fuels_per_fuel_type: dict[FuelTypeID, list[Fuel]] = (
            get_fuels_per_fuel_type(fuels)
        )

        # dynamic properties updated at every time-step --------------------------------

        # policies
        self.active_regulations: dict[str, Regulation]
        self.regulated_shore_power: set[tuple[str, int]]
        self.regulation_rhs_individual: dict[tuple[str, str], float]
        self.regulation_total_rhs_flexibility: dict[str, float]

        # regulation emission and energy terms per (regulation, vessel)
        self.regulation_emission_terms: dict[tuple[str, str], gp.LinExpr]
        self.regulation_energy_terms: dict[tuple[str, str], gp.LinExpr]

        # fair-share fuel properties ---------------------------------------------------

        self.previous_bunker: dict[tuple[str, int, str], float]
        self.allocation_fuel: dict[tuple[str, str, str], float]
        self.previously_released_fuel: dict[tuple[str, str, str], bool]
        self.fair_share_convergence_statistics: dict[str, list[float]]
        self.fair_share_converged: bool
        self.fair_share_solutions: FairShareSolutions | None

        # primary model attributes -----------------------------------------------------

        self.model: gp.Model = _create_model(scope, options)

        # vessel variables
        self.bunker: dict[tuple[str, int, str], gp.Var] = {}
        self.spend_sea: dict[tuple[str, str, str, int, int], gp.Var] = {}
        self.spend_port: dict[tuple[str, str, str, int], gp.Var] = {}
        self.mass_tank: dict[tuple[str, int, str], gp.Var] = {}
        self.shore_power: dict[tuple[str, int], gp.Var] = {}

        # regulation variables
        self.remedial_factor_individual: dict[tuple[str, str], gp.Var] = {}
        self.remedial_factor_flexibility: dict[str, gp.Var] = {}

        # vessel constraints
        self.energy_conservation_sea: dict[
            tuple[str, int, int, EnergyDemandID], gp.Constr
        ] = {}
        self.energy_conservation_port: dict[
            tuple[str, int, EnergyDemandID], gp.Constr
        ] = {}
        self.pilot_fuel_sea: dict[tuple[str, str, int, int], gp.Constr] = {}
        self.pilot_fuel_port: dict[tuple[str, str, int], gp.Constr] = {}
        self.mass_conservation: dict[tuple[str, int, str], gp.Constr] = {}
        self.mass_sufficient: dict[tuple[str, int, str], gp.Constr] = {}
        self.tank_capacity: dict[tuple[str, int, str], gp.Constr] = {}
        self.bunker_equals_spent: dict[tuple[str, str], gp.Constr] = {}
        self.fuel_inertia: dict[tuple[str, str, str], gp.Constr] = {}

        # regulation constraints
        self.regulation_threshold_individual: dict[tuple[str, str], gp.Constr] = {}
        self.regulation_threshold_flexibility: dict[str, gp.Constr] = {}

        # fair-share constraints
        self.fair_share_fuel: dict[tuple[str, str, str], gp.Constr] = {}

    @timed(TimingID.LP_BUILD)
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
        self.current_idx = current_idx
        self.idx = idx
        self.time = time
        self.time_step = time_step

        self._reset_dynamic_properties()
        remove_redundant_fuels_from_ports(self)

        for vessel, multiplier in self._vessel_multipliers(self.idx):
            self._update_vessel(vessel, multiplier)

        update_regulation_individual_rhs(self)
        update_regulation_flexibility_rhs(self)
        remove_redundant_regulations(self)

        update_regulation_variables(self)
        update_regulation_objectives(self)
        update_individual_regulation_threshold_constraints(self)
        update_flexibility_regulation_threshold_constraints(self)

    @timed(TimingID.LP_BUILD)
    def update_regulation_constraints(self) -> None:
        """Update the regulation constraints to the regulation inputs of the step."""
        update_regulation_individual_rhs(self)
        update_regulation_flexibility_rhs(self)
        update_individual_regulation_threshold_constraints(self)
        update_flexibility_regulation_threshold_constraints(self)

    @timed(TimingID.LP_BUILD)
    def solve(self) -> None:
        """
        Solve the LP with fair-share iterations.

        The constraint rebuilds between the iterations count as build time; optimize
        books the solves themselves.
        """
        self.fair_share_converged = run_fair_share_solve(self)

    @timed(TimingID.LP_TRANSFER)
    def transfer_regulation_solution(self) -> None:
        """Transfer the regulation results of the LP solution to the regulations."""
        transfer_regulation_solution(self)

    @timed(TimingID.LP_TRANSFER)
    def transfer(self) -> None:
        """Transfer the LP solution to the expectations and results of the nodes."""
        if self.scope == BunkerScopeID.EXISTING:
            # logged once per LP, for the solve its solution comes from
            self._log_fair_share_convergence()

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

        for vessel, multiplier in self._vessel_multipliers(steps):
            if _is_admitted(multiplier):
                admitted.append(vessel)

        return admitted

    def _vessel_multipliers(self, steps: Index) -> Iterator[tuple[Vessel, FloatLike]]:
        """
        Walk every vessel of the fleets with its multiplier in this scope.

        Parameters
        ----------
        steps
            Time-step index, or indices, the multipliers are read at.

        Yields
        ------
        tuple[Vessel, FloatLike]
            Vessel and its multiplier at the steps.
        """
        for fleet in self.fleets.values():
            expectation = fleet.expectation

            for vessel in fleet.vessels:
                multiplier = expectation.get_multiplier(vessel.name, self.scope, steps)
                yield vessel, multiplier

    def _reset_dynamic_properties(self) -> None:
        """Reset the containers recalculated at every time step, so none goes stale."""
        self.regulated_shore_power = set()

        self.regulation_rhs_individual = {}
        self.regulation_total_rhs_flexibility = {}
        self.regulation_emission_terms = {}
        self.regulation_energy_terms = {}

        self.active_regulations = {}

        for key, value in self.regulations.items():
            if value.is_active():
                self.active_regulations[key] = value

    def _update_vessel(self, vessel: Vessel, multiplier: FloatLike) -> None:
        """
        Update a vessel in the LP if its multiplier admits it, or else drop it.

        A zero multiplier, which only existing bunkering gives, drops a vessel that was
        in the model at an earlier time step.

        Parameters
        ----------
        vessel
            Vessel whose variables, objectives and constraints are updated.
        multiplier
            Multiplier of the vessel at the time step being built.
        """
        v = vessel.name

        if _is_admitted(multiplier):
            self.vessels[v] = vessel
            self.multipliers[v] = np.float64(multiplier)

            # registered before the vessel's variables are added, on purpose
            self._update_regulated_shore_power(vessel)

            update_vessel_variables(self, vessel)
            update_vessel_objectives(self, vessel)
            self._update_vessel_constraints(vessel)

        elif v in self.vessels:
            remove_redundant_vessel(self, v)

    def _update_regulated_shore_power(self, vessel: Vessel) -> None:
        """
        Add the vessel's shore-power connections in the model to those regulated.

        Only these are weighed by the regulation rows: a connection whose variable
        this build adds is not weighed until the next build. That is a known defect,
        kept so results do not move.

        Parameters
        ----------
        vessel
            Vessel whose connections are added.
        """
        v = vessel.name

        for p in range(len(vessel.route.ports)):
            if (v, p) in self.shore_power:
                self.regulated_shore_power.add((v, p))

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

        update_bunkered_equals_spent_constraints(self, vessel)

    def _log_fair_share_convergence(self) -> None:
        """Log the outcome of the last fair-share iterations, with their statistics."""
        statistics = self.fair_share_convergence_statistics
        iterations = len(statistics["Norm"])
        table = {"Iter.": range(1, iterations + 1), **statistics}

        if self.fair_share_converged:
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
