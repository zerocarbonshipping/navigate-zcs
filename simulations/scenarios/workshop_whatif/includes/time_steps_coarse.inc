# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Four years, not five. RetrofitFrequency defaults to 5, and is_retrofit_cycle
# tests `age % frequency < time_step`, so a 5-year step makes that always true
# and the drydock gate stops gating. On main the fleet converts late (from 2042
# in the yearly run), so this grid still converts far fewer hulls than the yearly
# run - 112 against 1,140 - and lands 2050 emissions at 711 Mt against 676.
#
# 2027 and 2030 are not a choice: DefaultConverterAvailable declares them, and
# every date the parser sees is merged into one timeline. They are listed here
# so this file states the grid the model will actually use.

Start

Date "01-01-2027"
Date "01-01-2030"
Date "01-01-2034"
Date "01-01-2038"
Date "01-01-2042"
Date "01-01-2046"
Date "01-01-2050"

End
