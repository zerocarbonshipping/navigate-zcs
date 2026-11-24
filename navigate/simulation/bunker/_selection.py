# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Select the solution a solve of the bunkering LP returns among its optimal ones.

The bunkering LP, with costs c, coefficients A and right-hand sides b,

    min c'x   s.t.   (A x)_i = b_i, <= b_i or >= b_i,   x_lower <= x <= x_upper

has many optimal values x, and at one of them many optimal duals y. Which of them a
solver returns depends on the order of its columns and rows, its seed, its version
and its method. A solve is therefore a sequence of runs of the solver:

- the first run finds one optimal x;
- the direction run selects the duals y: the optimal duals that maximize w'y, for a
  direction w in which the right-hand sides of all priced constraints, those whose
  dual the bunker reads, move together;
- the share of room, the first rule, finds in two runs the room of each member of
  the one pool that binds, and holds the members at one share of their rooms;
- the run of each minimizing rule, in the order of the rules, minimizes the
  expression of the rule over the solutions still optimal, and leaves those at
  which it is least.

The optimal solutions are those complementary to y and to its reduced costs
d = c - A'y: a variable with a non-zero reduced cost stays at its bound and a
constraint with a non-zero dual stays tight. Any optimal duals state the same
solutions, by other bounds and constraints; the selected ones state them for every
run after the direction run, so that the room of the members is found among the
solutions the minimizing rules then select among. The run of a minimizing rule
leaves the ones complementary to its own duals and reduced costs as well.

The rules are the bunker's (``_rules``): each states which of two equally cheap
solutions the simulation continues on. The values of a solve are those of the last
run of a minimizing rule, or of the first run where no minimizing rule has a run.
The share of room takes effect only through those runs, as bounds on the solutions
they select among: where no minimizing rule has a run, the values are the first
run's, whatever the pools. Nothing selects among the solutions the rules leave: the
values are those the solver ends the last run at.

Duals
-----
Each priced constraint moves the way that relaxes it, so one whose optimal duals do
not depend on those of the other priced constraints gets the saving from relaxing it
alone; an equality at zero can only rise, and gets the cost of its first unit. Where
the duals depend on each other, only the sum w'y is the largest: of two caps on a
cheap supply that bind only together, the one whose movement allows the smaller
amount of the supply still binds once both have moved, and gets the whole price,
though relaxing either alone saves nothing. Where two priced constraints bind only
together and, relaxed in proportion to their sizes, would allow the same amount,
which of the two carries the price is the solver's choice.

Where the other constraints keep an equality at zero from rising, no optimal duals
are largest along w. The direction run is then repeated along the w in which no
equality at zero moves, and the duals of those equalities are whichever optimal
ones the solver ends at.

The direction run works at the x of the first run. Every optimal y is complementary
to every optimal x, so the duals it selects among are the same whichever optimal x
that is.

Share of room
-------------
A pool is a constraint i that limits a weighted sum of member variables v, less an
excess variable e that relaxes it at a cost:

    sum_v n_v x_v - x_e <= b_i

The pool binds where its selected dual y_i is not zero. A member that lowers its
variable then lets another raise its own, and where neither change costs anything,
every split between the two is optimal. Each member takes the same share s of its
own room:

    x_v = lo_v + s (hi_v - lo_v)

where lo_v and hi_v are the least and the largest x_v among the solutions
complementary to y and d with the constraints of all pools left out. There a member
still pays the dual of each pool per unit of its variable, through its reduced
costs, but no longer has to balance the other members. With the pools' constraints
moved into the costs at their duals, these are the optimal solutions of what
remains, so they depend on the duals of the pools alone, not on which optimal duals
the other constraints have. And as no other constraint holds two members, one run
that minimizes sum_v x_v ends every member at lo_v, and one that maximizes it at
hi_v.

The share is the one that leaves the constraint of the pool tight. With x0 the
values of the first run:

    above = sum_v n_v (x0_v - lo_v)
    room  = sum_v n_v (hi_v - lo_v)
    kept  = max(x0_e - above, 0)   where d_e = 0,   x0_e elsewhere
    s     = (above - (x0_e - kept)) / room

