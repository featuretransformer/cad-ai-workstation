"""
Assembly: Spur Gear Reducer Assembly (ID: asm_gearbox_eck_gear)
Total Components: 3, Total Instances: 3
"""
from build123d import *

# === Component: Gearbox Base Plate (comp_eck_gear_housing) ===
"""
Generated build123d code for CADIR Document: Gearbox Base Plate (ID: doc_comp_eck_gear_housing)
Component Family: housing, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Gearbox Base Plate Body (box)
    Box(length=140.0, width=90.0, height=15.0, mode=Mode.ADD)

    # Feature: Gearbox Base Plate Cavity (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=14.0, depth=None)

result = p.part

# === Standard Reused Component: Involute Spur Gear Pinion 20T (m=2.0, d=40mm, bore=8mm) (comp_eck_gear_pinion) ===
# Reused Standard Asset: Involute Spur Gear Pinion 20T (m=2.0, d=40mm, bore=8mm)
# Source: Curated Mechanical Drive Standards
# License: CC0-1.0
part = import_step('C:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/datasets/cad_assets/models/spur_gear_m2_z20.step')
# === Standard Reused Component: Involute Spur Gear Wheel 40T (m=2.0, d=80mm, bore=20mm) (comp_eck_gear_gear) ===
# Reused Standard Asset: Involute Spur Gear Wheel 40T (m=2.0, d=80mm, bore=20mm)
# Source: Curated Mechanical Drive Standards
# License: CC0-1.0
part = import_step('C:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/datasets/cad_assets/models/spur_gear_m2_z40.step')

# --- Assembly Placement & Compound Construction ---
# Assembled 3 solids into Compound