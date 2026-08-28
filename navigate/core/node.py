# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core._mixin import CommandReferenceMixin, TypeCheckMixin


class Node(CommandReferenceMixin, TypeCheckMixin):
    def __init__(self, name):
        CommandReferenceMixin.__init__(self)

        self.name = name            # str
        self.type = None            # str

        # expectation/profile
        self.expectation = None
        self.profile = None

        # static properties
        self.allow_dates_in_table = False   # whether added tables can contain dates

        # dynamic properties
        self.just_copied = False            # whether node was just copied (used in Parser)

    def __repr__(self):
        return "{}(\"{}\")".format(self.type, self.name)

    def initialize(self):
        pass

    @staticmethod
    def is_node():
        return True
