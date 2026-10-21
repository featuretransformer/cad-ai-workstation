"""
Assembly: Precision Linear Actuator Slide Stage (ID: asm_actuator_eval_c27)
Total Components: 5, Total Instances: 5
"""
from build123d import *

# === Component: Base Linear Guide Rail (comp_eval_c27_rail) ===
"""
Generated build123d code for CADIR Document: Base Linear Guide Rail (ID: doc_comp_eval_c27_rail)
Component Family: mounting_plate, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Base Linear Guide Rail Plate (box)
    Box(length=200.0, width=45.0, height=15.0, mode=Mode.ADD)

result = p.part

# === Component: Carriage Slide Table (comp_eval_c27_table) ===
"""
Generated build123d code for CADIR Document: Carriage Slide Table (ID: doc_comp_eval_c27_table)
Component Family: mounting_plate, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Carriage Slide Table Plate (box)
    Box(length=60.0, width=55.0, height=15.0, mode=Mode.ADD)

result = p.part

# === Component: Precision Lead Screw (comp_eval_c27_screw) ===
"""
Generated build123d code for CADIR Document: Precision Lead Screw (ID: doc_comp_eval_c27_screw)
Component Family: lead_screw, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Precision Lead Screw Shaft (cylinder)
    Cylinder(radius=6.0, height=210.0, mode=Mode.ADD)

result = p.part

# === Component: Drive End Bearing Block (comp_eval_c27_end_drv) ===
"""
Generated build123d code for CADIR Document: Drive End Bearing Block (ID: doc_comp_eval_c27_end_drv)
Component Family: housing, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Drive End Bearing Block Body (box)
    Box(length=40.0, width=45.0, height=30.0, mode=Mode.ADD)

    # Feature: Drive End Bearing Block Cavity (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=8.0, depth=None)

result = p.part

# === Component: Floating End Bearing Block (comp_eval_c27_end_flt) ===
"""
Generated build123d code for CADIR Document: Floating End Bearing Block (ID: doc_comp_eval_c27_end_flt)
Component Family: housing, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Floating End Bearing Block Body (box)
    Box(length=40.0, width=45.0, height=30.0, mode=Mode.ADD)

    # Feature: Floating End Bearing Block Cavity (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=8.0, depth=None)

result = p.part


# --- Assembly Placement & Compound Construction ---
# Assembled 5 solids into Compound