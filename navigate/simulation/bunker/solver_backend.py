# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Choosing the solver backend and building models on it."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from navigate.core.enum_ import SolverBackendID
from navigate.simulation.bunker.solver_gurobi import GurobiModel, is_gurobi_licensed
from navigate.simulation.bunker.solver_highs import HighsModel

if TYPE_CHECKING:
    from navigate.core.general_nodes.bunker_options import BunkerOptions
    from navigate.simulation.bunker.solver import Model

logger = logging.getLogger(__name__)


def select_backend(preference: SolverBackendID) -> SolverBackendID:
    """
    Resolve a backend preference to Gurobi, when it is licensed, or HiGHS.

    Parameters
    ----------
    preference
        AUTOMATIC, GUROBI or HIGHS.

    Returns
    -------
    SolverBackendID
        GUROBI or HIGHS.
    """
    if preference == SolverBackendID.HIGHS:
        logger.info("HiGHS solver backend selected by user preference.")
        return SolverBackendID.HIGHS

    is_licensed = is_gurobi_licensed()

    if preference == SolverBackendID.GUROBI and is_licensed:
        logger.info("Gurobi solver backend selected by user preference.")
    elif preference == SolverBackendID.GUROBI:
        logger.warning(
            "Gurobi preferred but not available -- falling back to HiGHS solver "
            "backend."
        )
    elif is_licensed:
        logger.info("Gurobi license verified -- using Gurobi solver backend.")
    else:
        logger.info("Gurobi not available -- using HiGHS solver backend.")

    return SolverBackendID.GUROBI if is_licensed else SolverBackendID.HIGHS


def create_model(name: str, backend: SolverBackendID, options: BunkerOptions) -> Model:
    """
    Create an empty linear program on a backend, set up with the solver options.

    Parameters
    ----------
    name
        Name of the model.
    backend
        GUROBI or HIGHS, as ``select_backend()`` returns it.
    options
        Settings of the bunker algorithm.

    Returns
    -------
    Model
        The new model.
    """
    if backend == SolverBackendID.GUROBI:
        return GurobiModel(name, options)

    return HighsModel(name, options)
