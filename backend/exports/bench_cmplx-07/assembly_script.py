"""
Assembly: Spur Gear Reducer Assembly (ID: asm_gearbox_cmplx-07)
Total Components: 3, Total Instances: 3
"""
from build123d import *

# === Component: Gearbox Base Plate (comp_cmplx-07_housing) ===
"""
Generated build123d code for CADIR Document: Gearbox Base Plate (ID: doc_comp_cmplx-07_housing)
Component Family: housing, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Gearbox Base Plate Base (box)
    Box(length=140.0, width=90.0, height=15.0, mode=Mode.ADD)

    # Feature: Gearbox Base Plate Mounting Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=13.5, depth=30.0)

result = p.part

# === Component: Drive Pinion Gear & Shaft (comp_cmplx-07_pinion) ===
"""
Generated build123d code for CADIR Document: Drive Pinion Gear & Shaft (ID: doc_comp_cmplx-07_pinion)
Component Family: gear, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Gear Blank Cylinder (cylinder)
    Cylinder(radius=18.0, height=20.0, mode=Mode.ADD)

    # Feature: Shaft Bore Hole (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=8.0, depth=40.0)

result = p.part

# === Component: Driven Spur Gear & Shaft (comp_cmplx-07_gear) ===
"""
Generated build123d code for CADIR Document: Driven Spur Gear & Shaft (ID: doc_comp_cmplx-07_gear)
Component Family: gear, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Gear Blank Cylinder (cylinder)
    Cylinder(radius=42.0, height=20.0, mode=Mode.ADD)

    # Feature: Shaft Bore Hole (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=10.0, depth=40.0)

result = p.part


# --- Assembly Placement & Compound Construction ---
# Assembled 3 solids into Compound