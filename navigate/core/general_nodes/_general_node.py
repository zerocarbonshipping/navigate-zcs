# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0


class _GeneralNode:
    def __init__(self):
        self.command_references = []  # CommandReference queue executed by the Parser

    def __repr__(self):
        return "{}".format(type(self).__name__)

    def add_command_reference(self, command_reference):
        self.command_references.append(command_reference)

    def clear_command_references(self):
        self.command_references = []
