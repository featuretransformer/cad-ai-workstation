"""
Assembly: Industrial Flanged Ball Valve Assembly (ID: asm_valve_eval_c29)
Total Components: 4, Total Instances: 4
"""
from build123d import *

# === Component: Flanged Valve Body (comp_eval_c29_body) ===
"""
Generated build123d code for CADIR Document: Flanged Valve Body (ID: doc_comp_eval_c29_body)
Component Family: valve_body, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Flanged Valve Body Body (box)
    Box(length=100.0, width=70.0, height=70.0, mode=Mode.ADD)

    # Feature: Flanged Valve Body Cavity (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=17.5, depth=None)

result = p.part

# === Component: Valve Ball Core (comp_eval_c29_ball) ===
"""
Generated build123d code for CADIR Document: Valve Ball Core (ID: doc_comp_eval_c29_ball)
Component Family: rotor, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Valve Ball Core Solid (cylinder)
    Cylinder(radius=21.0, height=35.0, mode=Mode.ADD)

    # Feature: Valve Ball Core Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=12.5, depth=None)

result = p.part

# === Component: Valve Stem (comp_eval_c29_stem) ===
"""
Generated build123d code for CADIR Document: Valve Stem (ID: doc_comp_eval_c29_stem)
Component Family: shaft, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Valve Stem Shaft (cylinder)
    Cylinder(radius=6.0, height=55.0, mode=Mode.ADD)

result = p.part

# === Component: Manual Lever Handle (comp_eval_c29_handle) ===
"""
Generated build123d code for CADIR Document: Manual Lever Handle (ID: doc_comp_eval_c29_handle)
Component Family: lever, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Manual Lever Handle Arm (box)
    Box(length=110.0, width=20.0, height=6.0, mode=Mode.ADD)

    # Feature: Pivot Hole (hole)
    with Locations((-45.0, 0.0, 0.0)):
        Hole(radius=4.0, depth=12.0)

result = p.part


# --- Assembly Placement & Compound Construction ---
# Assembled 4 solids into Compound