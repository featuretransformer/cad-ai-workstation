"""
Assembly: Sensor Mounting Clamp Block (ID: asm_h_med-22)
Total Components: 2, Total Instances: 2
"""
from build123d import *

# === Component: Clamp Block Body (comp_1) ===
"""
Generated build123d code for CADIR Document: Clamp Block Body (ID: doc_comp_1)
Component Family: structural_housing, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Clamp Block Body Base (box)
    Box(length=45.0, width=30.0, height=20.0, mode=Mode.ADD)

    # Feature: Clamp Block Body Mounting Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=4.5, depth=40.0)

result = p.part

# === Component: Set Screw (comp_2) ===
"""
Generated build123d code for CADIR Document: Set Screw (ID: doc_comp_2)
Component Family: fastener, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Set Screw Base (box)
    Box(length=10.0, width=30.0, height=10.0, mode=Mode.ADD)

    # Feature: Set Screw Mounting Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=1.5, depth=20.0)

result = p.part


# --- Assembly Placement & Compound Construction ---
# Assembled 2 solids into Compound