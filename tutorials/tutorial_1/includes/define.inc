# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# This is an example of a DEFINE file with the minimum amount 
# of parameters needed to run a meaningful modelling scenario in Navigate. 

# Define ModelDefinition below.



# A) DEFINITION OF A FLEET
# Define the node "fleet" below.



# Define "uptake" below.



# B) DEFINITION OF A VESSEL
# Bi) Define vessel node "vessel_ice_oil" below.



# Define and assign attributes of the node "vessel_ice_oil" 
# Above, edit the vessel node so that each attribute and its value is written within the curly
# brackets of the "vessel_ice_oil" node (i.e. PowerSystem, Route etc.). 



# Bii) Define PowerSystem below.



# Define the node "propulsion_ice_oil" below.



# Define the node "electrical_ice_oil" below.



# Define the node "heat_boiler_oil" below. 



# Biii) DEFINITION OF NODES THAT WERE INTRODUCED IN THE DEFINITION OF THE NODE "vessel_ice_oil".
# Define the node "main_oil" below.



# Define the node "route" below.



# C) DEFINITION OF A PORT
# Define the node "port" below.



#Define the node "BunkerLogistics" below.



# D) DEFINITION OF A FUEL
# Define the fuel node "heavy_fuel_oil" below.



# E) DEFINITION OF OUTPUT (PLOTS)
# Define a Plot node "plots" below. Use the Directory attribute to point at the
# "plots" subfolder, and add_plot(...) for each plot you want produced (see the
# tutorial for the plot labels to include).



# END OF NAV FILE