# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Select the solution a solve of the bunkering LP returns among its optimal ones.

The bunkering LP, with costs c, coefficients A and right-hand sides b,

    min c'x   s.t.   (A x)_i = b_i, <= b_i or >= b_i,   x_lower <= x <= x_upper

has many optimal values x, and at one of them many optimal duals y. Which of them a
solver returns depends on the order of its columns and rows, its seed, its version
and its method. A solve is therefore three runs of the solver:

- the first run finds one optimal x and y, and with them which solutions are
  optimal: those complementary to y and to its reduced costs d = c - A'y;
- the keyed run gives the values: the optimal vertex of least keyed cost, where the
  key of a variable is a fixed number derived from its name;
- the direction run gives the duals of the priced constraints, those whose dual the
  bunker reads: the optimal duals that maximize w'y, for a direction w in which the
  right-hand sides of all priced constraints move together.

Each priced constraint moves the way that relaxes it, so one whose optimal duals do
not depend on those of the other priced constraints gets the saving from relaxing it
alone; an equality at zero can only rise, and gets the cost of its first unit. Where
the duals depend on each other, only the sum w'y is the largest: of two identical
caps on a cheap supply, one gets the whole price, though relaxing either alone saves
nothing.

Where the other constraints keep an equality at zero from rising, no optimal duals
are largest along w. The direction run is then repeated along the w in which no
equality at zero moves, and the duals of those equalities are whichever optimal
ones the solver ends at.

The selection has the precision of the solver. A reduced cost within about a factor
ten of the tolerance can count as zero in one solve and not in another of the same
LP, and the optimal solutions the keyed run chooses among then differ. Two keys
closer than the smallest tolerance the solver accepts leave the tie between their
variables, or their priced constraints, to the solver. A keyed or direction run that
does not end optimal leaves the values or duals of the first run as the solve's.

The keyed run and the direction run work on the solver's own model through
``VectorModel`` and leave it as they found it.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import SolveStatusID
from navigate.simulation.bunker._solver import Constraint, Program, Variable

if TYPE_CHECKING:
    from navigate.simulation.bunker._solver import VectorModel
    from navigate.util.types_ import BoolArray, FloatArray

logger = logging.getLogger(__name__)


