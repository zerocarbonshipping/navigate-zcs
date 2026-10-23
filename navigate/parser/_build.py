# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The build phase: the kept declarations become nodes, once, in one order.

Construct one node per kept declaration, apply the assignments, check the
required attributes, seed the command-written dictionaries, run the commands,
build the tables, initialize, validate. The same steps apply an event at its
date, followed by the registry-wide re-initialization and validation. A value
is materialized per target: a reference becomes its node, a wildcard the nodes
it matches, an expression a fresh Expression bound to its holder.
"""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.dsl import required_attributes
from navigate.core.expression import Expression, NodeReference, node_references
from navigate.core.general_nodes.bunker_options import BunkerOptions
from navigate.core.general_nodes.model_definition import ModelDefinition
from navigate.core.lifecycle import (
    initialize,
    reinitialize,
    seed_dependencies,
    validate,
)
from navigate.core.node import Node
from navigate.core.node_registry import NODE_CLASS, GeneralNodes, Nodes
from navigate.core.node_type import MODEL_DEFINITION
from navigate.core.table_data import TableData
from navigate.exceptions import DeckError, UnassignedAttributeError
from navigate.parser._collect import matching
from navigate.parser._lark_parser import Assignment, Command, ExpressionSyntax
from navigate.util import attribute_to_setter

if TYPE_CHECKING:
    from collections.abc import Callable

    from navigate.core.general_nodes._general_node import _GeneralNode
    from navigate.core.nodes.curve import Curve
    from navigate.core.nodes.forecast import Forecast
    from navigate.core.nodes.surface import Surface
    from navigate.core.nodes.timetable import Timetable
    from navigate.parser._collect import Collector, Key
    from navigate.parser._lark_parser import BodyItem, DeckValue, SourceLocation
    from navigate.parser._resolve import BoundEvent

logger = logging.getLogger(__name__)

# a deck value once every reference names its node
type MaterializedValue = (
    float
    | str
    | np.datetime64
    | Node
    | Expression
    | TableData
    | list[MaterializedValue]
)

type Holder = Node | _GeneralNode

# a node and the body items to apply to it
type Target = tuple[Node, list[BodyItem]]


class Builder:
    """
    Build the nodes of a resolved deck and apply its events.

    Parameters
    ----------
    collector
        The deck as collected, every default pulled.
    kept
        The declarations the simulation holds, in declaration order.
    """

    def __init__(self, collector: Collector, kept: list[Key]) -> None:
        self._collector: Collector = collector
        self._kept: list[Key] = kept

        self.nodes: Nodes = Nodes()
        self.general_nodes: GeneralNodes
        self._node_by_key: dict[Key, Node] = {}

        # the deck attributes whose setter ran on each node, for the required check
        self._assigned: dict[Holder, set[str]] = {}
        # the expressions of the item being applied, checked once its setter or
        # command has run
        self._unchecked: list[tuple[Expression, SourceLocation]] = []
        # the references to nodes the simulation does not hold, each as
        # "<holder> <attribute>: <reference>", left out of their lists
        self._dropped: list[str] = []

    # general nodes --------------------------------------------------------------------

    def build_general_nodes(self) -> GeneralNodes:
        """
        Build the general nodes from their declarations.

        Returns
        -------
        GeneralNodes
            The record of the deck's general nodes.
        """
        if MODEL_DEFINITION not in self._collector.general:
            raise DeckError("Error in simulation: 'ModelDefinition' must be defined.")

        model_definition, bunker_options = ModelDefinition(), BunkerOptions()
        holders = (model_definition, bunker_options)

        for holder in holders:
            # the collect phase lets no command onto a general node
            for item in self._collector.general.get(holder.type, []):
                assert isinstance(item, Assignment)
                self._assign(holder, item)

        for holder in holders:
            self._check_required(holder)

        self.general_nodes = GeneralNodes(
            bunker_options=bunker_options, model_definition=model_definition
        )
        return self.general_nodes

    # nodes ----------------------------------------------------------------------------

    def build_nodes(self) -> Nodes:
        """
        Construct the kept declarations' nodes and apply their bodies.

        Returns
        -------
        Nodes
            The node registry.
        """
        targets: list[Target] = []

        for key in self._kept:
            node_type, name = key
            node = NODE_CLASS[node_type](name)
            body = self._collector.declarations[key].effective_body()

            self.nodes.group(node_type)[name] = node
            self._node_by_key[key] = node
            targets.append((node, body))

        self._apply(targets, initialize)
        return self.nodes

    def apply_events(self, events: list[BoundEvent]) -> None:
        """
        Apply the events of one date, then re-initialize every node.

        Parameters
        ----------
        events
            The event blocks to apply, each with the nodes it targets; empty on
            a date with no events, which only re-initializes.
        """
        targets: list[Target] = []

        for block, keys in events:
            for key in keys:
                targets.append((self._node_by_key[key], block.body))

        self._apply(targets, reinitialize)

    def _apply(self, targets: list[Target], sweep: Callable[[Nodes], None]) -> None:
        """
        Assign, seed, command, build tables, run the lifecycle sweep, validate.

        The required attributes are checked before anything reads a node's
        attributes, the seeding included.
        """
        for node, body in targets:
            for item in body:
                if isinstance(item, Assignment):
                    self._assign(node, item)

        self._warn_dropped()

        for node, _ in targets:
            self._check_required(node)

        seed_dependencies(self.nodes)

        for node, body in targets:
            for item in body:
                if isinstance(item, Command):
                    self._run_command(node, item)

        self._build_tables()
        self._run_lifecycle(sweep)
        self._run_lifecycle(validate)

    # applying items -------------------------------------------------------------------

    def _assign(self, holder: Holder, item: Assignment) -> None:
        value = self._materialize(item.value, holder, item)
        if value is None:
            value = []

        setter = getattr(holder, attribute_to_setter(item.attribute))

        try:
            setter(value)
        except ValueError as e:
            raise item.source.error(
                f"{holder} attribute '{item.attribute}' {e!s}."
            ) from None

        self._check_expressions()
        self._assigned.setdefault(holder, set()).add(item.attribute)

    def _run_command(self, node: Node, item: Command) -> None:
        inputs = [self._materialize(argument, node, item) for argument in item.args]
        method = getattr(node, item.name)

        # the argument count is checked before the call, so an error raised
        # inside the command is a bug and keeps its traceback
        try:
            inspect.signature(method).bind(*inputs)
        except TypeError as e:
            raise item.source.error(f"'{item.name}' {e!s}.") from None

        try:
            method(*inputs)
        except ValueError as e:
            raise item.source.error(f"'{item.name}' {e!s}.") from None

        self._check_expressions()

    def _check_expressions(self) -> None:
        unchecked, self._unchecked = self._unchecked, []
        for expression, source in unchecked:
            try:
                expression.check_consistency()
            except ValueError as e:
                raise source.error(str(e)) from None

    def _check_required(self, holder: Holder) -> None:
        assigned = self._assigned.get(holder, set())
        for attribute in required_attributes(holder.deck_attributes):
            if attribute not in assigned:
                raise UnassignedAttributeError(str(holder), attribute)

    def _build_tables(self) -> None:
        """Build the tables set since the last pass, measuring dates from the start."""
        # once every item is applied, so the interpolation and extrapolation
        # settings apply wherever the deck writes them, and before any node's
        # hooks read a calculator
        start_date = self.general_nodes.model_definition.start_date
        dated: list[Forecast | Timetable] = [
            *self.nodes.forecasts.values(),
            *self.nodes.timetables.values(),
        ]
        undated: list[Curve | Surface] = [
            *self.nodes.curves.values(),
            *self.nodes.surfaces.values(),
        ]

        for table in dated:
            try:
                table.build_table(start_date)
            except ValueError as e:
                raise DeckError(f"{table}: {e!s}") from None

        for table in undated:
            try:
                table.build_table()
            except ValueError as e:
                raise DeckError(f"{table}: {e!s}") from None

    def _run_lifecycle(self, sweep: Callable[[Nodes], None]) -> None:
        try:
            sweep(self.nodes)
        except ValueError as e:
            raise DeckError(str(e)) from None

    # materializing values -------------------------------------------------------------

    def _materialize(
        self, value: DeckValue, holder: Holder, item: BodyItem
    ) -> MaterializedValue | None:
        """
        Replace every reference in a value with the node it names.

        A wildcard becomes the list of the nodes it matches, spliced into a list
        it sits in. A reference the simulation does not hold, which the prune
        leaves only under a non-activating attribute, is dropped from its list
        and recorded; a lone one becomes None.
        """
        if isinstance(value, NodeReference):
            if value.is_wildcard:
                return self._expand_wildcard(value, item)

            node = self._node_by_key.get((value.type, value.name))
            if node is None:
                self._dropped.append(f"{holder} {item.name}: {value}")
                return None

            return node

        if isinstance(value, list):
            materialized: list[MaterializedValue] = []
            for element in value:
                if isinstance(element, NodeReference) and element.is_wildcard:
                    materialized.extend(self._expand_wildcard(element, item))
                    continue

                result = self._materialize(element, holder, item)
                if result is not None:
                    materialized.append(result)

            return materialized

        if isinstance(value, ExpressionSyntax):
            return self._materialize_expression(value, holder, item)

        return value

    def _expand_wildcard(
        self, reference: NodeReference, item: BodyItem
    ) -> list[MaterializedValue]:
        keys = matching(self._node_by_key, reference.type, reference.name)
        if not keys:
            raise item.source.error(
                f"Wildcard '{reference.name}' did not match any {reference.type} nodes."
            )

        return [self._node_by_key[key] for key in keys]

    def _materialize_expression(
        self, syntax: ExpressionSyntax, holder: Holder, item: BodyItem
    ) -> Expression:
        nodes: dict[Key, Node] = {}
        for reference in node_references(syntax.root):
            node = self._node_by_key.get(reference.key)
            if node is None:
                raise item.source.error(
                    f"Expression <{syntax.text}> references {reference}, which the "
                    "simulation does not hold."
                )

            nodes[reference.key] = node

        expression = Expression(syntax.text, syntax.root, nodes, holder)
        self._unchecked.append((expression, item.source))
        return expression

    def _warn_dropped(self) -> None:
        if not self._dropped:
            return

        logger.warning(
            "Removed %s reference(s) to unused node(s):%s\n"
            "Assign the removed node(s) to a Route to keep them, or drop the stale "
            "reference(s) from the deck.",
            len(self._dropped),
            "".join(f"\n\t- {line}" for line in self._dropped),
        )
        self._dropped = []
