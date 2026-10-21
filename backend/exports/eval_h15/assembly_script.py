"""
Assembly: Flexible Jaw Shaft Coupling Assembly (ID: asm_coupling_eval_h15)
Total Components: 3, Total Instances: 3
"""
from build123d import *

# === Component: Drive Jaw Hub (comp_eval_h15_hub_drv) ===
"""
Generated build123d code for CADIR Document: Drive Jaw Hub (ID: doc_comp_eval_h15_hub_drv)
Component Family: housing, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Drive Jaw Hub Body (box)
    Box(length=42.0, width=42.0, height=32.0, mode=Mode.ADD)

    # Feature: Drive Jaw Hub Cavity (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=7.0, depth=None)

result = p.part

# === Component: Driven Jaw Hub (comp_eval_h15_hub_out) ===
"""
Generated build123d code for CADIR Document: Driven Jaw Hub (ID: doc_comp_eval_h15_hub_out)
Component Family: housing, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Driven Jaw Hub Body (box)
    Box(length=42.0, width=42.0, height=32.0, mode=Mode.ADD)

    # Feature: Driven Jaw Hub Cavity (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=7.0, depth=None)

result = p.part

# === Component: Elastomeric Spider Damper (comp_eval_h15_spider) ===
"""
Generated build123d code for CADIR Document: Elastomeric Spider Damper (ID: doc_comp_eval_h15_spider)
Component Family: disc, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Elastomeric Spider Damper Solid (cylinder)
    Cylinder(radius=20.0, height=12.0, mode=Mode.ADD)

    # Feature: Elastomeric Spider Damper Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=6.0, depth=None)

result = p.part


# --- Assembly Placement & Compound Construction ---
# Assembled 3 solids into Compound