class Selection[Basis]:
    """
    The solver-independent record of a model's elements and its selected solution.

    Parameters
    ----------
    tolerance
        Magnitude up to which a value, dual or reduced cost counts as zero.
    """

    def __init__(self, tolerance: float) -> None:
        self._tolerance: float = tolerance

        # per variable
        self._variable_keys: list[float] = []

        # per constraint
        self._constraint_keys: list[float] = []
        self._constraint_names: list[str] = []
        self._is_priced: list[bool] = []

        # the selected values and duals of the last solve
        self._x: FloatArray
        self._y: FloatArray

        # the basis the selected values are a vertex of, from which the next solve
        # of the model starts in few pivots; None before the first selection
        self.basis: Basis | None = None

    def add_variable(self, name: str) -> Variable:
        """Return the handle of a new variable, keyed by its name."""
        variable = Variable(len(self._variable_keys))
        self._variable_keys.append(_calculate_key(name))

        return variable

    def add_constraint(self, name: str, *, priced: bool) -> Constraint:
        """Return the handle of a new constraint, keyed by its name, priced or not."""
        constraint = Constraint(len(self._constraint_keys))

        self._constraint_keys.append(_calculate_key(name))
        self._constraint_names.append(name)
        self._is_priced.append(priced)

        return constraint

    def select(self, model: VectorModel[Basis]) -> None:
        """
        Select the values and duals of a model whose first run ended optimal.

        The keyed run and the direction run each set a program of their own, and
        the program of the model is set back after them, also where one raises.

        Parameters
        ----------
        model
            The model, at the solution of its first run.
        """
        lp = model.program()
        x = model.values()
        y = model.duals()
        basis = model.basis()

        try:
            self._x, self.basis = self._select_values(model, lp, basis, x, y)
            self._y = self._select_duals(model, lp, basis, self._x, y)
        finally:
            model.set_program(lp)

    def value(self, variable: Variable) -> float:
        """Return the selected value of a variable."""
        value: float = self._x[variable]
        return value

    def dual(self, constraint: Constraint) -> float:
        """
        Return the selected dual of a priced constraint.

        Raises
        ------
        ValueError
            If the constraint is not priced: no solve selects its dual.
        """
        if not self._is_priced[constraint]:
            name = self._constraint_names[constraint]
            raise ValueError(f"The dual of {name} is not selected: it is not priced.")

        dual: float = self._y[constraint]
        return dual

    def _select_values(
        self,
        model: VectorModel[Basis],
        lp: Program,
        basis: Basis,
        x: FloatArray,
        y: FloatArray,
    ) -> tuple[FloatArray, Basis]:
        """
        Return the values and basis of the keyed run.

        Where the keyed run does not end optimal, the values and basis of the first
        run are returned.

        Parameters
        ----------
        model
            The model, at the solution of its first run.
        lp
            The linear program of the model.
        basis
            Basis of the first run.
        x
            Values of the first run.
        y
            Duals of the first run.

        Returns
        -------
        tuple[FloatArray, Basis]
            The selected values and the basis they are a vertex of.
        """
        keys = np.array(self._variable_keys)
        optimal_face = _calculate_optimal_face(lp, x, y, self._tolerance)

        model.set_program(replace(optimal_face, c=keys))
        status = model.run("primal", basis)

        if status == SolveStatusID.OPTIMAL:
            return model.values(), model.basis()

        logger.debug(
            "The keyed run of the bunkering LP ended %s; the values of the first run "
            "are returned.",
            status.name,
        )

        return x, basis

    def _select_duals(
        self,
        model: VectorModel[Basis],
        lp: Program,
        basis: Basis,
        x: FloatArray,
        y: FloatArray,
    ) -> FloatArray:
        """
        Return the duals of the direction run.

        The direction moves the zero right-hand sides too. Where one of them
        cannot move, the run does not end optimal, and it is repeated along the
        direction that leaves them all, which selects no dual among the optimal
        ones of their constraints. Where that run does not end optimal either, the
        duals of the first run are returned.

        Parameters
        ----------
        model
            The model, at the solution of its first run.
        lp
            The linear program of the model.
        basis
            Basis of the first run.
        x
            The selected values.
        y
            Duals of the first run.

        Returns
        -------
        FloatArray
            The selected duals; only those of the priced constraints are selected.
        """
        tolerance = self._tolerance
        keys = np.array(self._constraint_keys)
        is_priced = np.array(self._is_priced)

        for moves_zeros in (True, False):
            w = _calculate_direction(lp, x, keys, is_priced, tolerance, moves_zeros)
            directions = _calculate_feasible_directions(lp, x, y, w, tolerance)

            model.set_program(directions)
            status = model.run("dual", basis)

            if status == SolveStatusID.OPTIMAL:
                return model.duals()

            logger.debug(
                "The direction run of the bunkering LP that %s the zero right-hand "
                "sides ended %s.",
                "moves" if moves_zeros else "leaves",
                status.name,
            )

        logger.debug("The duals of the first run of the bunkering LP are returned.")

        return y


def _calculate_key(name: str) -> float:
    """
    Calculate the key of an LP element from its name.

    The key comes from a SHA-256 digest of the name, which is the same in every
    process and on every platform; Python's ``hash`` of a string is neither.

    Parameters
    ----------
    name
        Name of the variable or constraint, distinct from every other one's.

    Returns
    -------
    float
        A number in [1, 2).
    """
    digest = hashlib.sha256(name.encode()).digest()
    mantissa = int.from_bytes(digest[:8]) >> 12

    return 1.0 + mantissa / 2**52


