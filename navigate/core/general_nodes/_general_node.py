# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0


class _GeneralNode:
    def __repr__(self):
        return "{}".format(type(self).__name__)
