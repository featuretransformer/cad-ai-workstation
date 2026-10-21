"""
Assembly: Mechanical Scissor Lift Table Assembly (ID: asm_scissor_eval_c13)
Total Components: 5, Total Instances: 7
"""
from build123d import *

# === Component: Base Frame Bed (comp_eval_c13_base) ===
"""
Generated build123d code for CADIR Document: Base Frame Bed (ID: doc_comp_eval_c13_base)
Component Family: mounting_plate, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Base Frame Bed Plate (box)
    Box(length=160.0, width=100.0, height=12.0, mode=Mode.ADD)

result = p.part

# === Component: Top Lift Platform (comp_eval_c13_platform) ===
"""
Generated build123d code for CADIR Document: Top Lift Platform (ID: doc_comp_eval_c13_platform)
Component Family: mounting_plate, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Top Lift Platform Plate (box)
    Box(length=160.0, width=100.0, height=10.0, mode=Mode.ADD)

result = p.part

# === Component: Inner Scissor Link Arm (comp_eval_c13_arm_in) ===
"""
Generated build123d code for CADIR Document: Inner Scissor Link Arm (ID: doc_comp_eval_c13_arm_in)
Component Family: linkage, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Link Arm Solid (box)
    with Locations((55.0, 0.0, 4.0)):
        Box(length=110.0, width=16.0, height=8.0, mode=Mode.ADD)

    # Feature: Drive End Hole (hole)
    with Locations((6.0, 0.0, 0.0)):
        Hole(radius=2.5, depth=None)

    # Feature: Output End Hole (hole)
    with Locations((104.0, 0.0, 0.0)):
        Hole(radius=2.5, depth=None)

result = p.part

# === Component: Outer Scissor Link Arm (comp_eval_c13_arm_out) ===
"""
Generated build123d code for CADIR Document: Outer Scissor Link Arm (ID: doc_comp_eval_c13_arm_out)
Component Family: linkage, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Link Arm Solid (box)
    with Locations((55.0, 0.0, 4.0)):
        Box(length=110.0, width=16.0, height=8.0, mode=Mode.ADD)

    # Feature: Drive End Hole (hole)
    with Locations((6.0, 0.0, 0.0)):
        Hole(radius=2.5, depth=None)

    # Feature: Output End Hole (hole)
    with Locations((104.0, 0.0, 0.0)):
        Hole(radius=2.5, depth=None)

result = p.part

# === Component: Central Actuator Drive Screw (comp_eval_c13_spindle) ===
"""
Generated build123d code for CADIR Document: Central Actuator Drive Screw (ID: doc_comp_eval_c13_spindle)
Component Family: lead_screw, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Central Actuator Drive Screw Shaft (cylinder)
    Cylinder(radius=7.0, height=140.0, mode=Mode.ADD)

result = p.part


# --- Assembly Placement & Compound Construction ---
# Assembled 7 solids into Compound