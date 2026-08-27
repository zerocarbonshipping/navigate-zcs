# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Node-type names: the DSL keywords that declare nodes in `.nav`/`.inc` files.
For regular nodes the name is also the value stored in the node's `_type`
attribute, so type checks and the parser's per-type tables share a single
vocabulary; general nodes carry no `_type` and use theirs only as parser
dispatch keys.
"""

CONVERTER = "Converter"
CURVE = "Curve"
EMISSION = "Emission"
FEEDSTOCK = "Feedstock"
FLEET = "Fleet"
FORECAST = "Forecast"
FUEL = "Fuel"
LEVY = "Levy"
PLANT = "Plant"
PLOT = "Plot"
PORT = "Port"
POWER_SYSTEM = "PowerSystem"
PROCESS = "Process"
PRODUCER = "Producer"
REGION = "Region"
REGULATION = "Regulation"
REPORT = "Report"
ROUTE = "Route"
SOURCE = "Source"
SURFACE = "Surface"
TANK = "Tank"
TECHNOLOGY = "Technology"
TIMETABLE = "Timetable"
TRANSPORT = "Transport"
VARIABLE = "Variable"
VESSEL = "Vessel"

# general nodes
BUNKER_LOGISTICS = "BunkerLogistics"
BUNKER_OPTIONS = "BunkerOptions"
MODEL_DEFINITION = "ModelDefinition"
