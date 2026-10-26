# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Define restricted arithmetic expressions for deck attributes and commands.

They are written using the deck's ``<...>`` syntax, which the parser's grammar
reads straight into a tree of the evaluator nodes defined here: numeric
literals, the operators ``+ - * / **``, unary signs and node references. The
parser hands an ``Expression`` that tree with the nodes its references name,
so nothing here parses text and nothing is ever passed to ``eval()``.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, overload

import numpy as np

from navigate.core.bounds import Bounds
from navigate.core.node_type import is_calculator
from navigate.util import name_contains_wildcards

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping

    from navigate.core.general_nodes.general_node import GeneralNode
    from navigate.core.node import Node
    from navigate.core.node_type import AcceptedNodeTypes
    from navigate.core.types_ import Calculator
    from navigate.util.types_ import FloatArray, FloatLike

type _UnaryOperator = Callable[[FloatLike], FloatLike]
type _BinaryOperator = Callable[[FloatLike, FloatLike], FloatLike]


# mypy cannot match the generic stubs of operator.pos and operator.neg to _UnaryOperator
def _positive(value: FloatLike) -> FloatLike:
    return +value


def _negative(value: FloatLike) -> FloatLike:
    return -value


# the operators an expression may use, by the symbol the deck writes them with
BINARY_OPERATORS: dict[str, _BinaryOperator] = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "**": operator.pow,
}
UNARY_OPERATORS: dict[str, _UnaryOperator] = {
    "+": _positive,
    "-": _negative,
}


# a node named in a deck: its type and name
type NodeKey = tuple[str, str]

# the calculators an expression's references evaluate through, by node key
type _Calculators = Mapping[NodeKey, Calculator]


class Evaluable(Protocol):
    """Node of the evaluator tree an expression is built from."""

    def evaluate(
        self, calculators: _Calculators, x: FloatLike | None, y: FloatLike | None
    ) -> FloatLike:
        """Evaluate the node, reading each reference through its calculator."""
        ...


@dataclass(frozen=True, slots=True)
class Constant:
    """Numeric literal."""

    value: float

    def evaluate(
        self, calculators: _Calculators, x: FloatLike | None, y: FloatLike | None
    ) -> FloatLike:
        """Return the literal."""
        return self.value


@dataclass(frozen=True, slots=True)
class NodeReference:
    """
    A node named in a deck, ``Type("name")``; the name may be a glob.

    As a value it names the node an attribute or argument takes; as a leaf of
    an expression tree it evaluates through the named node's getter.
    """

    type: str
    name: str

    @property
    def key(self) -> NodeKey:
        """The (type, name) pair the node is filed under."""
        return (self.type, self.name)

    @property
    def is_wildcard(self) -> bool:
        """Whether the name is a glob over the names of the type."""
        return name_contains_wildcards(self.name)

    def __repr__(self) -> str:
        return f'{self.type}("{self.name}")'

    def evaluate(
        self, calculators: _Calculators, x: FloatLike | None, y: FloatLike | None
    ) -> FloatLike:
        """Evaluate the referenced node at the inputs."""
        return calculators[self.key].get(x, y)


@dataclass(frozen=True, slots=True)
class UnaryOperation:
    """Sign applied to a single operand."""

    symbol: str
    operand: Evaluable

    def evaluate(
        self, calculators: _Calculators, x: FloatLike | None, y: FloatLike | None
    ) -> FloatLike:
        """Apply the sign to the evaluated operand."""
        return UNARY_OPERATORS[self.symbol](self.operand.evaluate(calculators, x, y))


@dataclass(frozen=True, slots=True)
class BinaryOperation:
    """Operator applied to two operands."""

    symbol: str
    left: Evaluable
    right: Evaluable

    def evaluate(
        self, calculators: _Calculators, x: FloatLike | None, y: FloatLike | None
    ) -> FloatLike:
        """Apply the operator to the evaluated operands."""
        left = self.left.evaluate(calculators, x, y)
        right = self.right.evaluate(calculators, x, y)
        return BINARY_OPERATORS[self.symbol](left, right)


def node_references(tree: Evaluable) -> Iterator[NodeReference]:
    """
    Yield every node reference in an expression tree, left to right.

    Parameters
    ----------
    tree
        The root of the tree.

    Yields
    ------
    NodeReference
        Each reference, in the order written.
    """
    if isinstance(tree, NodeReference):
        yield tree
    elif isinstance(tree, UnaryOperation):
        yield from node_references(tree.operand)
    elif isinstance(tree, BinaryOperation):
        yield from node_references(tree.left)
        yield from node_references(tree.right)


