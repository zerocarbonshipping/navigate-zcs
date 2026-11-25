# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# The coarse grid: 2026, 2027, 2030, then every four years to 2050.
#
# Four years, not five: RetrofitFrequency defaults to 5, and a cohort is at a
# retrofit cycle in the step in which its age reaches a multiple of it, so a
# 5-year step would make nearly every step a retrofit cycle.
#
# 2027 and 2030 are not a choice: DefaultConverterAvailable declares them, and
# every date the parser sees is merged into one timeline.

Start

Date "01-01-2027"
Date "01-01-2030"
Date "01-01-2034"
Date "01-01-2038"
Date "01-01-2042"
Date "01-01-2046"
Date "01-01-2050"

End
