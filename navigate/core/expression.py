# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Define restricted arithmetic expressions for deck attributes and commands.

They are written using the deck's ``<...>`` syntax. Expression bodies are parsed
with the standard library ``ast`` module into a small internal tree that only
supports numeric literals, the operators ``+ - * / **``, and node-reference calls
such as ``Forecast("name")`` - they are never passed to ``eval()`` and cannot execute
arbitrary code.
"""

from __future__ import annotations

import ast
import operator
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, overload

import numpy as np

from navigate.core.wrap import as_list

if TYPE_CHECKING:
    from collections.abc import Callable

    from navigate.core.node import Node
    from navigate.core.node_type import AcceptedNodeTypes
    from navigate.util.types_ import FloatArray, FloatLike

type _UnaryOperator = Callable[[FloatLike], FloatLike]
type _BinaryOperator = Callable[[FloatLike, FloatLike], FloatLike]

_REFERENCE_NAME = re.compile(r"([A-Z][a-z]+)+")
_CAPITALIZED_NAME = re.compile(r"[A-Z][A-Za-z]*")


def _positive(value: FloatLike) -> FloatLike:
    return +value


def _negative(value: FloatLike) -> FloatLike:
    return -value


_BINARY_OPERATORS: dict[type[ast.operator], _BinaryOperator] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}

_UNARY_OPERATORS: dict[type[ast.unaryop], _UnaryOperator] = {
    ast.UAdd: _positive,
    ast.USub: _negative,
}


class _ReferencedNode(Protocol):
    """Duck type of a referenced node: the expression reads it through its getter."""

    def get(self, x: FloatLike | None, y: FloatLike | None) -> FloatLike: ...


type _References = list[_ReferencedNode]


class _Evaluable(Protocol):
    """Node of the evaluator tree an expression body compiles to."""

    def evaluate(
        self, node_references: _References, x: FloatLike | None, y: FloatLike | None
    ) -> FloatLike: ...


@dataclass(frozen=True, slots=True)
class _Constant:
    """Numeric literal."""

    value: float  # the numeric literal

    def evaluate(
        self, node_references: _References, x: FloatLike | None, y: FloatLike | None
    ) -> FloatLike:
        return self.value


@dataclass(frozen=True, slots=True)
class _Reference:
    """Reference to a node, evaluated through the node's getter."""

    index: int  # position in the expression's references

    def evaluate(
        self, node_references: _References, x: FloatLike | None, y: FloatLike | None
    ) -> FloatLike:
        return node_references[self.index].get(x, y)


@dataclass(frozen=True, slots=True)
class _UnaryOperation:
    """Operator applied to a single operand."""

    operator: _UnaryOperator  # the arithmetic operation
    operand: _Evaluable  # subtree the operator is applied to

    def evaluate(
        self, node_references: _References, x: FloatLike | None, y: FloatLike | None
    ) -> FloatLike:
        return self.operator(self.operand.evaluate(node_references, x, y))


@dataclass(frozen=True, slots=True)
class _BinaryOperation:
    """Operator applied to two operands."""

    operator: _BinaryOperator  # the arithmetic operation
    left: _Evaluable  # subtree on the left of the operator
    right: _Evaluable  # subtree on the right of the operator

    def evaluate(
        self, node_references: _References, x: FloatLike | None, y: FloatLike | None
    ) -> FloatLike:
        return self.operator(
            self.left.evaluate(node_references, x, y),
            self.right.evaluate(node_references, x, y),
        )


