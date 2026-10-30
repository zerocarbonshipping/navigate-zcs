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

from navigate.core._bounds import Bounds
from navigate.core.node_type import accepts_type, is_calculator
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
_BINARY_OPERATORS: dict[str, _BinaryOperator] = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "**": operator.pow,
}
_UNARY_OPERATORS: dict[str, _UnaryOperator] = {
    "+": _positive,
    "-": _negative,
}


# a node named in a deck: its type and name
type _NodeKey = tuple[str, str]

# the calculators an expression's references evaluate through, by node key
type _Calculators = Mapping[_NodeKey, Calculator]


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
    def key(self) -> _NodeKey:
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
        return _UNARY_OPERATORS[self.symbol](self.operand.evaluate(calculators, x, y))


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
        return _BINARY_OPERATORS[self.symbol](left, right)


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
        nodes: Mapping[_NodeKey, Node],
        holder: Node | GeneralNode,
    ) -> None:
        self.calculators: dict[_NodeKey, Calculator] = {}

        self._text: str = text
        self._tree: Evaluable = tree
        self._nodes: Mapping[_NodeKey, Node] = nodes
        self._holder: Node | GeneralNode = holder
        self._allowed_types: AcceptedNodeTypes | None = None
        self._internal_bounds: Bounds = Bounds()

    def __repr__(self) -> str:
        return self._text

    @property
    def _owner(self) -> str:
        """The expression as its errors name it, after the node holding it."""
        return f"{self._holder}: Expression <{self._text}>"

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
        FloatLike
            Expression value, clamped to the internal bounds and broadcast to
            the shape of the input.

        Raises
        ------
        ValueError
            If the value, or any entry of it, is at or beyond an exclusive
            internal bound.
        """
        evaluated = self._tree.evaluate(self.calculators, x, y)

        try:
            value = self._internal_bounds.clamp(evaluated)
        except ValueError as error:
            raise ValueError(f"{self._owner}: {error}") from None

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
        self._allowed_types = allowed_types

    def set_internal_bounds(self, bounds: Bounds) -> None:
        """
        Set the bounds every evaluated value is clamped to.

        A value reaching an exclusive bound raises instead of being clamped.

        Parameters
        ----------
        bounds
            The bounds of the attribute holding the expression.
        """
        self._internal_bounds = bounds

    def check_consistency(self) -> None:
        """
        Check the referenced nodes against the types the attribute accepts.

        Runs once the setter holding the expression has declared the types it
        accepts; it binds the calculators the evaluator reads.
        """
        for reference in node_references(self._tree):
            if self._allowed_types is None:
                raise ValueError(f"{self._owner} does not allow node references.")

            node = self._nodes[reference.key]
            accepted = accepts_type(self._allowed_types, reference.type)

            if not (accepted and is_calculator(node)):
                raise ValueError(
                    f"{self._owner} references unacceptable type {reference.type}."
                )

            self.calculators[reference.key] = node