class Expression:
    """
    Restricted arithmetic expression assigned to a deck attribute or command.

    Parameters
    ----------
    text
        Expression body, as written in the deck between its ``<`` and ``>``.
    tree
        The evaluator tree the parser built from the text.
    nodes
        The node each ``NodeReference`` leaf of the tree names, by its key.
    holder
        The node or general node the expression is assigned to, named in errors.
    """

    def __init__(
        self,
        text: str,
        tree: Evaluable,
        nodes: Mapping[NodeKey, Node],
        holder: Node | GeneralNode,
    ) -> None:
        self.text: str = text
        self.calculators: dict[NodeKey, Calculator] = {}
        self.internal_bounds: Bounds = Bounds()

        self._tree: Evaluable = tree
        self._nodes: Mapping[NodeKey, Node] = nodes
        self._holder: Node | GeneralNode = holder
        self._allowed_types: tuple[str, ...] | None = None

    def __repr__(self) -> str:
        return self.text

    @overload
    def get(self, x: float | None = None, y: float | None = None) -> float: ...

    @overload
    def get(self, x: FloatArray, y: FloatLike | None = None) -> FloatArray: ...

    @overload
    def get(
        self, x: FloatLike | None = None, y: FloatLike | None = None
    ) -> FloatLike: ...

    def get(self, x: FloatLike | None = None, y: FloatLike | None = None) -> FloatLike:
        """
        Evaluate the expression.

        Parameters
        ----------
        x
            First input variable passed on to the getters of referenced nodes.
        y
            Second input variable passed on to the getters of referenced nodes.

        Returns
        -------
        float or FloatArray
            Expression value, clipped to the internal bounds and broadcast to
            the shape of the input.

        Raises
        ------
        ValueError
            If the value, or any entry of it, is at or beyond an exclusive
            internal bound.
        """
        evaluated = self._tree.evaluate(self.calculators, x, y)
        bounds = self.internal_bounds

        # inclusive bounds only clamp, so the check is skipped where both are
        if bounds.exclusive:
            violation = bounds.exclusive_violation(evaluated)
            if violation is not None:
                owner = f"{self._holder}: Expression <{self.text}>"
                raise ValueError(f"{owner}: {violation}")

        # numpy's stubs type np.clip over a float or an array as an array,
        # though a float comes back as an np.float64, a float
        value: FloatLike = np.clip(evaluated, bounds.lower, bounds.upper)

        # a float result is broadcast so an expression over scalars answers
        # an array input the way one over arrays does
        if isinstance(value, float):
            if isinstance(x, np.ndarray):
                return np.full_like(x, value)

            if isinstance(y, np.ndarray):
                return np.full_like(y, value)

        return value

    def set_allowed_types(self, allowed_types: AcceptedNodeTypes | None) -> None:
        """
        Set the node types the attribute holding the expression accepts.

        Parameters
        ----------
        allowed_types
            Accepted node types; None where the attribute accepts no reference.
        """
        self._allowed_types = (
            (allowed_types,) if isinstance(allowed_types, str) else allowed_types
        )

    def set_internal_bounds(
        self,
        lower: float,
        upper: float,
        *,
        inclusive_lower: bool = True,
        inclusive_upper: bool = True,
    ) -> None:
        """
        Set the range every evaluated value is clipped to.

        A value reaching an exclusive bound raises instead of being clipped.

        Parameters
        ----------
        lower
            Lower bound.
        upper
            Upper bound.
        inclusive_lower
            Whether the value may equal the lower bound.
        inclusive_upper
            Whether the value may equal the upper bound.
        """
        self.internal_bounds = Bounds(lower, upper, inclusive_lower, inclusive_upper)

    def check_consistency(self) -> None:
        """
        Check the referenced nodes against the types the attribute accepts.

        Runs once the setter holding the expression has declared the types it
        accepts; it binds the calculators the evaluator reads.
        """
        for reference in node_references(self._tree):
            if self._allowed_types is None:
                raise ValueError(
                    f"{self._holder}: Expression <{self.text}> does not allow node"
                    " references."
                )

            node = self._nodes[reference.key]

            if reference.type not in self._allowed_types or not is_calculator(node):
                raise ValueError(
                    f"{self._holder}: Expression <{self.text}> references"
                    f" unacceptable type {reference.type}."
                )

            self.calculators[reference.key] = node