class _Builder:
    """
    Compile an expression body into an evaluator tree and its reference strings.

    Parameters
    ----------
    text
        Expression body, as written in the deck.
    owner
        Node the expression is assigned to, named in the error messages; None
        where the caller discards them.
    """

    def __init__(self, text: str, owner: Node | None) -> None:
        self._text: str = text  # expression body, as written in the deck
        self._owner: Node | None = owner  # node the expression is assigned to
        self.reference_strings: list[str] = []  # references, in order of appearance

    def build(self) -> tuple[_Evaluable, list[str]]:
        """
        Build the evaluator tree.

        Returns
        -------
        tuple[_Evaluable, list[str]]
            The tree and the canonical reference strings it indexes into.
        """
        try:
            tree = ast.parse(self._text, mode="eval")
        except SyntaxError as error:
            raise self._error(f"{error.msg}.") from None

        return self._build(tree.body), self.reference_strings

    def _build(self, node_ast: ast.expr) -> _Evaluable:
        if isinstance(node_ast, ast.Constant):
            return self._build_constant(node_ast)

        if isinstance(node_ast, ast.BinOp):
            return self._build_binary_operation(node_ast)

        if isinstance(node_ast, ast.UnaryOp):
            return self._build_unary_operation(node_ast)

        if isinstance(node_ast, ast.Call):
            return self._build_reference(node_ast)

        if isinstance(node_ast, ast.Name) and _CAPITALIZED_NAME.fullmatch(node_ast.id):
            raise NotImplementedError(
                f"{self._owner}: Expression '{self._text}' is currently unable"
                " to support references to attributes."
            )

        raise self._error(f"unsupported syntax '{ast.unparse(node_ast)}'.")

    def _build_constant(self, node_ast: ast.Constant) -> _Constant:
        value = node_ast.value

        # bools are ints to Python, but a deck writing 'True' does not mean a number
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise self._error(f"only numeric literals are allowed, got {value!r}.")

        # literals are evaluated as floats so that '**' overflows
        # instead of building arbitrarily large integers
        return _Constant(float(value))

    def _build_binary_operation(self, node_ast: ast.BinOp) -> _BinaryOperation:
        operator_ = _BINARY_OPERATORS.get(type(node_ast.op))

        if operator_ is None:
            raise self._error(f"unsupported operator '{type(node_ast.op).__name__}'.")

        return _BinaryOperation(
            operator_, self._build(node_ast.left), self._build(node_ast.right)
        )

    def _build_unary_operation(self, node_ast: ast.UnaryOp) -> _UnaryOperation:
        operator_ = _UNARY_OPERATORS.get(type(node_ast.op))

        if operator_ is None:
            raise self._error(
                f"unsupported unary operator '{type(node_ast.op).__name__}'."
            )

        return _UnaryOperation(operator_, self._build(node_ast.operand))

    def _build_reference(self, node_ast: ast.Call) -> _Reference:
        if not isinstance(node_ast.func, ast.Name) or not _REFERENCE_NAME.fullmatch(
            node_ast.func.id
        ):
            raise self._error(
                f"'{ast.unparse(node_ast)}' is not a valid node reference."
            )

        if node_ast.keywords or len(node_ast.args) != 1:
            raise self._error(
                f"'{ast.unparse(node_ast)}' must take exactly one positional argument."
            )

        argument = node_ast.args[0]

        if not isinstance(argument, ast.Constant) or type(argument.value) is not str:
            raise self._error(
                f"'{ast.unparse(node_ast)}' argument must be a string literal."
            )

        if '"' in argument.value:
            raise self._error("node reference name must not contain a quote.")

        # canonical spelling, whatever quoting and spacing the deck used
        self.reference_strings.append(f'{node_ast.func.id}("{argument.value}")')

        return _Reference(len(self.reference_strings) - 1)

    def _error(self, detail: str) -> ValueError:
        return ValueError(
            f"{self._owner}: Error in expression <{self._text}>: {detail}"
        )