The members lower their variables before the pool keeps an excess: where d_e = 0, a
unit of excess costs what a unit lowered costs, and the excess kept is what the
members cannot lower.

above and x0_e depend on the optimal x the first run ended at, and above - x0_e
does not: by the tight constraint it is b_i - sum_v n_v lo_v, from which kept and
s follow. It is summed member by member, as written, and not taken as that
difference of two totals, in whose rounding the room of a member with a small
weight is lost.

Every member but one is fixed at its share, and the excess at kept, for the runs of
the minimizing rules. The member left out follows from the tight constraint, which
gives it the rounding of the pool's total with it: with every member fixed, that
rounding would have nowhere to go. It is the member whose weighted room
n_v (hi_v - lo_v) is the largest: the rounding moves a member by a part of its room
that is the least for that one, and a member without room could not take it at all.
Two members equal in that are interchangeable.

Whether the shares can be met together with every other constraint, such as that
of a second pool, is for those runs to tell: where one does not end optimal, the
minimizing rules run again without the shares.

The rule applies where exactly one pool binds: with two, the room a member has
under one depends on what it takes under the other. Which pools bind is read from
the selected duals, and so is the solver's choice where they are. That is where
the direction is parallel to a face of the optimal duals, as for two pools that
bind only together and, relaxed in proportion to their sizes, would allow the same
amount; and where no direction run ends optimal. The rule has nothing to share
where no member has room, and is skipped where one of its two runs does not end
optimal.

Precision
---------
The selection has the precision of the solver. A reduced cost is non-zero beyond the
tolerance of the model, whatever tolerance the run that gave it took
(``VectorModel.run``); a dual where its part of one is beyond the tolerance or, for
the optimal solutions, beyond the variable's share of it
(``_calculate_optimal_face``). One within about a factor ten of that tolerance can
count as zero in one solve and not in another of the same LP, and the solutions the
runs after it choose among then differ.

A run of a minimizing rule that does not end optimal ends the rules: the values
are those of the last run that ended optimal. Where neither direction run ends
optimal, the duals of the solve are those of the first run, the prices of the pools
among them.

The runs after the first work on the solver's own model through ``VectorModel``
and leave it as they found it.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import TYPE_CHECKING, NamedTuple

import numpy as np

from navigate.core.enum_ import SolveStatusID
from navigate.simulation.bunker._solver import Constraint, Program

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.simulation.bunker._solver import (
        MinimizingRule,
        Pool,
        Variable,
        VectorModel,
    )
    from navigate.util.types_ import BoolArray, FloatArray, IntArray

logger = logging.getLogger(__name__)


class _Solution[Basis](NamedTuple):
    """Optimal values and duals of a linear program, with the basis of the values."""

    lp: Program
    x: FloatArray
    y: FloatArray
    basis: Basis


