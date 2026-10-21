"""
Assembly: Simplified Toggle Clamp (ID: asm_29401352)
Total Components: 7, Total Instances: 7
"""
from build123d import *

# === Component: Base Plate (comp_base) ===
"""
Generated build123d code for CADIR Document: Base Plate (ID: doc_comp_base)
Component Family: mounting_plate, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Plate Base Disk (cylinder)
    Cylinder(radius=60.0, height=8.0, mode=Mode.ADD)

    # Feature: Actuator Center Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=16.0, depth=16.0)

    # Feature: Clevis Mounting Lug 1 (box)
    with Locations((45.0, 0.0, 17.0)):
        Box(length=22.0, width=24.0, height=18.0, mode=Mode.ADD)

    # Feature: Clevis Slot 1 (pocket)
    with Locations((45.0, 0.0, 18.799999999999997)):
        Box(length=26.0, width=11.5, height=21.599999999999998, mode=Mode.SUBTRACT)

    # Feature: Lug Pin Hole 1 (hole)
    with Locations((45.0, 0.0, 19.700000000000003)):
        Hole(radius=4.0, depth=30.0)

    # Feature: Clevis Mounting Lug 2 (box)
    with Locations((-22.5, 38.97, 17.0)):
        Box(length=22.0, width=24.0, height=18.0, mode=Mode.ADD)

    # Feature: Clevis Slot 2 (pocket)
    with Locations((-22.5, 38.97, 18.799999999999997)):
        Box(length=26.0, width=11.5, height=21.599999999999998, mode=Mode.SUBTRACT)

    # Feature: Lug Pin Hole 2 (hole)
    with Locations((-22.5, 38.97, 19.700000000000003)):
        Hole(radius=4.0, depth=30.0)

    # Feature: Clevis Mounting Lug 3 (box)
    with Locations((-22.5, -38.97, 17.0)):
        Box(length=22.0, width=24.0, height=18.0, mode=Mode.ADD)

    # Feature: Clevis Slot 3 (pocket)
    with Locations((-22.5, -38.97, 18.799999999999997)):
        Box(length=26.0, width=11.5, height=21.599999999999998, mode=Mode.SUBTRACT)

    # Feature: Lug Pin Hole 3 (hole)
    with Locations((-22.5, -38.97, 19.700000000000003)):
        Hole(radius=4.0, depth=30.0)

result = p.part

# === Component: Upright Support (comp_support) ===
"""
Generated build123d code for CADIR Document: Upright Support (ID: doc_comp_support)
Component Family: support_structure, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Upright Support Base (box)
    Box(length=50.0, width=30.0, height=8.0, mode=Mode.ADD)

    # Feature: Upright Support Mounting Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=4.5, depth=16.0)

result = p.part

# === Component: Long Toggle Link (comp_link_long) ===
"""
Generated build123d code for CADIR Document: Long Toggle Link (ID: doc_comp_link_long)
Component Family: link, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Link Arm Solid (box)
    with Locations((32.5, 0.0, 4.0)):
        Box(length=65.0, width=20.0, height=8.0, mode=Mode.ADD)

    # Feature: Drive End Hole (hole)
    with Locations((6.0, 0.0, 0.0)):
        Hole(radius=2.5, depth=16.0)

    # Feature: Output End Hole (hole)
    with Locations((59.0, 0.0, 0.0)):
        Hole(radius=2.5, depth=16.0)

result = p.part

# === Component: Short Toggle Link (comp_link_short) ===
"""
Generated build123d code for CADIR Document: Short Toggle Link (ID: doc_comp_link_short)
Component Family: link, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Link Arm Solid (box)
    with Locations((22.5, 0.0, 4.0)):
        Box(length=45.0, width=20.0, height=8.0, mode=Mode.ADD)

    # Feature: Drive End Hole (hole)
    with Locations((6.0, 0.0, 0.0)):
        Hole(radius=2.5, depth=16.0)

    # Feature: Output End Hole (hole)
    with Locations((39.0, 0.0, 0.0)):
        Hole(radius=2.5, depth=16.0)

result = p.part

# === Component: Clamp Handle (comp_handle) ===
"""
Generated build123d code for CADIR Document: Clamp Handle (ID: doc_comp_handle)
Component Family: actuator, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Actuator Cylinder Body (cylinder)
    Cylinder(radius=15.0, height=65.0, mode=Mode.ADD)

    # Feature: Piston Extension Rod (cylinder)
    with Locations((0.0, 0.0, 65.0)):
        Cylinder(radius=6.0, height=30.0, mode=Mode.ADD)

    # Feature: Linkage Crosshead Hub (cylinder)
    with Locations((0.0, 0.0, 95.0)):
        Cylinder(radius=14.0, height=10.0, mode=Mode.ADD)

result = p.part

# === Component: Shoulder Pin Support (comp_pin_support) ===
"""
Generated build123d code for CADIR Document: Shoulder Pin Support (ID: doc_comp_pin_support)
Component Family: fastener, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Shoulder Pin Support Base (box)
    Box(length=24.0, width=30.0, height=10.0, mode=Mode.ADD)

    # Feature: Shoulder Pin Support Mounting Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=3.5999999999999996, depth=20.0)

result = p.part

# === Component: Shoulder Pin Toggle (comp_pin_toggle) ===
"""
Generated build123d code for CADIR Document: Shoulder Pin Toggle (ID: doc_comp_pin_toggle)
Component Family: fastener, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Shoulder Pin Toggle Base (box)
    Box(length=24.0, width=30.0, height=10.0, mode=Mode.ADD)

    # Feature: Shoulder Pin Toggle Mounting Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=3.5999999999999996, depth=20.0)

result = p.part


# --- Assembly Placement & Compound Construction ---
# Assembled 7 solids into Compound