class Expression:
    """
    Restricted arithmetic expression assigned to a deck attribute or command.

    Parameters
    ----------
    text
        Expression body, as written in the deck between its ``<`` and ``>``.
    """

    def __init__(self, text: str) -> None:
        self.text: str = text  # expression body, as written in the deck
        self.reference_strings: list[str] = []  # references, in order of appearance
        self.node_references: _References = []  # resolved references, in that order
        self.reference_location: str = ""  # deck file and line it is read from
        self.internal_bounds: tuple[float, float] = (-np.inf, np.inf)  # clip range

        self._tree: _Evaluable | None = None  # evaluator tree built from the text
        self._node: Node | None = None  # node the expression is assigned to
        self._allowed_types: list[str] | None = None  # node types the attribute accepts

    def __repr__(self) -> str:
        return self.text

    def initialize(self, node: Node) -> None:
        """
        Parse the expression text and build the internal evaluation tree.

        Parameters
        ----------
        node
            Node the expression is assigned to.
        """
        self._node = node
        self._tree, self.reference_strings = _Builder(self.text, node).build()

    def resolve(
        self, node: Node, read_reference: Callable[[str, str], _ReferencedNode]
    ) -> None:
        """
        Initialize the expression, resolve its references and check their types.

        An expression already initialized is left as it is.

        Parameters
        ----------
        node
            Node the expression is assigned to.
        read_reference
            Returns the node a canonical reference string names, given the
            string and the deck location the expression is read from.
        """
        if self.is_initialized():
            return

        self.initialize(node)
        self.node_references = [
            read_reference(reference_string, self.reference_location)
            for reference_string in self.reference_strings
        ]
        self.check_consistency()

    @overload
    def get(self, x: FloatArray, y: FloatLike | None = None) -> FloatArray: ...

    @overload
    def get(self, x: float | None = None, y: FloatLike | None = None) -> FloatLike: ...

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
        """
        if self._tree is None:
            raise RuntimeError("Expression evaluated before it was initialized.")

        evaluated = self._tree.evaluate(self.node_references, x, y)
        value = np.clip(evaluated, *self.internal_bounds)

        # a float result is broadcast so an expression over scalars answers
        # an array input the way one over arrays does
        if isinstance(value, float):
            if isinstance(x, np.ndarray):
                return np.full_like(x, value)

            if isinstance(y, np.ndarray):
                return np.full_like(y, value)

        return value

    def set_allowed_types(self, allowed_types: AcceptedNodeTypes) -> None:
        """
        Set the node types the attribute holding the expression accepts.

        Parameters
        ----------
        allowed_types
            Accepted node types; None where the attribute accepts no reference.
        """
        self._allowed_types = (
            as_list(allowed_types) if allowed_types is not None else None
        )

    def set_internal_bounds(self, lower: float, upper: float) -> None:
        """
        Set the range every evaluated value is clipped to.

        Parameters
        ----------
        lower
            Lower bound.
        upper
            Upper bound.
        """
        self.internal_bounds = (lower, upper)

    def is_initialized(self) -> bool:
        """
        Check whether the expression text has been parsed.

        Returns
        -------
        bool
            True once the text has been built into an evaluator tree.
        """
        return self._tree is not None

    def check_consistency(self) -> None:
        """Check that the attribute accepts the node types the expression references."""
        if not self.reference_strings:
            return

        if self._allowed_types is None:
            raise ValueError(
                f"{self._node}: Expression <{self.text}> does not allow node"
                " references."
            )

        # the type word of a reference string is the referenced node's own type
        for reference_string in self.reference_strings:
            type_ = reference_string.split("(")[0]

            if type_ not in self._allowed_types:
                raise ValueError(
                    f"{self._node}: Expression <{self.text}> references unacceptable"
                    f" type {type_}."
                )


def parse_reference_strings(text: str) -> list[str]:
    """
    Extract the node reference strings from an expression text.

    A text that does not parse yields none; the error surfaces when the
    expression carrying it is initialized for real.

    Parameters
    ----------
    text
        Expression body, as written in the deck.

    Returns
    -------
    list[str]
        Canonical reference strings, e.g. 'Forecast("name")'.
    """
    try:
        _, reference_strings = _Builder(text, None).build()
    except (ValueError, NotImplementedError):
        return []

    return reference_strings