class Selection[Basis]:
    """
    The solver-independent record of a model's constraints, rules and solution.

    Parameters
    ----------
    tolerance
        Magnitude up to which a value, dual or reduced cost counts as zero.
    """

    def __init__(self, tolerance: float) -> None:
        self._tolerance: float = tolerance

        # per constraint
        self._constraint_names: list[str] = []
        self._is_priced: list[bool] = []

        # the pools of the share of room
        self._pools: Sequence[Pool] = ()

        # per minimizing rule, by its name and first rule first: the variables of its
        # expression and their coefficients
        self._expressions: dict[str, tuple[IntArray, FloatArray]] = {}

        # the selected values and duals of the last solve
        self._x: FloatArray
        self._y: FloatArray

        # the basis the selected values are a vertex of, from which the next solve
        # of the model starts in few pivots; None before the first selection
        self.basis: Basis | None = None

    def add_constraint(self, name: str, *, priced: bool) -> Constraint:
        """Return the handle of a new constraint, priced or not."""
        constraint = Constraint(len(self._is_priced))

        self._constraint_names.append(name)
        self._is_priced.append(priced)

        return constraint

    def set_rules(
        self, pools: Sequence[Pool], minimizing_rules: Sequence[MinimizingRule]
    ) -> None:
        """Set the rules a solve selects its values by: the pools, then the others."""
        self._pools = pools
        self._expressions = {}

        for name, terms in minimizing_rules:
            variables = np.array([variable for variable, _ in terms], dtype=np.intp)
            coefficients = np.array([coefficient for _, coefficient in terms])
            self._expressions[name] = (variables, coefficients)

    def select(self, model: VectorModel[Basis]) -> None:
        """
        Select the values and duals of a model whose first run ended optimal.

        The duals are selected first: the share of room reads them, and the
        optimal solutions the rules select among are those complementary to them.
        Every run of the selection sets a program of its own, and the program of
        the model is set back after them, also where one raises.

        Parameters
        ----------
        model
            The model, at the solution of its first run.
        """
        lp = model.program()
        first = _Solution(lp, model.values(), model.duals(), model.basis())

        try:
            self._y = self._select_duals(model, first)
            selected = first._replace(y=self._y)
            self._x, self.basis = self._select_values(model, selected)
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

    def _select_duals(
        self, model: VectorModel[Basis], first: _Solution[Basis]
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
            The model, whose first run ended optimal.
        first
            The solution of the first run.

        Returns
        -------
        FloatArray
            The selected duals; only those of the priced constraints are selected.
        """
        lp, x, y, basis = first
        tolerance = self._tolerance
        is_priced = np.array(self._is_priced)

        for moves_zeros in (True, False):
            w = _calculate_direction(lp, is_priced, tolerance, moves_zeros)
            directions = _calculate_feasible_directions(lp, x, y, w, tolerance)

            model.set_program(directions)
            model.set_basis(basis)
            status = model.run("dual")

            if status == SolveStatusID.OPTIMAL:
                return model.duals()

            logger.debug(
                "The direction run of the bunkering LP that %s the zero right-hand "
                "sides ended %s.",
                "moves" if moves_zeros else "leaves",
                status.name,
            )

        logger.debug("The bunkering LP keeps the duals of its first run.")

        return y

    def _select_values(
        self, model: VectorModel[Basis], selected: _Solution[Basis]
    ) -> tuple[FloatArray, Basis]:
        """
        Return the values and basis the rules select.

        The minimizing rules run on the optimal solutions with the shares of room
        held. Where one of those runs does not end optimal, the shares may be what
        keeps it from an optimum, and the minimizing rules run again on the optimal
        solutions without them.

        Parameters
        ----------
        model
            The model, whose first run ended optimal.
        selected
            The values and basis of the first run, with the selected duals.

        Returns
        -------
        tuple[FloatArray, Basis]
            The selected values and the basis they are a vertex of.
        """
        lp, x, y, _ = selected

        face = _calculate_optimal_face(lp, x, y, self._tolerance)
        held = self._share_room(model, face, selected)

        if held is not None:
            last, ended_optimal = self._run_minimizing_rules(model, held, selected)

            if ended_optimal:
                return last.x, last.basis

            logger.debug(
                "A run of a minimizing rule of the bunkering LP did not end optimal "
                "with the shares of room held; the minimizing rules run again "
                "without the shares."
            )

        last, _ = self._run_minimizing_rules(model, face, selected)

        return last.x, last.basis

    def _share_room(
        self, model: VectorModel[Basis], face: Program, selected: _Solution[Basis]
    ) -> Program | None:
        """
        Return the optimal solutions with the members of the one binding pool held.

        Parameters
        ----------
        model
            The model, whose first run ended optimal.
        face
            The linear program of the model, restricted to its optimal solutions.
        selected
            The values and basis of the first run, with the selected duals.

        Returns
        -------
        Program | None
            The restricted program with every member of the pool but one, and its
            excess variable, fixed; None where no pool or several bind, where no
            member has room and where a run to the ends does not end optimal.
        """
        _, x, y, basis = selected
        tolerance = self._tolerance

        # the face holds a constraint as an equality where its dual is not zero
        binding = [pool for pool in self._pools if face.is_equality[pool.constraint]]

        if not binding:
            return None

        if len(binding) > 1:
            logger.debug(
                "The share of room of the bunkering LP is skipped: %d pools bind.",
                len(binding),
            )

            return None

        pool = binding[0]
        members = np.array(pool.members, dtype=np.intp)
        e = pool.excess

        own = _leave_out(face, [pool.constraint for pool in self._pools])
        ends = self._run_ends(model, own, members, basis)

        if ends is None:
            return None

        lo, hi = ends

        # a room within the tolerance is none: two runs give a value no closer
        if not np.any(hi - lo > tolerance):
            return None

        n = face.A[[pool.constraint]].toarray()[0, members]

        # the reduced cost of the excess variable, which stands in the constraint
        # of its pool alone, with a coefficient of -1
        d_e = face.c[e] + y[pool.constraint]
        lowers_first = abs(d_e) <= tolerance
        shares, kept = _calculate_shares(n, x[members], lo, hi, x[e], lowers_first)

        left_out = np.argmax(n * (hi - lo))
        held = np.append(np.delete(members, left_out), e)
        values = np.append(np.delete(shares, left_out), kept)

        return _fix(face, held, values)

    def _run_ends(
        self,
        model: VectorModel[Basis],
        own: Program,
        members: IntArray,
        basis: Basis,
    ) -> tuple[FloatArray, FloatArray] | None:
        """
        Return the least and the largest value each member of a pool has on its own.

        Parameters
        ----------
        model
            The model.
        own
            The linear program of the model, restricted to the solutions
            complementary to the selected duals, the constraints of the pools
            left out.
        members
            The member variables of the pool.
        basis
            Basis of the first run, which both runs start from.

        Returns
        -------
        tuple[FloatArray, FloatArray] | None
            The values of the members in the run that minimizes their sum, and in
            the run that maximizes it; None where a run does not end optimal.
        """
        c = np.zeros(own.c.size)
        c[members] = 1.0
        ends = {}

        for end, sign in (("low", 1.0), ("high", -1.0)):
            model.set_program(replace(own, c=sign * c))
            model.set_basis(basis)
            status = model.run("primal")

            if status != SolveStatusID.OPTIMAL:
                logger.debug(
                    "The run of the share of room of the bunkering LP to the %s ends "
                    "of the members ended %s; the share of room is skipped.",
                    end,
                    status.name,
                )

                return None

            ends[end] = model.values()[members]

        return ends["low"], ends["high"]

    def _run_minimizing_rules(
        self, model: VectorModel[Basis], face: Program, start: _Solution[Basis]
    ) -> tuple[_Solution[Basis], bool]:
        """
        Return the solution of the last run of a minimizing rule that ended optimal.

        The first run minimizes the expression of its rule over the solutions of
        the given program, from the basis of the start, and each run after it over
        the solutions complementary to the solution of the run before, cut at the
        tolerance of the model, from its basis. A rule whose expression has no
        non-zero coefficient tells no two solutions apart and has no run. A run
        that does not end optimal ends the rules.

        Parameters
        ----------
        model
            The model, whose first run ended optimal.
        face
            The linear program of the model, restricted to the solutions the
            rules select among.
        start
            The solution those are restricted from: the first run starts from its
            basis, and it is returned where no run ends optimal.

        Returns
        -------
        tuple[_Solution[Basis], bool]
            The solution of the last run that ended optimal, or the given one
            where none did, and whether every run ended optimal.
        """
        tolerance = self._tolerance
        last = start

        model.set_basis(start.basis)

        for name, (variables, coefficients) in self._expressions.items():
            c = np.zeros(face.c.size)
            np.add.at(c, variables, coefficients)

            if not c.any():
                continue

            # the solutions the run before left
            if last is not start:
                face = _calculate_optimal_face(last.lp, last.x, last.y, tolerance)

            program = replace(face, c=c)

            model.set_program(program)
            status = model.run("primal")

            if status != SolveStatusID.OPTIMAL:
                logger.debug(
                    "The run of the minimizing rule %r of the bunkering LP ended %s; "
                    "the minimizing rules after it do not run.",
                    name,
                    status.name,
                )

                return last, False

            last = _Solution(program, model.values(), model.duals(), model.basis())

        return last, True


def _calculate_optimal_face(
    lp: Program, x: FloatArray, y: FloatArray, tolerance: float
) -> Program:
    """
    Restrict a linear program to its optimal solutions.

    Every optimal solution is complementary to any optimal duals: a variable with
    a non-zero reduced cost stays at the bound it is at, and a constraint with a
    non-zero dual stays tight. The feasible set with those held is the set of
    optimal solutions, whichever optimal duals they are.

    The constraints a variable stands in share the tolerance of its reduced cost
    equally: a dual is non-zero where its part of the reduced cost of one of its
    variables exceeds that variable's share (``_has_dual``). Together, the
    constraints held free so add at most the tolerance to any reduced cost, and a
    solution that moves along them costs at most the tolerance more per unit a
    variable moves, as one that moves a variable left free does. With the whole
    tolerance for each constraint, a variable in a thousand constraints, each with
    a dual just within it, could move at a thousand times the tolerance per unit.

    Parameters
    ----------
    lp
        The linear program.
    x
        Optimal values.
    y
        Any optimal duals.
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

    constraint_counts = np.bincount(lp.A.indices, minlength=lp.c.size)
    shares = tolerance / np.maximum(constraint_counts, 1)

    is_fixed = np.abs(d) > tolerance
    is_tight = _has_dual(lp, y, shares)

    return replace(
        lp,
        x_lower=np.where(is_fixed, x, lp.x_lower),
        x_upper=np.where(is_fixed, x, lp.x_upper),
        b_lower=np.where(is_tight, b, lp.b_lower),
        b_upper=np.where(is_tight, b, lp.b_upper),
    )


def _has_dual(lp: Program, y: FloatArray, tolerances: FloatArray) -> BoolArray:
    """
    Check which constraints have a non-zero dual.

    A dual y_i enters the reduced cost of variable j as A_ij y_i. It is non-zero
    where one of those terms exceeds the tolerance of variable j. The dual alone
    says nothing: on a constraint with coefficients of 1e7, a dual of 1e-6 is 10 in
    the reduced costs.

    Parameters
    ----------
    lp
        The linear program.
    y
        Optimal duals.
    tolerances
        Magnitude, per variable, beyond which a dual's part of its reduced cost is
        non-zero.

    Returns
    -------
    BoolArray
        Whether each constraint's dual is non-zero.
    """
    # |A_ij y_i| exceeds the tolerance t_j where |y_i| |A_ij| / t_j exceeds one
    relative_coefficients = np.abs(lp.A.data) / tolerances[lp.A.indices]
    largest = _calculate_largest_per_constraint(lp, relative_coefficients)
    has_dual: BoolArray = np.abs(y) * largest > 1.0

    return has_dual


def _calculate_largest_per_constraint(lp: Program, values: FloatArray) -> FloatArray:
    """
    Calculate the largest of values given per coefficient, in each constraint.

    The coefficients are stored constraint by constraint, so numpy reduces the
    stretch of each constraint directly. The row-wise maximum of scipy takes
    several times as long.

    Parameters
    ----------
    lp
        The linear program.
    values
        A value per stored coefficient, in the order of ``lp.A.data``.

    Returns
    -------
    FloatArray
        The largest value per constraint; zero for one without coefficients.
    """
    starts = lp.A.indptr[:-1]
    has_terms = np.diff(lp.A.indptr) > 0

    largest = np.zeros(has_terms.size)
    largest[has_terms] = np.maximum.reduceat(values, starts[has_terms])

    return largest


def _leave_out(lp: Program, constraints: Sequence[Constraint]) -> Program:
    """
    Leave constraints out of a linear program.

    Parameters
    ----------
    lp
        The linear program.
    constraints
        The constraints to leave out.

    Returns
    -------
    Program
        The linear program with those constraints in their places, without bounds.
    """
    b_lower = lp.b_lower.copy()
    b_upper = lp.b_upper.copy()

    b_lower[constraints] = -np.inf
    b_upper[constraints] = np.inf

    return replace(lp, b_lower=b_lower, b_upper=b_upper)


def _calculate_shares(
    n: FloatArray,
    x0: FloatArray,
    lo: FloatArray,
    hi: FloatArray,
    x0_e: float,
    lowers_first: bool,
) -> tuple[FloatArray, float]:
    """
    Calculate the values of the members of a pool at one share of their rooms.

    The share s and the excess kept are those of the module docstring. s stays
    within [0, 1], which it leaves only by the rounding of a first run outside
    the ends.

    Parameters
    ----------
    n
        Weight of each member in the constraint of the pool.
    x0
        Value of each member in the first run.
    lo
        Least value of each member on its own.
    hi
        Largest value of each member on its own; above lo for at least one member.
    x0_e
        Value of the excess variable of the pool in the first run.
    lowers_first
        Whether the reduced cost of the excess variable is zero, so that the
        members lower their variables before the pool keeps an excess.

    Returns
    -------
    tuple[FloatArray, float]
        The value of each member at the share, and the excess the pool keeps.
    """
    above = float(n @ (x0 - lo))
    room = float(n @ (hi - lo))

    kept = max(x0_e - above, 0.0) if lowers_first else x0_e
    s = np.clip((above - (x0_e - kept)) / room, 0.0, 1.0)

    return lo + s * (hi - lo), kept


def _fix(lp: Program, variables: IntArray, values: FloatArray) -> Program:
    """
    Fix variables of a linear program at values.

    Parameters
    ----------
    lp
        The linear program.
    variables
        The variables to fix.
    values
        The value of each of them.

    Returns
    -------
    Program
        The linear program with both bounds of each such variable at its value.
    """
    x_lower = lp.x_lower.copy()
    x_upper = lp.x_upper.copy()

    x_lower[variables] = values
    x_upper[variables] = values

    return replace(lp, x_lower=x_lower, x_upper=x_upper)


def _calculate_direction(
    lp: Program, is_priced: BoolArray, tolerance: float, moves_zeros: bool
) -> FloatArray:
    """
    Calculate the direction in which the right-hand sides of the priced rows move.

    At a kink of the total cost a constraint has an interval of optimal duals, one
    end per way its right-hand side b can move. Each priced constraint moves the way
    that relaxes it, towards the saving:

    - ``<=``: up, towards one unit more of what it limits;
    - ``>=``: down, towards one unit less requirement;
    - ``==`` with a b that is not zero: towards zero, one unit less;
    - ``==`` with a zero b: up, the only way it can move, towards the cost of the
      first unit.

    The duals largest along the direction are those ends only where the intervals
    of the priced constraints do not depend on each other (module docstring).

    A constraint moves by the larger of abs(b) and one. Where the direction is
    parallel to a face of the optimal duals, as for two priced constraints that
    bind only together and, relaxed in proportion to their sizes, would allow the
    same amount, every dual of that face is largest along it, and the direction
    run ends at whichever the solver finds.

    An equality with a zero b does not move where no variable can supply it, nor
    where ``moves_zeros`` is false, and its dual is then whichever optimal one the
    direction run ends at. A variable can supply it unless its bounds fix it, as
    they do a removed one. The test reads the bounds and not the values of a
    solution, so the direction is the same at every optimal one.

    Parameters
    ----------
    lp
        The linear program.
    is_priced
        Whether each constraint is priced.
    tolerance
        Magnitude up to which a right-hand side, or the distance between the
        bounds of a variable, is zero.
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

    can_move = lp.x_upper - lp.x_lower > tolerance
    supplier_count = (lp.A > 0.0) @ can_move.astype(np.float64)
    can_supply = supplier_count > 0.0

    size = np.maximum(np.abs(b), 1.0)
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
    has. For the same reason a dual is non-zero where its part of one reduced cost
    exceeds the whole tolerance (``_has_dual``), and not a variable's share of it as
    in the optimal face: the test decides only for a constraint with slack, whose
    optimal duals are all zero. Duals within the tolerance on several constraints
    of a variable add up only in the correction of its cost below, which the
    optimal face sees as a reduced cost of the variable: beyond the tolerance, it
    holds the variable at its value.

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

    is_tight = _has_dual(lp, y, np.full(lp.c.size, tolerance))
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
