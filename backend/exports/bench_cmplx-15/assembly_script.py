"""
Assembly: Rigid Flange Shaft Coupling (ID: asm_cmplx-15)
Total Components: 4, Total Instances: 7
"""
from build123d import *

# === Component: Drive Hub (comp_1) ===
"""
Generated build123d code for CADIR Document: Drive Hub (ID: doc_comp_1)
Component Family: hub, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Drive Hub Base (box)
    Box(length=40.0, width=30.0, height=10.0, mode=Mode.ADD)

    # Feature: Drive Hub Mounting Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=4.5, depth=20.0)

result = p.part

# === Component: Driven Hub (comp_2) ===
"""
Generated build123d code for CADIR Document: Driven Hub (ID: doc_comp_2)
Component Family: hub, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Driven Hub Base (box)
    Box(length=40.0, width=30.0, height=10.0, mode=Mode.ADD)

    # Feature: Driven Hub Mounting Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=4.5, depth=20.0)

result = p.part

# === Component: Drive Key (comp_3) ===
"""
Generated build123d code for CADIR Document: Drive Key (ID: doc_comp_3)
Component Family: key, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Drive Key Base (box)
    Box(length=25.0, width=8.0, height=7.0, mode=Mode.ADD)

    # Feature: Drive Key Mounting Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=1.2, depth=14.0)

result = p.part

# === Component: Connecting Bolt (comp_4) ===
"""
Generated build123d code for CADIR Document: Connecting Bolt (ID: doc_comp_4)
Component Family: fastener, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Connecting Bolt Base (box)
    Box(length=50.0, width=30.0, height=10.0, mode=Mode.ADD)

    # Feature: Connecting Bolt Mounting Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=4.5, depth=20.0)

result = p.part


# --- Assembly Placement & Compound Construction ---
# Assembled 7 solids into Compound