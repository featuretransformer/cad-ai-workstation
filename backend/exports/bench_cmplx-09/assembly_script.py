"""
Assembly: Heavy-Duty Caster Wheel Assembly (ID: asm_caster_cmplx-09)
Total Components: 4, Total Instances: 4
"""
from build123d import *

# === Component: Swivel Top Plate (comp_cmplx-09_top_plate) ===
"""
Generated build123d code for CADIR Document: Swivel Top Plate (ID: doc_comp_cmplx-09_top_plate)
Component Family: mounting_plate, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Plate Base Disk (cylinder)
    Cylinder(radius=60.0, height=6.0, mode=Mode.ADD)

    # Feature: Actuator Center Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=16.0, depth=12.0)

    # Feature: Clevis Mounting Lug 1 (box)
    with Locations((45.0, 0.0, 15.0)):
        Box(length=22.0, width=24.0, height=18.0, mode=Mode.ADD)

    # Feature: Clevis Slot 1 (pocket)
    with Locations((45.0, 0.0, 16.799999999999997)):
        Box(length=26.0, width=11.5, height=21.599999999999998, mode=Mode.SUBTRACT)

    # Feature: Lug Pin Hole 1 (hole)
    with Locations((45.0, 0.0, 17.700000000000003)):
        Hole(radius=4.0, depth=30.0)

    # Feature: Clevis Mounting Lug 2 (box)
    with Locations((-22.5, 38.97, 15.0)):
        Box(length=22.0, width=24.0, height=18.0, mode=Mode.ADD)

    # Feature: Clevis Slot 2 (pocket)
    with Locations((-22.5, 38.97, 16.799999999999997)):
        Box(length=26.0, width=11.5, height=21.599999999999998, mode=Mode.SUBTRACT)

    # Feature: Lug Pin Hole 2 (hole)
    with Locations((-22.5, 38.97, 17.700000000000003)):
        Hole(radius=4.0, depth=30.0)

    # Feature: Clevis Mounting Lug 3 (box)
    with Locations((-22.5, -38.97, 15.0)):
        Box(length=22.0, width=24.0, height=18.0, mode=Mode.ADD)

    # Feature: Clevis Slot 3 (pocket)
    with Locations((-22.5, -38.97, 16.799999999999997)):
        Box(length=26.0, width=11.5, height=21.599999999999998, mode=Mode.SUBTRACT)

    # Feature: Lug Pin Hole 3 (hole)
    with Locations((-22.5, -38.97, 17.700000000000003)):
        Hole(radius=4.0, depth=30.0)

result = p.part

# === Component: Caster Fork Bracket (comp_cmplx-09_fork) ===
"""
Generated build123d code for CADIR Document: Caster Fork Bracket (ID: doc_comp_cmplx-09_fork)
Component Family: bracket, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Caster Fork Bracket Base (box)
    Box(length=50.0, width=45.0, height=4.0, mode=Mode.ADD)

    # Feature: Caster Fork Bracket Mounting Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=6.75, depth=8.0)

result = p.part

# === Component: Wheel Roller (comp_cmplx-09_wheel) ===
"""
Generated build123d code for CADIR Document: Wheel Roller (ID: doc_comp_cmplx-09_wheel)
Component Family: wheel, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Wheel Roller Base (box)
    Box(length=50.0, width=30.0, height=10.0, mode=Mode.ADD)

    # Feature: Wheel Roller Mounting Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=4.5, depth=20.0)

result = p.part

# === Component: Axle Bolt & Nut (comp_cmplx-09_axle) ===
"""
Generated build123d code for CADIR Document: Axle Bolt & Nut (ID: doc_comp_cmplx-09_axle)
Component Family: fastener, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Axle Bolt & Nut Base (box)
    Box(length=48.0, width=30.0, height=10.0, mode=Mode.ADD)

    # Feature: Axle Bolt & Nut Mounting Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=4.5, depth=20.0)

result = p.part


# --- Assembly Placement & Compound Construction ---
# Assembled 4 solids into Compound