"""
Assembly: 90-Degree Bevel Gear Drive Assembly (ID: asm_cmplx-06)
Total Components: 5, Total Instances: 5
"""
from build123d import *

# === Component: Right Angle Support Bracket (comp_1) ===
"""
Generated build123d code for CADIR Document: Right Angle Support Bracket (ID: doc_comp_1)
Component Family: structural_support, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Right Angle Support Bracket Base (box)
    Box(length=150.0, width=150.0, height=80.0, mode=Mode.ADD)

    # Feature: Right Angle Support Bracket Mounting Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=22.5, depth=160.0)

result = p.part

# === Component: Input Shaft (comp_2) ===
"""
Generated build123d code for CADIR Document: Input Shaft (ID: doc_comp_2)
Component Family: rotating_shaft, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Input Shaft Base (box)
    Box(length=120.0, width=30.0, height=10.0, mode=Mode.ADD)

    # Feature: Input Shaft Mounting Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=4.5, depth=20.0)

result = p.part

# === Component: Bevel Pinion (comp_3) ===
"""
Generated build123d code for CADIR Document: Bevel Pinion (ID: doc_comp_3)
Component Family: gear, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Gear Blank Cylinder (cylinder)
    Cylinder(radius=24.0, height=25.0, mode=Mode.ADD)

    # Feature: Shaft Bore Hole (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=7.0, depth=50.0)

result = p.part

# === Component: Output Shaft (comp_4) ===
"""
Generated build123d code for CADIR Document: Output Shaft (ID: doc_comp_4)
Component Family: rotating_shaft, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Output Shaft Base (box)
    Box(length=120.0, width=30.0, height=10.0, mode=Mode.ADD)

    # Feature: Output Shaft Mounting Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=4.5, depth=20.0)

result = p.part

# === Component: Bevel Gear (comp_5) ===
"""
Generated build123d code for CADIR Document: Bevel Gear (ID: doc_comp_5)
Component Family: gear, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Gear Blank Cylinder (cylinder)
    Cylinder(radius=24.0, height=25.0, mode=Mode.ADD)

    # Feature: Shaft Bore Hole (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=7.0, depth=50.0)

result = p.part


# --- Assembly Placement & Compound Construction ---
# Assembled 5 solids into Compound