def _calculate_optimal_face(
    lp: Program, x: FloatArray, y: FloatArray, tolerance: float
) -> Program:
    """
    Restrict a linear program to its optimal solutions.

    Every optimal solution is complementary to the duals of one optimal run: a
    variable with a non-zero reduced cost stays at the bound it is at, and a
    constraint with a non-zero dual stays tight. The feasible set with those held is
    the set of optimal solutions, whichever optimal run the duals are from.

    A dual is non-zero where it holds more than the tolerance of a reduced cost
    (``_has_dual``), so a solution that moves along a constraint held free costs at
    most the tolerance more per unit a variable moves, as one that moves a variable
    left free does.

    Parameters
    ----------
    lp
        The linear program.
    x
        Values of an optimal run.
    y
        Duals of that run.
    tolerance
        Magnitude beyond which a reduced cost, or a dual's part of one, is non-zero.

    Returns
    -------
    Program
        The linear program with each such variable fixed at its value and each
        such constraint an equality.
    """
    b = lp.b
    d = lp.c - lp.A.T @ y

    is_fixed = np.abs(d) > tolerance
    is_tight = _has_dual(lp, y, tolerance)

    return replace(
        lp,
        x_lower=np.where(is_fixed, x, lp.x_lower),
        x_upper=np.where(is_fixed, x, lp.x_upper),
        b_lower=np.where(is_tight, b, lp.b_lower),
        b_upper=np.where(is_tight, b, lp.b_upper),
    )


def _has_dual(lp: Program, y: FloatArray, tolerance: float) -> BoolArray:
    """
    Check which constraints have a non-zero dual.

    A dual y_i enters the reduced cost of variable j as A_ij y_i. It is non-zero
    where the largest of those terms exceeds the tolerance, the magnitude beyond
    which a reduced cost is non-zero itself. The dual alone says nothing: on a
    constraint with coefficients of 1e7, a dual of 1e-6 is 10 in the reduced costs.

    Parameters
    ----------
    lp
        The linear program.
    y
        Duals of an optimal run.
    tolerance
        Magnitude beyond which a reduced cost is non-zero.

    Returns
    -------
    BoolArray
        Whether each constraint's dual is non-zero.
    """
    largest_coefficient = np.abs(lp.A).max(axis=1).toarray().ravel()
    has_dual: BoolArray = np.abs(y) * largest_coefficient > tolerance

    return has_dual


def _calculate_direction(
    lp: Program,
    x: FloatArray,
    keys: FloatArray,
    is_priced: BoolArray,
    tolerance: float,
    moves_zeros: bool,
) -> FloatArray:
    """
    Calculate the direction in which the right-hand sides of the priced rows move.

    At a kink of the total cost a constraint has an interval of optimal duals, one
    end per way its right-hand side b can move. Each priced constraint moves the way
    that relaxes it, towards the saving:

    - ``<=``: up, towards one unit more room;
    - ``>=``: down, towards one unit less requirement;
    - ``==`` with a b that is not zero: towards zero, one unit less;
    - ``==`` with a zero b: up, the only way it can move, towards the cost of the
      first unit.

    The duals largest along the direction are those ends only where the intervals
    of the priced constraints do not depend on each other (module docstring).

    A constraint moves by the larger of abs(b) and one, times its key, which keeps
    the direction from being parallel to a face of the optimal duals. An equality
    with a zero b does not move where no variable can supply it, nor where
    ``moves_zeros`` is false, and its dual is then whichever optimal one the
    direction run ends at.

    Parameters
    ----------
    lp
        The linear program.
    x
        The selected values.
    keys
        A number in [1, 2) per constraint.
    is_priced
        Whether each constraint is priced.
    tolerance
        Magnitude up to which a right-hand side or a variable's headroom is zero.
    moves_zeros
        Whether an equality with a zero b moves at all.

    Returns
    -------
    FloatArray
        Movement of each right-hand side; zero where the constraint is not priced.
    """
    b = lp.b
    is_equality = lp.is_equality
    is_zero = np.abs(b) <= tolerance

    has_headroom = lp.x_upper - x > tolerance
    supplier_count = (lp.A > 0.0) @ has_headroom.astype(np.float64)
    can_supply = supplier_count > 0.0

    size = np.maximum(np.abs(b), 1.0) * keys
    senses = [
        np.isfinite(lp.b_upper) & ~is_equality,
        np.isfinite(lp.b_lower) & ~is_equality,
        is_equality & ~is_zero,
        is_equality & can_supply & moves_zeros,
    ]
    movements = [size, -size, -np.sign(b) * size, size]
    w = np.select(senses, movements, default=0.0)

    return np.where(is_priced, w, 0.0)


