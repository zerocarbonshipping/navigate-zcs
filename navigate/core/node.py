# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core.node_type import TypeCheckMixin


class Node(TypeCheckMixin):
    def __init__(self, name: str, type_: str) -> None:
        super().__init__(type_)

        self.name = name            # str

        # expectation/profile
        self.expectation = None
        self.profile = None

        # static properties
        self.allow_dates_in_table = False   # whether added tables can contain dates

        # dynamic properties
        self.just_copied = False            # whether node was just copied (used in Parser)
        self.command_references = []        # CommandReference queue executed by the Parser

    def __repr__(self):
        return "{}(\"{}\")".format(self.type, self.name)

    def add_command_reference(self, command_reference):
        self.command_references.append(command_reference)

    def clear_command_references(self):
        self.command_references = []

    def initialize(self):
        pass
