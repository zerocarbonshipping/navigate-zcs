# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Restricted arithmetic expressions assigned to attributes and commands through
the deck's ``<...>`` syntax. Expression bodies are parsed with the standard
library ``ast`` module into a small internal tree that only supports numeric
literals, the operators ``+ - * / **``, and node-reference calls such as
``Forecast("name")`` — they are never passed to ``eval()`` and cannot execute
arbitrary code.
"""

import ast
import operator
import re

import numpy as np

from navigate.core.wrap import as_list

_REFERENCE_NAME = re.compile(r'([A-Z][a-z]+)+')
_CAPITALIZED_NAME = re.compile(r'[A-Z][A-Za-z]*')

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}

_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class _Constant:
    def __init__(self, value):
        self.value = value

    def evaluate(self, node_references, x, y):
        return self.value


class _Reference:
    def __init__(self, index):
        self.index = index

    def evaluate(self, node_references, x, y):
        return node_references[self.index].get(x, y)


class _UnaryOperation:
    def __init__(self, operator_, operand):
        self.operator = operator_
        self.operand = operand

    def evaluate(self, node_references, x, y):
        return self.operator(self.operand.evaluate(node_references, x, y))


class _BinaryOperation:
    def __init__(self, operator_, left, right):
        self.operator = operator_
        self.left = left
        self.right = right

    def evaluate(self, node_references, x, y):
        return self.operator(self.left.evaluate(node_references, x, y),
                             self.right.evaluate(node_references, x, y))


class Expression:
    def __init__(self, expression):

        self._expression = expression       # str, as written in deck
        self._allowed_types = None

        self._internal_expression = None    # evaluator tree built from the parsed expression
        self._node = None                   # Node on which expression is assigned
        self.node_references = []           # list[Node] referenced in the expression
        self.reference_location = ''       # the file and line in the deck where the node is reference
        self.internal_bounds = (-np.inf, np.inf)

        self._node_initialize_finished = False
        self._attribute_initialization_finished = False

    def __repr__(self):
        return self._expression

    def initialize(self, node):
        """

        Parameters
        ----------
        node : Node
            Class Node on which the expression is assigned to an attribute.
        """

        self._node = node

        try:
            tree = ast.parse(self._expression, mode='eval')
        except SyntaxError as e:
            raise ValueError("{}: Error in expression <{}>: {}."
                             .format(self._node, self._expression, e.msg))

        self._internal_expression = self._build(tree.body)

    def _build(self, node_ast):
        if isinstance(node_ast, ast.Constant):
            return self._build_constant(node_ast)

        if isinstance(node_ast, ast.BinOp):
            return self._build_binary_operation(node_ast)

        if isinstance(node_ast, ast.UnaryOp):
            return self._build_unary_operation(node_ast)

        if isinstance(node_ast, ast.Call):
            return self._build_reference(node_ast)

        if isinstance(node_ast, ast.Name) and _CAPITALIZED_NAME.fullmatch(node_ast.id):
            raise NotImplementedError("{}: Expression '{}' is currently unable to support references to attributes."
                                      .format(self._node, self._expression))

        raise ValueError("{}: Error in expression <{}>: unsupported syntax '{}'."
                         .format(self._node, self._expression, ast.unparse(node_ast)))

    def _build_constant(self, node_ast):
        value = node_ast.value

        if type(value) not in (int, float):
            raise ValueError("{}: Error in expression <{}>: only numeric literals are allowed, got {!r}."
                             .format(self._node, self._expression, value))

        # literals are evaluated as floats so that '**' overflows
        # instead of building arbitrarily large integers
        return _Constant(float(value))

    def _build_binary_operation(self, node_ast):
        operator_ = _BINARY_OPERATORS.get(type(node_ast.op))

        if operator_ is None:
            raise ValueError("{}: Error in expression <{}>: unsupported operator '{}'."
                             .format(self._node, self._expression, type(node_ast.op).__name__))

        return _BinaryOperation(operator_, self._build(node_ast.left), self._build(node_ast.right))

    def _build_unary_operation(self, node_ast):
        operator_ = _UNARY_OPERATORS.get(type(node_ast.op))

        if operator_ is None:
            raise ValueError("{}: Error in expression <{}>: unsupported unary operator '{}'."
                             .format(self._node, self._expression, type(node_ast.op).__name__))

        return _UnaryOperation(operator_, self._build(node_ast.operand))

    def _build_reference(self, node_ast):
        if not isinstance(node_ast.func, ast.Name) or not _REFERENCE_NAME.fullmatch(node_ast.func.id):
            raise ValueError("{}: Error in expression <{}>: '{}' is not a valid node reference."
                             .format(self._node, self._expression, ast.unparse(node_ast)))

        if node_ast.keywords or len(node_ast.args) != 1:
            raise ValueError("{}: Error in expression <{}>: '{}' must take exactly one positional argument."
                             .format(self._node, self._expression, ast.unparse(node_ast)))

        argument = node_ast.args[0]

        if not isinstance(argument, ast.Constant) or type(argument.value) is not str:
            raise ValueError("{}: Error in expression <{}>: '{}' argument must be a string literal."
                             .format(self._node, self._expression, ast.unparse(node_ast)))

        if '"' in argument.value:
            raise ValueError("{}: Error in expression <{}>: node reference name must not contain a quote."
                             .format(self._node, self._expression))

        # node references are stored as canonical strings and changed
        # to actual NodeReference classes in the Parser later
        self.node_references.append('{}("{}")'.format(node_ast.func.id, argument.value))

        return _Reference(len(self.node_references) - 1)

    def get(self, x=None, y=None):
        value = self._internal_expression.evaluate(self.node_references, x, y)
        value = np.clip(value, *self.internal_bounds)

        # resize to same shape as the input
        if isinstance(value, float):
            if isinstance(x, np.ndarray):
                value = np.full_like(x, value)
            elif isinstance(y, np.ndarray):
                value = np.full_like(y, value)

        return value

    def set_allowed_types(self, allowed_types):
        self._allowed_types = as_list(allowed_types) if allowed_types is not None else None

    def set_internal_bounds(self, lower, upper):
        self.internal_bounds = (lower, upper)

    def is_initialized(self):
        return self._internal_expression is not None

    def check_consistency(self):
        # check that the attribute to which the expression
        # is assigned allows the kind of node reference
        # that is being used in the expression
        for node_reference in self.node_references:
            self._check_node_reference(_extract_node_type(node_reference))

    def _check_node_reference(self, type_):
        if self._allowed_types is None:
            raise ValueError("{}: Expression <{}> does not allow node references.".format(self._node, self._expression))

        elif type_ not in self._allowed_types:
            raise ValueError("{}: Expression <{}> references unacceptable type {}."
                             .format(self._node, self._expression, type_))


def _extract_node_type(node_reference):
    if isinstance(node_reference, str):
        type_ = node_reference.split('(')[0]
    else:
        type_ = node_reference.type

    return type_
