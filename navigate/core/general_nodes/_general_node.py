# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0


from __future__ import annotations


class _GeneralNode:
    def __repr__(self):
        return f"{type(self).__name__}"

    def check_requirements(self) -> None:
        """Raise if an attribute the node cannot run without is unassigned."""
