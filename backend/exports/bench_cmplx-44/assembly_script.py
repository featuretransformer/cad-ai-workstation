"""
Assembly: Three-Finger Mechanical Gripper Assembly (ID: asm_gripper_cmplx-44)
Total Components: 5, Total Instances: 11
"""
from build123d import *

# === Component: Base Mounting Plate (comp_cmplx-44_mount_plate) ===
"""
Generated build123d code for CADIR Document: Base Mounting Plate (ID: doc_comp_cmplx-44_mount_plate)
Component Family: mounting_plate, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Plate Base Disk (cylinder)
    Cylinder(radius=60.0, height=12.0, mode=Mode.ADD)

    # Feature: Actuator Center Bore (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=16.0, depth=24.0)

    # Feature: Clevis Mounting Lug 1 (box)
    with Locations((45.0, 0.0, 21.0)):
        Box(length=22.0, width=24.0, height=18.0, mode=Mode.ADD)

    # Feature: Clevis Slot 1 (pocket)
    with Locations((45.0, 0.0, 22.799999999999997)):
        Box(length=26.0, width=11.5, height=21.599999999999998, mode=Mode.SUBTRACT)

    # Feature: Lug Pin Hole 1 (hole)
    with Locations((45.0, 0.0, 23.700000000000003)):
        Hole(radius=4.0, depth=30.0)

    # Feature: Clevis Mounting Lug 2 (box)
    with Locations((-22.5, 38.97, 21.0)):
        Box(length=22.0, width=24.0, height=18.0, mode=Mode.ADD)

    # Feature: Clevis Slot 2 (pocket)
    with Locations((-22.5, 38.97, 22.799999999999997)):
        Box(length=26.0, width=11.5, height=21.599999999999998, mode=Mode.SUBTRACT)

    # Feature: Lug Pin Hole 2 (hole)
    with Locations((-22.5, 38.97, 23.700000000000003)):
        Hole(radius=4.0, depth=30.0)

    # Feature: Clevis Mounting Lug 3 (box)
    with Locations((-22.5, -38.97, 21.0)):
        Box(length=22.0, width=24.0, height=18.0, mode=Mode.ADD)

    # Feature: Clevis Slot 3 (pocket)
    with Locations((-22.5, -38.97, 22.799999999999997)):
        Box(length=26.0, width=11.5, height=21.599999999999998, mode=Mode.SUBTRACT)

    # Feature: Lug Pin Hole 3 (hole)
    with Locations((-22.5, -38.97, 23.700000000000003)):
        Hole(radius=4.0, depth=30.0)

result = p.part

# === Component: Articulated Gripping Finger (comp_cmplx-44_finger) ===
"""
Generated build123d code for CADIR Document: Articulated Gripping Finger (ID: doc_comp_cmplx-44_finger)
Component Family: finger, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Finger Beam Body (box)
    with Locations((27.5, 0.0, 5.0)):
        Box(length=75.0, width=16.0, height=10.0, mode=Mode.ADD)

    # Feature: Main Hinge Pivot Hole (hole)
    with Locations((0.0, 0.0, 0.0)):
        Hole(radius=4.0, depth=20.0)

    # Feature: Linkage Drive Hole (hole)
    with Locations((22.0, 0.0, 0.0)):
        Hole(radius=2.5, depth=20.0)

    # Feature: Finger Tip Taper Pocket (pocket)
    with Locations((60.0, 0.0, 7.0)):
        Box(length=30.0, width=8.0, height=6.0, mode=Mode.SUBTRACT)

result = p.part

# === Component: Finger Pivot Pin (comp_cmplx-44_pivot_pin) ===
"""
Generated build123d code for CADIR Document: Finger Pivot Pin (ID: doc_comp_cmplx-44_pivot_pin)
Component Family: pivot_pin, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Pin Main Shaft (cylinder)
    Cylinder(radius=3.975, height=26.0, mode=Mode.ADD)

    # Feature: Pin Retaining Head (cylinder)
    with Locations((0.0, 0.0, 26.0)):
        Cylinder(radius=6.0, height=3.0, mode=Mode.ADD)

    # Feature: Lead-in Chamfer (chamfer)
    try:
        _edges = p.edges()
        _edges = _edges.sort_by(Axis.Z)[:4] 
        if _edges:
            chamfer(_edges, length=0.8)
    except Exception as _ce:
        print(f"Chamfer warning: {_ce}")

result = p.part

# === Component: Actuation Drive Link (comp_cmplx-44_linkage) ===
"""
Generated build123d code for CADIR Document: Actuation Drive Link (ID: doc_comp_cmplx-44_linkage)
Component Family: linkage, Units: mm
"""
from build123d import *

with BuildPart() as p:
    # Feature: Link Arm Solid (box)
    with Locations((21.0, 0.0, 2.5)):
        Box(length=42.0, width=12.0, height=5.0, mode=Mode.ADD)

    # Feature: Drive End Hole (hole)
    with Locations((6.0, 0.0, 0.0)):
        Hole(radius=2.5, depth=10.0)

    # Feature: Output End Hole (hole)
    with Locations((36.0, 0.0, 0.0)):
        Hole(radius=2.5, depth=10.0)

result = p.part

# === Component: Central Actuator & Crosshead (comp_cmplx-44_actuator) ===
"""
Generated build123d code for CADIR Document: Central Actuator & Crosshead (ID: doc_comp_cmplx-44_actuator)
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


# --- Assembly Placement & Compound Construction ---
# Assembled 11 solids into Compound