# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core._mixin import CommandReferenceMixin


class GeneralNode(CommandReferenceMixin):
    def __init__(self):
        CommandReferenceMixin.__init__(self)

    @staticmethod
    def is_node():
        return False

    def __repr__(self):
        return "{}".format(type(self).__name__)
