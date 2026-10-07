# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Run the navigate command line with 'python -m navigate'."""

from __future__ import annotations

import sys

from navigate.app import main

if __name__ == "__main__":
    sys.exit(main())
