"""
Assembly: Slider-Crank Reciprocating Mechanism Assembly (ID: asm_recip_eval_h18)
Total Components: 4, Total Instances: 4
"""
from build123d import *

# === Component: Cylinder & Guide Block (comp_eval_h18_block) ===
"""
Generated build123d code for CADIR Document: Cylinder & Guide Block (ID: doc_comp_eval_h18_block)
Component Family: cylinder_block, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Cylinder & Guide Block Body (box)
    Box(length=120.0, width=80.0, height=70.0, mode=Mode.ADD)

    # Feature: Cylinder & Guide Block Cavity (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=20.0, depth=None)

result = p.part

# === Component: Crank Disk & Shaft (comp_eval_h18_crank) ===
"""
Generated build123d code for CADIR Document: Crank Disk & Shaft (ID: doc_comp_eval_h18_crank)
Component Family: flywheel, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Crank Disk & Shaft Solid (cylinder)
    Cylinder(radius=35.0, height=18.0, mode=Mode.ADD)

    # Feature: Crank Disk & Shaft Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=8.0, depth=None)

result = p.part

# === Component: Connecting Linkage Rod (comp_eval_h18_rod) ===
"""
Generated build123d code for CADIR Document: Connecting Linkage Rod (ID: doc_comp_eval_h18_rod)
Component Family: connecting_rod, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Connecting Linkage Rod Arm (box)
    Box(length=90.0, width=16.0, height=10.0, mode=Mode.ADD)

    # Feature: Pivot Hole (hole)
    with Locations((-35.0, 0.0, 0.0)):
        Hole(radius=4.0, depth=None)

result = p.part

# === Component: Reciprocating Piston Slider (comp_eval_h18_slider) ===
"""
Generated build123d code for CADIR Document: Reciprocating Piston Slider (ID: doc_comp_eval_h18_slider)
Component Family: actuator, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Actuator Cylinder Body (cylinder)
    Cylinder(radius=19.0, height=45.0, mode=Mode.ADD)

    # Feature: Piston Extension Rod (cylinder)
    with Locations((0.0, 0.0, 45.0)):
        Cylinder(radius=6.0, height=30.0, mode=Mode.ADD)

    # Feature: Linkage Crosshead Hub (cylinder)
    with Locations((0.0, 0.0, 75.0)):
        Cylinder(radius=14.0, height=10.0, mode=Mode.ADD)

result = p.part


# --- Assembly Placement & Compound Construction ---
# Assembled 4 solids into Compound