def _calculate_feasible_directions(
    lp: Program, x: FloatArray, y: FloatArray, w: FloatArray, tolerance: float
) -> Program:
    """
    Calculate the linear program of the directions an optimal solution can move in.

    As the right-hand sides move by w, an optimal solution x moves by u at least
    cost:

        min c'u   s.t.   (A u)_i = w_i     for an equality i
                         (A u)_i <= w_i    for an active <= constraint i
                         (A u)_i >= w_i    for an active >= constraint i
                         u_j >= 0          for a variable j at its lower bound
                         u_j <= 0          for a variable j at its upper bound

    Its duals are the optimal duals of the linear program that maximize w'y.

    A constraint is active where its dual y is non-zero, or where x leaves it no
    slack beyond the tolerance and the rounding error of its activity (A x)_i: at
    most the number of its terms times the machine epsilon times the sum of their
    magnitudes. The slack is not scaled by the right-hand side beyond that, as a
    constraint with slack counted as active would get a dual no optimal solution
    has.

    The program has an optimum only if it has feasible duals, and the y of a run is
    feasible only to the solver's tolerance: a dual of the wrong sign, or a reduced
    cost on a variable between its bounds, each within the tolerance, leaves an
    unbounded direction. The costs c are therefore lowered by exactly those
    violations, which makes y, cleared of its own, feasible by construction.

    An active constraint counted as slack makes that correction large: its dual is
    cleared as a violation, and where its coefficients are large, a dual within the
    tolerance holds a large part of the reduced costs of its variables. The duals
    of the program are then not feasible for the linear program.

    Parameters
    ----------
    lp
        The linear program.
    x
        An optimal solution.
    y
        Duals of an optimal run.
    w
        Movement of each right-hand side.
    tolerance
        Distance up to which a variable is at a bound and a constraint, rounding
        aside, at its right-hand side; magnitude beyond which a dual's part of a
        reduced cost is non-zero.

    Returns
    -------
    Program
        The linear program of the feasible directions.
    """
    inf = np.inf
    epsilon = np.finfo(np.float64).eps

    activity = lp.A @ x
    magnitude = np.abs(lp.A) @ np.abs(x)
    term_count = np.diff(lp.A.indptr)
    rounding = term_count * epsilon * magnitude

    is_at_lower = x - lp.x_lower <= tolerance
    is_at_upper = lp.x_upper - x <= tolerance

    is_tight = _has_dual(lp, y, tolerance)
    reaches_lower = activity - lp.b_lower <= tolerance + rounding
    reaches_upper = lp.b_upper - activity <= tolerance + rounding

    is_active = is_tight | lp.is_equality
    is_active_lower = np.isfinite(lp.b_lower) & (is_active | reaches_lower)
    is_active_upper = np.isfinite(lp.b_upper) & (is_active | reaches_upper)

    # the signs feasible duals and reduced costs have, and the violations of them
    y_lower = np.where(is_active_upper, -inf, 0.0)
    y_upper = np.where(is_active_lower, inf, 0.0)
    d_lower = np.where(is_at_upper, -inf, 0.0)
    d_upper = np.where(is_at_lower, inf, 0.0)

    d = lp.c - lp.A.T @ np.clip(y, y_lower, y_upper)
    violation = d - np.clip(d, d_lower, d_upper)

    return Program(
        c=lp.c - violation,
        A=lp.A,
        x_lower=np.where(is_at_lower, 0.0, -inf),
        x_upper=np.where(is_at_upper, 0.0, inf),
        b_lower=np.where(is_active_lower, w, -inf),
        b_upper=np.where(is_active_upper, w, inf),
    )
